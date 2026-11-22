import json
from rest_framework import serializers
from django.contrib.gis.geos import Point, MultiPolygon, Polygon, GEOSGeometry
from django.contrib.gis.geos.error import GEOSException
from .models import Village


class GeometryJSONField(serializers.Field):
    """
    Serializes a GeoDjango GEOSGeometry into a standard GeoJSON geometry object,
    and deserializes GeoJSON dicts, coordinate tuples [lng, lat], or WKT strings into GEOSGeometry.
    """
    def to_representation(self, value):
        if value is None:
            return None
        if hasattr(value, 'geojson'):
            return json.loads(value.geojson)
        return None

    def to_internal_value(self, data):
        if data is None or data == '':
            return None

        # Direct GEOSGeometry instance
        if isinstance(data, GEOSGeometry):
            return data

        # GeoJSON geometry dictionary
        if isinstance(data, dict):
            try:
                geom_json_str = json.dumps(data)
                geom = GEOSGeometry(geom_json_str)
                if geom.srid is None or geom.srid == 0:
                    geom.srid = 4326
                return geom
            except (GEOSException, ValueError, TypeError) as exc:
                raise serializers.ValidationError(f"Invalid GeoJSON geometry structure: {exc}")

        # String representation (GeoJSON JSON string or WKT)
        if isinstance(data, str):
            try:
                geom = GEOSGeometry(data.strip())
                if geom.srid is None or geom.srid == 0:
                    geom.srid = 4326
                return geom
            except (GEOSException, ValueError, TypeError) as exc:
                raise serializers.ValidationError(f"Invalid geometry string / WKT: {exc}")

        # Coordinate list/tuple: [longitude, latitude]
        if isinstance(data, (list, tuple)):
            if len(data) != 2:
                raise serializers.ValidationError("Point coordinates must contain exactly [longitude, latitude].")
            try:
                lng = float(data[0])
                lat = float(data[1])
            except (ValueError, TypeError):
                raise serializers.ValidationError("Coordinates must be valid numbers.")

            if not (-180.0 <= lng <= 180.0):
                raise serializers.ValidationError(f"Longitude {lng} is out of valid range [-180, 180].")
            if not (-90.0 <= lat <= 90.0):
                raise serializers.ValidationError(f"Latitude {lat} is out of valid range [-90, 90].")

            return Point(lng, lat, srid=4326)

        raise serializers.ValidationError("Geometry data must be a GeoJSON object, WKT string, or [lng, lat] coordinate array.")


class VillageSerializer(serializers.ModelSerializer):
    """
    Serializer for Village spatial model.
    Accepts coordinates as GeoJSON geometry, coordinate array, WKT, or separate latitude/longitude fields.
    Outputs GeoJSON spatial geometries alongside standard coordinate and attribute fields.
    """
    location = GeometryJSONField(required=False, help_text="GeoJSON Point, [lng, lat], or WKT")
    boundary = GeometryJSONField(required=False, allow_null=True, help_text="GeoJSON MultiPolygon or WKT")
    latitude = serializers.FloatField(required=False, allow_null=True)
    longitude = serializers.FloatField(required=False, allow_null=True)

    class Meta:
        model = Village
        fields = [
            'id',
            'name',
            'district',
            'state',
            'location',
            'latitude',
            'longitude',
            'boundary',
            'area_hectares',
            'population',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        if instance.location:
            ret['latitude'] = round(instance.location.y, 6)
            ret['longitude'] = round(instance.location.x, 6)
        else:
            ret['latitude'] = None
            ret['longitude'] = None
        return ret

    def validate(self, attrs):
        lat = attrs.pop('latitude', None)
        lng = attrs.pop('longitude', None)
        location = attrs.get('location')

        # 1. Coordinate fields (latitude, longitude) validation
        if lat is not None or lng is not None:
            if lat is None or lng is None:
                raise serializers.ValidationError("Both 'latitude' and 'longitude' must be provided together.")
            try:
                lat = float(lat)
                lng = float(lng)
            except (ValueError, TypeError):
                raise serializers.ValidationError("Latitude and longitude must be valid floating-point numbers.")

            if not (-90.0 <= lat <= 90.0):
                raise serializers.ValidationError({"latitude": f"Latitude {lat} is invalid. Must be between -90 and 90."})
            if not (-180.0 <= lng <= 180.0):
                raise serializers.ValidationError({"longitude": f"Longitude {lng} is invalid. Must be between -180 and 180."})

            attrs['location'] = Point(lng, lat, srid=4326)

        # 2. Location geometry validation
        elif location is not None:
            if not isinstance(location, Point):
                raise serializers.ValidationError({"location": "The location field must be a Point geometry."})
            if not (-90.0 <= location.y <= 90.0):
                raise serializers.ValidationError({"location": f"Latitude {location.y} is invalid. Must be between -90 and 90."})
            if not (-180.0 <= location.x <= 180.0):
                raise serializers.ValidationError({"location": f"Longitude {location.x} is invalid. Must be between -180 and 180."})

        # 3. Location required for creation
        elif self.instance is None and 'location' not in attrs:
            raise serializers.ValidationError("Geographic location is required. Provide 'location' or both 'latitude' and 'longitude'.")

        # 4. Boundary geometry validation
        boundary = attrs.get('boundary')
        if boundary is not None:
            if isinstance(boundary, Polygon):
                attrs['boundary'] = MultiPolygon(boundary, srid=4326)
            elif not isinstance(boundary, MultiPolygon):
                raise serializers.ValidationError({"boundary": "The boundary must be a Polygon or MultiPolygon geometry."})

        return attrs

