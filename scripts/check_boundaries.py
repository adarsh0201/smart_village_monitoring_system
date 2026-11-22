import os
import json

geojson_path = os.path.join(os.path.dirname(__file__), "..", "data", "boundaries", "rajasthan_pilot_villages.geojson")
geojson_path = os.path.abspath(geojson_path)

if not os.path.exists(geojson_path):
    print(f"Error: Boundary file not found at {geojson_path}")
    exit(1)

with open(geojson_path, "r", encoding="utf-8") as f:
    data = json.load(f)

print("=" * 80)
print(f"{'VILLAGE':<12} | {'OFFICIAL':<9} | {'VERTICES':<9} | {'AREA (HA)':<10} | {'SOURCE'}")
print("=" * 80)

for f in data.get("features", []):
    props = f.get("properties", {})
    geom = f.get("geometry", {})
    name = props.get("name", "Unknown")
    is_official = str(props.get("is_official", False))
    area = str(props.get("area_hectares", "N/A"))
    source = props.get("source", "Unknown")
    
    # Calculate vertices count
    coords = geom.get("coordinates", [])
    if geom.get("type") == "MultiPolygon" and coords:
        vertices = len(coords[0][0])
    elif geom.get("type") == "Polygon" and coords:
        vertices = len(coords[0])
    else:
        vertices = 0

    print(f"{name:<12} | {is_official:<9} | {vertices:<9} | {area:<10} | {source}")

print("=" * 80)
print("NOTE: Official=False and Vertices=13 means OpenStreetMap only had Point coordinates,")
print("so a 12-sided fallback cadastral boundary was generated to prevent pipeline failure.")
print("=" * 80)

