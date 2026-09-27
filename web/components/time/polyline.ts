type LatLon = { lat: number; lon: number };

/** Decode an encoded polyline (precision 5, as stored by the route fetch) into [lng, lat] pairs. */
export function decodePolyline(encoded: string, precision = 5): [number, number][] {
  const factor = 10 ** precision;
  const out: [number, number][] = [];
  let i = 0;
  let lat = 0;
  let lng = 0;
  const next = () => {
    let shift = 0;
    let result = 0;
    let byte: number;
    do {
      byte = encoded.charCodeAt(i++) - 63;
      result |= (byte & 0x1f) << shift;
      shift += 5;
    } while (byte >= 0x20 && i < encoded.length);
    return result & 1 ? ~(result >> 1) : result >> 1;
  };
  while (i < encoded.length) {
    lat += next();
    lng += next();
    out.push([lng / factor, lat / factor]);
  }
  return out;
}

/** The ground path of a routed pair: center A, the route's snapped start, the stored road, its snapped end, center B.
 * Null without a stored polyline, so the caller keeps the straight link. */
export function roadPath(
  a: LatLon,
  b: LatLon,
  route: { polyline: string | null; start?: LatLon | null; end?: LatLon | null } | null | undefined,
): [number, number][] | null {
  if (!route?.polyline) return null;
  const road = decodePolyline(route.polyline);
  if (!road.length) return null;
  const at = (p: LatLon): [number, number] => [p.lon, p.lat];
  const path = [at(a), ...(route.start ? [at(route.start)] : []), ...road, ...(route.end ? [at(route.end)] : []), at(b)];
  return path.filter((p, k) => k === 0 || p[0] !== path[k - 1][0] || p[1] !== path[k - 1][1]);
}
