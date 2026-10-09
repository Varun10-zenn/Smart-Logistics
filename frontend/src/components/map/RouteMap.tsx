import { useEffect, useState } from 'react';
import { MapContainer, TileLayer, Polyline, Marker, Popup, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { MapPin } from 'lucide-react';
import { parseRouteGeometry } from '../../utils/routeGeometry';

// Leaflet default icon fix for Vite bundler
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
});

// Custom HTML Pin Markers using Leaflet divIcon
const createCustomIcon = (color: string, label: string) => {
  return L.divIcon({
    className: 'custom-leaflet-marker',
    html: `<div style="
      background-color: ${color};
      width: 28px;
      height: 28px;
      border-radius: 50%;
      border: 2px solid #FFFFFF;
      box-shadow: 0 4px 12px rgba(0,0,0,0.5);
      display: flex;
      align-items: center;
      justify-content: center;
      color: #FFFFFF;
      font-weight: bold;
      font-size: 11px;
    ">${label}</div>`,
    iconSize: [28, 28],
    iconAnchor: [14, 14],
  });
};

const storeIcon = createCustomIcon('#10B981', 'WH'); // Emerald
const stopIcon = createCustomIcon('#EF4444', 'DEST'); // Red
const riderIcon = createCustomIcon('#F59E0B', 'R'); // Amber

interface RouteMapProps {
  routeGeometry?: string | null;
  storeLat?: number | null;
  storeLon?: number | null;
  storeName?: string;
  destLat?: number | null;
  destLon?: number | null;
  destAddress?: string;
  riderLat?: number | null;
  riderLon?: number | null;
  riderName?: string;
  simStep?: number;
  height?: string;
}

// Map Bounds Auto-Fit Sub-Component
function FitBounds({ points }: { points: [number, number][] }) {
  const map = useMap();
  useEffect(() => {
    if (points.length > 0) {
      const bounds = L.latLngBounds(points);
      map.fitBounds(bounds, { padding: [30, 30] });
    }
  }, [map, points]);
  return null;
}

