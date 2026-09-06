"""Stable demonstration geometries for the Live Network Map.

Coordinates are fictional operational sketches around the seeded asset
positions. They do not represent real utility infrastructure.
"""

from shapely.geometry import LineString, MultiPolygon, Point, Polygon

# GeoJSON / PostGIS order is (longitude, latitude).

ZONE_POLYGONS: dict[str, list[tuple[float, float]]] = {
    "Corniche DMA": [
        (54.3356, 24.4748),
        (54.3358, 24.4774),
        (54.3374, 24.4776),
        (54.3386, 24.4766),
        (54.3382, 24.4749),
        (54.3356, 24.4748),
    ],
    "Dubai Harbour": [
        (55.1378, 25.0882),
        (55.1379, 25.0908),
        (55.1404, 25.0910),
        (55.1406, 25.0886),
        (55.1390, 25.0879),
        (55.1378, 25.0882),
    ],
    "Al Ain North": [
        (55.7594, 24.2306),
        (55.7596, 24.2336),
        (55.7626, 24.2338),
        (55.7628, 24.2310),
        (55.7608, 24.2302),
        (55.7594, 24.2306),
    ],
    "Jeddah North": [
        (39.1256, 21.7526),
        (39.1258, 21.7552),
        (39.1282, 21.7554),
        (39.1284, 21.7528),
        (39.1268, 21.7522),
        (39.1256, 21.7526),
    ],
    "Doha West": [
        (51.4888, 25.3728),
        (51.4890, 25.3756),
        (51.4918, 25.3758),
        (51.4920, 25.3732),
        (51.4902, 25.3724),
        (51.4888, 25.3728),
    ],
    "Muscat Old Town": [
        (58.5646, 23.6154),
        (58.5648, 23.6180),
        (58.5674, 23.6182),
        (58.5676, 23.6158),
        (58.5658, 23.6150),
        (58.5646, 23.6154),
    ],
    "Casablanca Medina": [
        (-7.6176, 33.5982),
        (-7.6174, 33.6006),
        (-7.6150, 33.6008),
        (-7.6148, 33.5986),
        (-7.6164, 33.5978),
        (-7.6176, 33.5982),
    ],
    "Riyadh Industrial": [
        (46.9036, 24.5338),
        (46.9038, 24.5364),
        (46.9064, 24.5366),
        (46.9066, 24.5340),
        (46.9048, 24.5332),
        (46.9036, 24.5338),
    ],
    "Amman Heights": [
        (35.9094, 31.9622),
        (35.9096, 31.9648),
        (35.9118, 31.9650),
        (35.9120, 31.9626),
        (35.9104, 31.9618),
        (35.9094, 31.9622),
    ],
}

SEGMENT_PATHS: dict[str, list[tuple[float, float]]] = {
    "Corniche Trunk Main · KM 4.2": [
        (54.3362, 24.4754),
        (54.3364, 24.4758),
        (54.3368, 24.4760),
        (54.3371, 24.4762),
        (54.3376, 24.4755),
        (54.3378, 24.4768),
    ],
    "Harbour Transfer Main · Segment 7": [
        (55.1386, 25.0888),
        (55.1389, 25.0891),
        (55.1392, 25.0894),
        (55.1398, 25.0900),
        (55.1386, 25.0901),
    ],
    "Al Ain Feeder 3": [
        (55.7602, 24.2314),
        (55.7610, 24.2318),
        (55.7614, 24.2321),
        (55.7620, 24.2328),
    ],
    "Obhur Feeder · Node 12": [
        (39.1265, 21.7534),
        (39.1268, 21.7536),
        (39.1272, 21.7540),
        (39.1275, 21.7544),
    ],
    "Lusail Distributor 2": [
        (51.4898, 25.3736),
        (51.4902, 25.3740),
        (51.4906, 25.3742),
        (51.4912, 25.3748),
    ],
    "Mutrah Distributor": [
        (58.5655, 23.6170),
        (58.5659, 23.6162),
        (58.5662, 23.6164),
        (58.5668, 23.6172),
    ],
    "Medina Ring Main · Arc B": [
        (-7.6164, 33.5993),
        (-7.6160, 33.5990),
        (-7.6158, 33.5998),
        (-7.6168, 33.5996),
        (-7.6164, 33.5993),
    ],
    "Second Industrial Ring": [
        (46.9044, 24.5354),
        (46.9048, 24.5346),
        (46.9051, 24.5348),
        (46.9056, 24.5356),
        (46.9044, 24.5354),
    ],
    "Abdali Trunk": [
        (35.9102, 31.9631),
        (35.9106, 31.9634),
        (35.9110, 31.9639),
    ],
}


def zone_multipolygon(zone_name: str) -> MultiPolygon:
    ring = ZONE_POLYGONS[zone_name]
    return MultiPolygon([Polygon(ring)])


def segment_linestring(segment_name: str) -> LineString:
    return LineString(SEGMENT_PATHS[segment_name])


def asset_point(longitude: float, latitude: float) -> Point:
    return Point(longitude, latitude)
