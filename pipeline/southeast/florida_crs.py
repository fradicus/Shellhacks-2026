"""EPSG:6439 to WGS84 through inverse ESRI:108354, for reviewed DEP points.

Parameters: Esri geographic transformations 12.1, page 1841, operation 108354.
Independent source-byte reproduction is recorded in hopkins-location-review.md.
Zero computational ellipsoidal height is a 2D convention, not source elevation.
"""
import math

TRANSFORM = "EPSG:6439 inverse Albers; inverse ESRI:108354; 2D height=0"


def to_wgs84(x: float, y: float) -> tuple[float, float]:
    a = 6378137.0
    flattening = 1 / 298.257222101
    eccentricity_squared = 2 * flattening - flattening * flattening
    eccentricity = math.sqrt(eccentricity_squared)

    def q(phi):
        sine = math.sin(phi)
        return (1 - eccentricity_squared) * (
            sine / (1 - eccentricity_squared * sine * sine)
            - math.log((1 - eccentricity * sine) / (1 + eccentricity * sine)) / (2 * eccentricity))

    def m(phi):
        return math.cos(phi) / math.sqrt(1 - eccentricity_squared * math.sin(phi) ** 2)

    p1, p2, p0 = map(math.radians, [24, 31.5, 24])
    n = (m(p1) ** 2 - m(p2) ** 2) / (q(p2) - q(p1))
    c = m(p1) ** 2 + n * q(p1)
    rho0 = a * math.sqrt(c - n * q(p0)) / n
    dx, dy = x - 400000, rho0 - y
    target = (c - (math.hypot(dx, dy) * n / a) ** 2) / n
    low, high = -math.pi / 2, math.pi / 2
    if not q(low) <= target <= q(high):
        raise ValueError("invalid Florida Albers source point")
    for _ in range(80):
        middle = (low + high) / 2
        if q(middle) < target:
            low = middle
        else:
            high = middle
    lat = (low + high) / 2
    lon = math.radians(-84) + math.atan2(dx, dy) / n
    radius = a / math.sqrt(1 - eccentricity_squared * math.sin(lat) ** 2)
    xyz = [radius * math.cos(lat) * math.cos(lon), radius * math.cos(lat) * math.sin(lon),
           radius * (1 - eccentricity_squared) * math.sin(lat)]
    rx, ry, rz = [math.radians(value / 3600) for value in [0.025915, 0.009426, 0.011599]]
    scale = 1 + 0.00062e-6
    # Solve the inverse of the published forward Coordinate_Frame affine operation.
    matrix = [[scale, scale * rz, -scale * ry, xyz[0] - 0.9956],
              [-scale * rz, scale, scale * rx, xyz[1] + 1.9013],
              [scale * ry, -scale * rx, scale, xyz[2] + 0.5215]]
    for i in range(3):
        divisor = matrix[i][i]
        matrix[i] = [value / divisor for value in matrix[i]]
        for j in range(3):
            if j != i:
                multiplier = matrix[j][i]
                matrix[j] = [u - multiplier * v for u, v in zip(matrix[j], matrix[i], strict=True)]
    gx, gy, gz = [row[3] for row in matrix]
    horizontal = math.hypot(gx, gy)
    wgs_flattening = 1 / 298.257223563
    wgs_e2 = 2 * wgs_flattening - wgs_flattening ** 2
    phi = math.atan2(gz, horizontal * (1 - wgs_e2))
    for _ in range(20):
        radius = a / math.sqrt(1 - wgs_e2 * math.sin(phi) ** 2)
        phi = math.atan2(gz + wgs_e2 * radius * math.sin(phi), horizontal)
    return math.degrees(math.atan2(gy, gx)), math.degrees(phi)
