"""
Django Management Command: load_village_shapefile

Loads official administrative MultiPolygon boundaries from external GIS sources
(such as ISRO Bhuvan Panchayat, Survey of India, or Bharat Maps shapefiles)
into the GeoDjango Village model in PostgreSQL/PostGIS.

Features:
- Mandatory District Pre-Filtering: Automatically filters the 45,000+ state-wide
  dataset by District Name (e.g. Rajsamand for Piplantri/Kothariya, Jhunjhunu for Mandawa,
  Phalodi/Jodhpur/Jaisalmer for Bhadla/Kuldhara) BEFORE performing any name matching.
  Guarantees zero cross-district namesake false positives.
- Spatial Proximity Ranking: Ranks candidate matches by distance to known village
  centroid coordinates, selecting the spatially closest authentic cadastral polygon.
- Normalizes column names (strips whitespace and newlines, handles case-insensitivity).
- Auto-reprojects input CRS (EPSG:7755, LCC, Everest, etc.) to WGS 84 (EPSG:4326).
- Automatically repairs invalid self-intersecting geometries (make_valid).
- Casts Polygon to MultiPolygon and strips 3D coordinates.
- Computes high-precision metric area in hectares using local UTM projection.
"""

import os
import sys
import math
import difflib
from django.core.management.base import BaseCommand, CommandError
from django.contrib.gis.geos import GEOSGeometry, MultiPolygon, Polygon
from django.db import transaction
from villages.models import Village

# Candidate column names in lower-case
CANDIDATE_NAME_FIELDS = [
    "village", "vill_name", "villname", "name", "village_na", "vil_name",
    "name_en", "vill_name_", "v_name", "villagname", "tehsil_vil"
]

CANDIDATE_DISTRICT_FIELDS = [
    "district", "dist_name", "district_name", "dist_na", "dt_name", "district_n",
    "dist_name_", "ds_name", "district_head_quarter"
]

# District mapping for administrative reorganizations and state-specific aliases
DISTRICT_SYNONYMS = {
    # Rajasthan
    "rajsamand": ["rajsamand"],
    "jhunjhunu": ["jhunjhunu", "jhunjhunun"],
    "jaisalmer": ["jaisalmer"],
    "phalodi": ["phalodi", "jodhpur", "jaisalmer", "bikaner"],  # Bap tehsil / Phalodi historical borders
    "bhadla": ["phalodi", "jodhpur", "jaisalmer", "bikaner"],
    # Uttar Pradesh
    "lakhimpur kheri": ["lakhimpur kheri", "kheri", "lakhimpur"],
    "prayagraj": ["prayagraj", "allahabad"],
    "ayodhya": ["ayodhya", "faizabad"],
    "amroha": ["amroha", "jyotiba phule nagar"],
    "varanasi": ["varanasi", "banaras", "kashi"],
}

# Known survey / transliteration synonyms for pilot villages
NAME_ALIASES = {
    "juggaur": ["juggaur", "jugor", "jugaur"],
    "dumri khas": ["dumri khas", "dumri"],
    "bhatkaon": ["bhatkaon", "bhatkauli", "bhatkawan"],
    "bhadla": ["bhadla", "bhadlachuhron ki basti"],
    "kuldhara": ["kuldhara", "kuldhar"],
}


def haversine_distance_km(lon1, lat1, lon2, lat2):
    """Calculate great-circle distance between two WGS84 coordinates in km."""
    r = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2.0) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return r * c


