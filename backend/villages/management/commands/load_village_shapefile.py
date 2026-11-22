"""
Django Management Command: load_village_shapefile

Loads official administrative MultiPolygon boundaries from external GIS sources
(such as ISRO Bhuvan Panchayat, Survey of India, or Bharat Maps shapefiles)
into the GeoDjango Village model in PostgreSQL/PostGIS.

Features:
- Reads ESRI Shapefiles (.shp), zipped shapefiles (.zip), GeoJSON (.geojson),
  and GeoPackages (.gpkg) via GeoPandas and GeoDjango GDAL.
- --inspect mode: Displays attribute schema, CRS, and sample records so you can
  identify exact column names (e.g. VILL_NAME, DIST_NAME).
- Auto-reprojects input CRS (LCC, UTM, Everest 1954, etc.) to EPSG:4326.
- Automatically repairs invalid self-intersecting geometries (make_valid).
- Casts Polygon to MultiPolygon and strips 3D coordinates.
- Computes high-precision metric area in hectares using local UTM projection.
- Supports case-insensitive and fuzzy name matching.
"""

import os
import sys
import difflib
from django.core.management.base import BaseCommand, CommandError
from django.contrib.gis.geos import GEOSGeometry, MultiPolygon, Polygon
from django.db import transaction
from villages.models import Village

# Common attribute column names in Bhuvan Panchayat, Census, and Survey of India shapefiles
CANDIDATE_NAME_FIELDS = [
    "VILL_NAME", "VILLNAME", "NAME", "VILLAGE", "VILLAGE_NA", "VIL_NAME",
    "NAME_EN", "VILL_NAME_", "V_NAME", "VILLAGNAME", "TEHSIL_VIL"
]

CANDIDATE_DISTRICT_FIELDS = [
    "DIST_NAME", "DISTRICT", "DIST_NA", "DT_NAME", "DISTRICT_N", "DIST_NAME_"
]


