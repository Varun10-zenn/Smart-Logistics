/**
 * Shared helper utility for parsing route geometry and normalizing points to [lat, lon] tuples.
 * 
 * Input route_geometry JSON strings can contain arrays of points.
 * Points are stored as:
 * - OSRM: [lon, lat] (standard GeoJSON format: longitude first, latitude second)
 * - Haversine Fallback: [lon, lat] (standardized format: longitude first, latitude second)
 * 
 * This helper guarantees all returned points are formatted as [lat, lon] (Latitude first: ~12.97, Longitude second: ~79.14 for Leaflet & map display).
 */
export function parseRouteGeometry(routeGeometryStr: string | null | undefined): [number, number][] {
  if (!routeGeometryStr) return [];
  try {
    const parsed = JSON.parse(routeGeometryStr);
    if (!Array.isArray(parsed)) return [];

    return parsed
      .filter((pt: any) => Array.isArray(pt) && pt.length >= 2)
      .map((pt: [number, number]) => {
        const val0 = Number(pt[0]);
        const val1 = Number(pt[1]);

        // If val0 is ~79.14 (Longitude) and val1 is ~12.97 (Latitude), swap to [lat, lon]
        if (Math.abs(val0) > Math.abs(val1)) {
          return [val1, val0] as [number, number];
        }
        return [val0, val1] as [number, number];
      });
  } catch (err) {
    console.warn('[routeGeometry] Failed to parse route_geometry:', err);
    return [];
  }
}