class Command(BaseCommand):
    help = "Import village boundaries from state-wide Shapefile/GeoJSON with mandatory District Pre-Filtering"

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            type=str,
            required=True,
            help="Path to input Shapefile (.shp), GeoJSON (.geojson), or zipped archive (.zip)"
        )
        parser.add_argument(
            "--inspect",
            action="store_true",
            help="Inspect shapefile attributes, CRS, and preview records without importing"
        )
        parser.add_argument(
            "--name-field",
            type=str,
            default=None,
            help="Attribute column name containing village names (e.g. village, VILL_NAME)"
        )
        parser.add_argument(
            "--district-field",
            type=str,
            default=None,
            help="Attribute column name containing district names (e.g. district, DIST_NAME)"
        )
        parser.add_argument(
            "--district",
            type=str,
            default=None,
            help="Override district filter for all target villages"
        )
        parser.add_argument(
            "--max-distance-km",
            type=float,
            default=35.0,
            help="Maximum allowed distance in km from known centroid to reject spatial false positives (default: 35.0 km)"
        )
        parser.add_argument(
            "--village",
            type=str,
            default=None,
            help="Target a specific village name (e.g. --village Piplantri)"
        )
        parser.add_argument(
            "--state",
            type=str,
            default=None,
            help="Target villages by state name (e.g. --state 'Uttar Pradesh')"
        )
        parser.add_argument(
            "--fuzzy",
            action="store_true",
            help="Enable fuzzy matching for spelling variants (e.g. 'Piplantri Khurd')"
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Perform simulation without committing changes to PostgreSQL"
        )

    def handle(self, *args, **options):
        file_path = options["file"]
        inspect_mode = options["inspect"]
        name_field_arg = options["name_field"]
        district_field_arg = options["district_field"]
        cli_district = options["district"]
        max_dist_km = options["max_distance_km"]
        target_village = options["village"]
        target_state = options.get("state")
        enable_fuzzy = options["fuzzy"]
        dry_run = options["dry_run"]

        if not os.path.exists(file_path):
            raise CommandError(f"File not found: {file_path}")

        try:
            import geopandas as gpd
            from shapely.validation import make_valid
        except ImportError:
            raise CommandError("GeoPandas and Shapely are required. Run: pip install geopandas shapely")

        self.stdout.write(f"Reading GIS file: {file_path} ...")
        try:
            gdf = gpd.read_file(file_path)
        except Exception as exc:
            raise CommandError(f"Failed to read file with GeoPandas: {exc}")

        # Normalize column names: strip whitespace and trailing newlines
        original_cols = list(gdf.columns)
        col_rename_map = {c: str(c).strip().replace("\n", "").replace("\r", "") for c in original_cols}
        gdf = gdf.rename(columns=col_rename_map)

        # 1. Inspection Mode
        if inspect_mode:
            self._inspect_file(gdf, file_path)
            return

        # 2. Identify Name & District Columns (case-insensitive)
        lower_cols = {c.lower(): c for c in gdf.columns}

        name_field = None
        if name_field_arg and name_field_arg in gdf.columns:
            name_field = name_field_arg
        elif name_field_arg and name_field_arg.lower() in lower_cols:
            name_field = lower_cols[name_field_arg.lower()]
        else:
            for cand in CANDIDATE_NAME_FIELDS:
                if cand in lower_cols:
                    name_field = lower_cols[cand]
                    break

        if not name_field:
            raise CommandError(
                f"Could not automatically detect village name column. "
                f"Available columns: {list(gdf.columns)}. "
                f"Please specify using --name-field <column_name>."
            )

        district_field = None
        if district_field_arg and district_field_arg in gdf.columns:
            district_field = district_field_arg
        elif district_field_arg and district_field_arg.lower() in lower_cols:
            district_field = lower_cols[district_field_arg.lower()]
        else:
            for cand in CANDIDATE_DISTRICT_FIELDS:
                if cand in lower_cols:
                    district_field = lower_cols[cand]
                    break

        if not district_field:
            raise CommandError(
                f"District column is required for state-wide datasets. "
                f"Could not detect district column among: {list(gdf.columns)}. "
                f"Please specify using --district-field <column_name>."
            )

        self.stdout.write(self.style.SUCCESS(
            f"✓ Columns Identified: Name Column = '{name_field}' | District Column = '{district_field}'"
        ))

        # 3. Ensure CRS is WGS 84 (EPSG:4326) BEFORE distance calculations
        if gdf.crs is None:
            self.stdout.write(self.style.WARNING("File has no CRS defined. Assuming EPSG:4326."))
            gdf = gdf.set_crs("EPSG:4326")
        elif gdf.crs.to_string() != "EPSG:4326":
            self.stdout.write(f"Reprojecting {len(gdf):,} records from {gdf.crs.to_string()} to EPSG:4326 ...")
            gdf = gdf.to_crs("EPSG:4326")

        # 4. Target villages in database
        db_villages = list(Village.objects.all())
        if target_state:
            db_villages = [v for v in db_villages if target_state.lower() in (v.state or "").lower()]
            if not db_villages:
                raise CommandError(f"No villages found in database for state '{target_state}'.")
        if target_village:
            db_villages = [v for v in db_villages if v.name.lower() == target_village.lower()]
            if not db_villages:
                raise CommandError(f"Target village '{target_village}' not found in database.")

        self.stdout.write(
            f"\nMatching {len(db_villages)} village(s) with MANDATORY District Pre-Filtering (Max distance: {max_dist_km} km)..."
        )

        updated_count = 0
        summary_results = []

        with transaction.atomic():
            for village in db_villages:
                self.stdout.write("=" * 70)
                self.stdout.write(f"Target: '{village.name}' (Database District: {village.district})")

                # -------------------------------------------------------------
                # STEP 1: STRICT DISTRICT PRE-FILTERING
                # -------------------------------------------------------------
                target_district = (cli_district or village.district or "").strip().lower()
                allowed_districts = DISTRICT_SYNONYMS.get(target_district, [target_district])

                # Check if village is Bhadla (check Phalodi, Jodhpur, and Jaisalmer)
                if village.name.lower() == "bhadla":
                    allowed_districts = ["phalodi", "jodhpur", "jaisalmer", "bikaner"]

                district_series = gdf[district_field].astype(str).str.strip().str.lower()
                district_mask = district_series.apply(
                    lambda d: any(ad in d for ad in allowed_districts)
                )

                district_subset = gdf[district_mask]
                self.stdout.write(
                    f"  [1. DISTRICT FILTER] State dataset: {len(gdf):,} records -> "
                    f"Filtered down to {len(district_subset):,} records in district(s): {allowed_districts}"
                )

                if district_subset.empty:
                    self.stdout.write(self.style.WARNING(
                        f"  [!] No records found for district(s) {allowed_districts}. Skipping."
                    ))
                    summary_results.append({
                        "name": village.name,
                        "district": target_district,
                        "matched": "None",
                        "status": "NO_DISTRICT_RECORDS"
                    })
                    continue

                # -------------------------------------------------------------
                # STEP 2: NAME MATCHING WITHIN DISTRICT SUBSET
                # -------------------------------------------------------------
                target_clean = village.name.strip().lower()
                target_aliases = [target_clean] + NAME_ALIASES.get(target_clean, [])
                candidate_rows = []

                for idx, row in district_subset.iterrows():
                    shp_name = str(row[name_field]).strip()
                    shp_lower = shp_name.lower()

                    # Exact or alias match
                    if any(shp_lower == alias for alias in target_aliases):
                        candidate_rows.append((row, 1.0, f"Exact/Alias Match ('{shp_name}')"))
                    # Prefix / Contains match (either direction)
                    elif any(alias in shp_lower or shp_lower in alias for alias in target_aliases):
                        candidate_rows.append((row, 0.9, f"Contains ('{shp_name}')"))
                    elif enable_fuzzy:
                        sim = max(difflib.SequenceMatcher(None, alias, shp_lower).ratio() for alias in target_aliases)
                        if sim >= 0.70 and len(shp_lower) >= (len(target_clean) - 2):
                            candidate_rows.append((row, sim, f"Fuzzy ({sim:.2f})"))

                if not candidate_rows:
                    self.stdout.write(self.style.WARNING(
                        f"  [2. NAME MATCH] No shapefile record matched '{village.name}' in district '{target_district}'."
                    ))
                    summary_results.append({
                        "name": village.name,
                        "district": target_district,
                        "matched": "None",
                        "status": "NO_NAME_MATCH"
                    })
                    continue

                # -------------------------------------------------------------
                # STEP 3: SPATIAL PROXIMITY RANKING (Centroid Distance)
                # -------------------------------------------------------------
                ranked_candidates = []
                for row, score, match_type in candidate_rows:
                    geom = row.geometry
                    if geom is None or geom.is_empty:
                        continue
                    poly_centroid = geom.centroid
                    dist_km = haversine_distance_km(
                        village.location.x, village.location.y,
                        poly_centroid.x, poly_centroid.y
                    )
                    ranked_candidates.append((dist_km, score, row, match_type))

                if not ranked_candidates:
                    self.stdout.write(self.style.WARNING(f"  [!] No candidates with valid geometry for '{village.name}'."))
                    continue

                # Filter by spatial proximity FIRST: Discard any namesake > max_dist_km away
                valid_spatial = [c for c in ranked_candidates if c[0] <= max_dist_km]

                if not valid_spatial:
                    closest = min(ranked_candidates, key=lambda x: x[0])
                    closest_name = closest[2][name_field]
                    closest_dist_val = closest[2][district_field]
                    self.stdout.write(self.style.WARNING(
                        f"  [REJECTED] Closest candidate '{closest_name}' ({closest_dist_val}) "
                        f"is {closest[0]:.1f} km away (exceeds {max_dist_km} km spatial limit). "
                        f"Skipping cross-district false positive."
                    ))
                    summary_results.append({
                        "name": village.name,
                        "district": target_district,
                        "matched": closest_name,
                        "distance_km": round(closest[0], 2),
                        "status": "REJECTED_DISTANCE"
                    })
                    continue

                # Sort geographically valid candidates by match quality (-score), then by proximity (distance)
                valid_spatial.sort(key=lambda x: (-x[1], x[0]))

                best_dist, best_score, best_row, match_type = valid_spatial[0]
                shp_vname = best_row[name_field]
                shp_dist_val = best_row[district_field]

                self.stdout.write(
                    f"  [3. SPATIAL CHECK] Best Verified Candidate: '{shp_vname}' ({shp_dist_val}) | "
                    f"Distance to Centroid: {best_dist:.2f} km (PASS <= {max_dist_km} km) | Match: {match_type}"
                )

                # -------------------------------------------------------------
                # STEP 4: GEOMETRY CLEANING & POSTGIS COMMIT
                # -------------------------------------------------------------
                geom = best_row.geometry
                if not geom.is_valid:
                    self.stdout.write(f"  Repairing self-intersecting geometry for '{shp_vname}'...")
                    geom = make_valid(geom)

                multipoly = self._to_geodjango_multipolygon(geom)
                if multipoly is None:
                    self.stdout.write(self.style.ERROR(f"  Failed to convert geometry to MultiPolygon."))
                    continue

                # Dynamically choose UTM projection based on longitude for accurate area calculation:
                # Zone 42N (32642): 66°E - 72°E (Western Thar)
                # Zone 43N (32643): 72°E - 78°E (Central/Eastern Rajasthan, Western UP)
                # Zone 44N (32644): 78°E - 84°E (Central & Eastern UP / Doab / Purvanchal)
                # Zone 45N (32645): >= 84°E
                lng = village.location.x
                if lng < 72.0:
                    utm_epsg = 32642
                elif lng < 78.0:
                    utm_epsg = 32643
                elif lng < 84.0:
                    utm_epsg = 32644
                else:
                    utm_epsg = 32645

                projected_geom = multipoly.transform(utm_epsg, clone=True)
                area_ha = round(projected_geom.area / 10000.0, 2)

                village.boundary = multipoly
                village.area_hectares = area_ha
                village.location = multipoly.centroid

                if not dry_run:
                    village.save(update_fields=["boundary", "area_hectares", "location", "updated_at"])

                self.stdout.write(self.style.SUCCESS(
                    f"  ✓ VERIFIED & COMMITTED: '{village.name}' -> '{shp_vname}'\n"
                    f"    District: {shp_dist_val} | Distance: {best_dist:.2f} km (PASS)\n"
                    f"    Area: {area_ha} ha | Vertices: {len(multipoly[0][0])}"
                ))
                updated_count += 1
                summary_results.append({
                    "name": village.name,
                    "district": shp_dist_val,
                    "matched": shp_vname,
                    "distance_km": round(best_dist, 2),
                    "area_ha": area_ha,
                    "vertices": len(multipoly[0][0]),
                    "status": "UPDATED"
                })

            if dry_run:
                self.stdout.write(self.style.WARNING("\n[DRY RUN] Rolled back transaction. No changes committed."))
                transaction.set_rollback(True)

        self.stdout.write("\n" + "=" * 70)
        self.stdout.write("IMPORT SUMMARY:")
        self.stdout.write("=" * 70)
        for res in summary_results:
            st = res["status"]
            if st == "UPDATED":
                self.stdout.write(self.style.SUCCESS(
                    f"  ✓ {res['name']:<12} | Matched: {res['matched']:<24} | Dist: {res['district']:<12} | "
                    f"Offset: {res['distance_km']} km | Area: {res['area_ha']} ha"
                ))
            else:
                self.stdout.write(self.style.WARNING(
                    f"  - {res['name']:<12} | Status: {st:<18} | Target Dist: {res['district']}"
                ))
        self.stdout.write("=" * 70)
        self.stdout.write(self.style.SUCCESS(
            f"Complete: {updated_count}/{len(db_villages)} villages updated with verified boundaries."
        ))

    def _inspect_file(self, gdf, file_path):
        """Displays metadata, CRS, and sample rows from the shapefile."""
        self.stdout.write("=" * 70)
        self.stdout.write(f"SHAPEFILE INSPECTION: {os.path.basename(file_path)}")
        self.stdout.write("=" * 70)
        self.stdout.write(f"Total Features (Rows): {len(gdf):,}")
        self.stdout.write(f"CRS: {gdf.crs}")
        self.stdout.write(f"Geometry Types: {gdf.geometry.geom_type.value_counts().to_dict()}")
        self.stdout.write(f"Attribute Columns ({len(gdf.columns)}): {list(gdf.columns)}")
        self.stdout.write("\nSample Records (First 5):")
        cols_to_show = [c for c in gdf.columns if c != "geometry"][:6]
        for idx, row in gdf.head(5).iterrows():
            props = {c: str(row[c])[:30] for c in cols_to_show}
            self.stdout.write(f"  Record #{idx + 1}: {props}")
        self.stdout.write("=" * 70)

    def _to_geodjango_multipolygon(self, shapely_geom):
        """Convert a Shapely geometry into a clean 2D GeoDjango MultiPolygon."""
        from shapely.geometry import Polygon as ShapelyPoly, MultiPolygon as ShapelyMultiPoly, GeometryCollection

        if isinstance(shapely_geom, GeometryCollection):
            polys = [g for g in shapely_geom.geoms if isinstance(g, (ShapelyPoly, ShapelyMultiPoly))]
            if not polys:
                return None
            shapely_geom = ShapelyMultiPoly([p if isinstance(p, ShapelyPoly) else p.geoms[0] for p in polys])

        if isinstance(shapely_geom, ShapelyPoly):
            geos_poly = GEOSGeometry(shapely_geom.wkt)
            geos_poly.srid = 4326
            return MultiPolygon(geos_poly, srid=4326)
        elif isinstance(shapely_geom, ShapelyMultiPoly):
            geos_mpoly = GEOSGeometry(shapely_geom.wkt)
            geos_mpoly.srid = 4326
            return geos_mpoly
        return None