export function RouteMap({
  routeGeometry,
  storeLat,
  storeLon,
  storeName = 'Warehouse',
  destLat,
  destLon,
  destAddress = 'Delivery Destination',
  riderLat,
  riderLon,
  riderName = 'Rider',
  simStep,
  height = '320px',
}: RouteMapProps) {
  const [tileError, setTileError] = useState(false);

  // Convert and normalize route geometry points to [lat, lon] tuples using shared helper
  const routePoints = parseRouteGeometry(routeGeometry);

  // Derive store location if missing from geometry first point
  const actualStoreLat = storeLat ?? (routePoints.length > 0 ? routePoints[0][0] : 12.9683);
  const actualStoreLon = storeLon ?? (routePoints.length > 0 ? routePoints[0][1] : 79.1522);

  // Determine rider position: from props or simStep
  let currentRiderLat = riderLat;
  let currentRiderLon = riderLon;

  if (routePoints.length > 0 && (currentRiderLat === undefined || currentRiderLat === null)) {
    const stepIdx = simStep !== undefined ? Math.min(simStep, routePoints.length - 1) : 0;
    currentRiderLat = routePoints[stepIdx][0];
    currentRiderLon = routePoints[stepIdx][1];
  }

  // Destination point
  const hasDest = destLat !== undefined && destLat !== null && destLon !== undefined && destLon !== null;

  // Build bounds array for auto-fitting
  const boundsPoints: [number, number][] = [...routePoints];
  if (boundsPoints.length === 0) {
    boundsPoints.push([actualStoreLat, actualStoreLon]);
    if (hasDest) boundsPoints.push([destLat!, destLon!]);
  }

  const defaultCenter: [number, number] = boundsPoints.length > 0 ? boundsPoints[0] : [12.9683, 79.1522];

  // SVG Fallback Canvas Rendering
  const renderSvgFallback = () => {
    let minLat = 90, maxLat = -90, minLon = 180, maxLon = -180;
    const allPts = boundsPoints.length > 0 ? boundsPoints : [[12.9683, 79.1522]];
    allPts.forEach(([lt, ln]) => {
      if (lt < minLat) minLat = lt;
      if (lt > maxLat) maxLat = lt;
      if (ln < minLon) minLon = ln;
      if (ln > maxLon) maxLon = ln;
    });

    const latSpan = maxLat - minLat || 0.01;
    const lonSpan = maxLon - minLon || 0.01;

    const svgPoints = routePoints
      .map(([lt, ln]) => {
        const x = ((ln - minLon) / lonSpan) * 80 + 10;
        const y = 90 - ((lt - minLat) / latSpan) * 80;
        return `${x.toFixed(1)},${y.toFixed(1)}`;
      })
      .join(' ');

    let liveX = 50, liveY = 50;
    if (currentRiderLat !== null && currentRiderLat !== undefined && currentRiderLon !== null && currentRiderLon !== undefined) {
      liveX = ((currentRiderLon - minLon) / lonSpan) * 80 + 10;
      liveY = 90 - ((currentRiderLat - minLat) / latSpan) * 80;
    }

    return (
      <div className="relative w-full h-full bg-[#0F141F] rounded-2xl border border-slate-800 p-4 flex items-center justify-center overflow-hidden">
        {routePoints.length > 0 ? (
          <svg className="w-full h-full" viewBox="0 0 100 100" preserveAspectRatio="none">
            <polyline fill="none" stroke="#38BDF8" strokeWidth="2.5" strokeDasharray="4 2" points={svgPoints} />
            <circle cx={svgPoints.split(' ')[0]?.split(',')[0]} cy={svgPoints.split(' ')[0]?.split(',')[1]} r="3" fill="#10B981" />
            <circle cx={svgPoints.split(' ')[svgPoints.split(' ').length - 1]?.split(',')[0]} cy={svgPoints.split(' ')[svgPoints.split(' ').length - 1]?.split(',')[1]} r="3" fill="#EF4444" />
            <g transform={`translate(${liveX}, ${liveY})`}>
              <circle r="5" fill="#F59E0B" className="animate-ping opacity-75" />
              <circle r="4" fill="#F59E0B" stroke="#FFFFFF" strokeWidth="1" />
            </g>
          </svg>
        ) : (
          <div className="text-center text-slate-500">
            <MapPin size={24} className="mx-auto mb-2 opacity-50" />
            <p className="text-xs">Fallback Route Map View</p>
          </div>
        )}
      </div>
    );
  };

  if (tileError) {
    return <div style={{ height }}>{renderSvgFallback()}</div>;
  }

  return (
    <div style={{ height }} className="relative w-full rounded-2xl overflow-hidden border border-slate-800 shadow-xl z-0">
      <MapContainer
        center={defaultCenter}
        zoom={13}
        scrollWheelZoom={false}
        style={{ width: '100%', height: '100%', backgroundColor: '#0B0F17' }}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          eventHandlers={{
            tileerror: () => setTileError(true),
          }}
        />

        {boundsPoints.length > 0 && <FitBounds points={boundsPoints} />}

        {/* Route Polyline */}
        {routePoints.length > 0 && (
          <Polyline
            positions={routePoints}
            pathOptions={{ color: '#38BDF8', weight: 4, opacity: 0.85, dashArray: '6, 6' }}
          />
        )}

        {/* Store Marker */}
        <Marker position={[actualStoreLat, actualStoreLon]} icon={storeIcon}>
          <Popup className="leaflet-popup-dark">
            <div className="text-xs font-sans">
              <strong className="text-emerald-600 block">{storeName}</strong>
              <span className="text-slate-500">Warehouse Origin Hub</span>
            </div>
          </Popup>
        </Marker>

        {/* Destination Marker (This Customer's Stop Only) */}
        {hasDest && (
          <Marker position={[destLat!, destLon!]} icon={stopIcon}>
            <Popup className="leaflet-popup-dark">
              <div className="text-xs font-sans">
                <strong className="text-red-600 block">Delivery Destination</strong>
                <span className="text-slate-600">{destAddress}</span>
              </div>
            </Popup>
          </Marker>
        )}

        {/* Rider Live Location Marker */}
        {currentRiderLat !== undefined && currentRiderLat !== null && currentRiderLon !== undefined && currentRiderLon !== null && (
          <Marker position={[currentRiderLat, currentRiderLon]} icon={riderIcon}>
            <Popup className="leaflet-popup-dark">
              <div className="text-xs font-sans">
                <strong className="text-amber-600 block">{riderName}</strong>
                <span className="text-slate-500">Live Courier Position</span>
              </div>
            </Popup>
          </Marker>
        )}
      </MapContainer>

      {/* Map Legend Overlay */}
      <div className="absolute bottom-3 right-3 z-[1000] bg-slate-900/90 border border-slate-800 rounded-xl px-3 py-1.5 text-[10px] text-slate-300 font-mono flex items-center gap-3 backdrop-blur shadow-lg">
        <span className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 inline-block" /> Store
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-amber-500 inline-block animate-pulse" /> Rider
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-red-500 inline-block" /> Destination
        </span>
      </div>
    </div>
  );
}