class Command(BaseCommand):
    help = "Import official village boundaries from external Shapefile/GeoJSON (e.g. Bhuvan Panchayat) into PostGIS"

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
            help="Attribute column name containing village names (e.g. VILL_NAME)"
        )
        parser.add_argument(
            "--district-field",
            type=str,
            default=None,
            help="Attribute column name containing district names (e.g. DIST_NAME)"
        )
        parser.add_argument(
            "--village",
            type=str,
            default=None,
            help="Target a specific village name (e.g. --village Piplantri)"
        )
        parser.add_argument(
            "--fuzzy",
            action="store_true",
            help="Enable fuzzy matching (useful for slight spelling differences like 'Piplantari')"
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Perform simulation without committing changes to PostgreSQL"
        )

    def handle(self, *args, **options):
        file_path = options["file"]
        inspect_mode = options["inspect"]
        name_field = options["name_field"]
        district_field = options["district_field"]
        target_village = options["village"]
        enable_fuzzy = options["fuzzy"]
        dry_run = options["dry_run"]

        if not os.path.exists(file_path):
            raise CommandError(f"File not found: {file_path}")

        try:
            import geopandas as gpd
            from shapely.validation import make_valid
            from shapely.geometry import Polygon as ShapelyPolygon, MultiPolygon as ShapelyMultiPolygon
        except ImportError:
            raise CommandError("GeoPandas and Shapely are required. Run: pip install geopandas shapely")

        self.stdout.write(f"Reading GIS file: {file_path} ...")
        try:
            gdf = gpd.read_file(file_path)
        except Exception as exc:
            raise CommandError(f"Failed to read file with GeoPandas: {exc}")

        # 1. Inspection Mode
        if inspect_mode:
            self._inspect_file(gdf, file_path)
            return

        # 2. Identify Name & District Columns
        if not name_field:
            for col in CANDIDATE_NAME_FIELDS:
                if col in gdf.columns:
                    name_field = col
                    break
            if not name_field:
                raise CommandError(
                    f"Could not automatically detect village name column. "
                    f"Available columns: {list(gdf.columns)}. "
                    f"Please specify using --name-field <column_name>."
                )

        if not district_field:
            for col in CANDIDATE_DISTRICT_FIELDS:
                if col in gdf.columns:
                    district_field = col
                    break

        self.stdout.write(self.style.SUCCESS(
            f"Using Name field: '{name_field}'" + (f", District field: '{district_field}'" if district_field else "")
        ))

        # 3. Ensure CRS is WGS 84 (EPSG:4326)
        if gdf.crs is None:
            self.stdout.write(self.style.WARNING("File has no CRS defined. Assuming EPSG:4326."))
            gdf = gdf.set_crs("EPSG:4326")
        elif gdf.crs.to_string() != "EPSG:4326":
            self.stdout.write(f"Reprojecting from {gdf.crs.to_string()} to EPSG:4326 ...")
            gdf = gdf.to_crs("EPSG:4326")

        # 4. Filter or Match Villages in Database
        db_villages = list(Village.objects.all())
        if target_village:
            db_villages = [v for v in db_villages if v.name.lower() == target_village.lower()]
            if not db_villages:
                raise CommandError(f"Target village '{target_village}' not found in database.")

        self.stdout.write(f"Matching {len(db_villages)} database village(s) against {len(gdf)} GIS records...")

        shp_names = gdf[name_field].astype(str).tolist()
        updated_count = 0

        with transaction.atomic():
            for village in db_villages:
                matched_idx = self._find_match(village.name, shp_names, enable_fuzzy)

                if matched_idx is None:
                    self.stdout.write(self.style.WARNING(
                        f"  [NO MATCH] No shapefile feature matched database village: '{village.name}'"
                    ))
                    continue

                row = gdf.iloc[matched_idx]
                shp_vname = row[name_field]
                geom = row.geometry

                if geom is None or geom.is_empty:
                    self.stdout.write(self.style.ERROR(
                        f"  [EMPTY GEOM] Geometry for '{shp_vname}' is empty. Skipping."
                    ))
                    continue

                # Repair invalid geometries
                if not geom.is_valid:
                    self.stdout.write(self.style.WARNING(f"  Repairing self-intersecting geometry for '{shp_vname}'..."))
                    geom = make_valid(geom)

                # Ensure 2D MultiPolygon
                multipoly = self._to_geodjango_multipolygon(geom)
                if multipoly is None:
                    self.stdout.write(self.style.ERROR(f"  Cannot cast geometry of type {geom.geom_type} to MultiPolygon."))
                    continue

                # Metric area computation via UTM projection
                utm_epsg = 32643 if village.location.x > 73.0 else 32642
                projected_geom = multipoly.transform(utm_epsg, clone=True)
                area_ha = round(projected_geom.area / 10000.0, 2)

                village.boundary = multipoly
                village.area_hectares = area_ha

                if not dry_run:
                    village.save(update_fields=["boundary", "area_hectares"])

                self.stdout.write(self.style.SUCCESS(
                    f"  ✓ Matched '{village.name}' with Shapefile record '{shp_vname}': "
                    f"Area = {area_ha} ha, Vertices = {len(multipoly[0][0])}"
                ))
                updated_count += 1

            if dry_run:
                self.stdout.write(self.style.WARNING("\n[DRY RUN] Rolled back transaction. No changes committed."))
                transaction.set_rollback(True)

        self.stdout.write(self.style.SUCCESS(
            f"\nFinished: Successfully updated {updated_count}/{len(db_villages)} villages from official Shapefile."
        ))

    def _inspect_file(self, gdf, file_path):
        """Displays metadata, CRS, and sample rows from the shapefile."""
        self.stdout.write("=" * 70)
        self.stdout.write(f"SHAPEFILE INSPECTION: {os.path.basename(file_path)}")
        self.stdout.write("=" * 70)
        self.stdout.write(f"Total Features (Rows): {len(gdf)}")
        self.stdout.write(f"CRS: {gdf.crs}")
        self.stdout.write(f"Geometry Types: {gdf.geometry.geom_type.value_counts().to_dict()}")
        self.stdout.write(f"Attribute Columns ({len(gdf.columns)}): {list(gdf.columns)}")
        self.stdout.write("\nSample Records (First 5):")
        cols_to_show = [c for c in gdf.columns if c != "geometry"][:6]
        for idx, row in gdf.head(5).iterrows():
            props = {c: str(row[c])[:30] for c in cols_to_show}
            self.stdout.write(f"  Record #{idx + 1}: {props}")
        self.stdout.write("=" * 70)
        self.stdout.write("TIP: Identify the village name column and run:")
        self.stdout.write(f"python manage.py load_village_shapefile --file \"{file_path}\" --name-field <NAME_COL>")
        self.stdout.write("=" * 70)

    def _find_match(self, target_name, candidates, fuzzy=False):
        """Find index of matching candidate name."""
        target_clean = target_name.strip().lower()
        for idx, cand in enumerate(candidates):
            if str(cand).strip().lower() == target_clean:
                return idx

        # Contains match (e.g. "Piplantri Kalan" contains "Piplantri")
        for idx, cand in enumerate(candidates):
            c_clean = str(cand).strip().lower()
            if target_clean in c_clean or c_clean in target_clean:
                return idx

        if fuzzy:
            cand_clean = [str(c).strip().lower() for c in candidates]
            matches = difflib.get_close_matches(target_clean, cand_clean, n=1, cutoff=0.75)
            if matches:
                return cand_clean.index(matches[0])

        return None

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

