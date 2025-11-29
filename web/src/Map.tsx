import { useEffect } from 'react';
import maplibregl, { Map as MapLibreMap } from 'maplibre-gl';
import useGeoJSON from './hooks/useGeoJSON';
import 'maplibre-gl/dist/maplibre-gl.css';
import { centroid } from '@turf/turf';
import { useMap } from './context/MapContext/MapContext';
import type { FeatureCollection, Geometry, GeoJsonProperties } from 'geojson';

function addMarkers(data: FeatureCollection<Geometry, GeoJsonProperties> | null, map: MapLibreMap) {
    data?.features.forEach(feature => {
        const center = centroid(feature.geometry)
        const popup = new maplibregl.Popup({ offset: 25 }).setHTML(
            `Company Name: ${feature.properties?.company_name || 'N/A'}<br/>
             Entity Type: ${feature.properties?.entity_type || 'N/A'}<br/>
                 `
        );
        new maplibregl.Marker()
            .setLngLat(center.geometry.coordinates as [number, number])
            .setPopup(popup)
            .addTo(map);
    })
}
export default function Map() {
    const geojson = useGeoJSON('/api/geodata');
    const { map } = useMap()
    useEffect(() => {
        if (!(map && geojson)) return
        addMarkers(geojson, map)
        if (!map.getSource('company-locations'))
            map.addSource('company-locations', {
                type: 'geojson',
                data: geojson,
            });

        if (!map.getLayer('company-locations-layer'))
            map.addLayer({
                id: 'company-locations-layer',
                type: 'line',
                source: 'company-locations',
                paint: {
                    'line-color': 'black',
                    'line-width': 1,
                    "line-blur": 0.4,
                },
            })
        if (!map.getLayer('company-locations-fill-layer'))
            map.addLayer({
                id: 'company-locations-fill-layer',
                type: 'fill',
                source: 'company-locations',
                paint: {
                    'fill-color': 'red',
                    'fill-opacity': 0.5,
                }
            });
    }, [map, geojson])

    return (
        <div id="map" className='w-full'></div>
    );
}
