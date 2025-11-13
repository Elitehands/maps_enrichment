import { useRef, useEffect, useState } from 'react';
import maplibregl, { Map as MapLibreMap } from 'maplibre-gl';
import type { FeatureCollection, Geometry } from 'geojson';
import 'maplibre-gl/dist/maplibre-gl.css';
import { centroid } from '@turf/turf';

async function fetchGeojsonData(url: string): Promise<FeatureCollection<Geometry>> {
    try {
        const response = await fetch(url);
        const data = await response.json();
        return data as FeatureCollection<Geometry>;
    }
    catch (e) {
        console.error("Failed to fetch geojson data:", e);
        throw e;
    }
}

function useGeoJSON(url: string) {
    const [data, setData] = useState<FeatureCollection<Geometry> | null>(null);
    useEffect(() => {
        fetchGeojsonData(url)
            .then(fetchedData => setData(fetchedData))
            .catch(error => console.error("Error loading geojson data:", error));
    }, [url]);
    return data;
}

function useMap(map: MapLibreMap | null, callbackfn: (map: MapLibreMap) => void) {
    useEffect(() => {
        // Early return if map is null
        if (!map) return;

        const onload = () => callbackfn(map);
        map.on('load', onload);

        return () => { map.off('load', onload); };
    }, [map, callbackfn]);
}

export default function Map() {
    const libreMapRef = useRef<MapLibreMap | null>(null);
    const mapElementRef = useRef<HTMLDivElement | null>(null);
    const mapStyle = 'https://raw.githubusercontent.com/go2garret/maps/main/src/assets/json/openStreetMap.json';
    const geojson = useGeoJSON('http://localhost:8000/geodata');


    useMap(libreMapRef.current, (map) => {
        geojson?.features.forEach((feature) => {
            const center = centroid(feature as any);
            const popup = new maplibregl.Popup({ offset: 25 }).setHTML(
                `Company Name: ${feature.properties?.company_name || 'N/A'}<br/>
                 Entity Type: ${feature.properties?.entity_type || 'N/A'}<br/>
                 Country: ${feature.properties?.country || 'N/A'}`
            );
            new maplibregl.Marker()
                .setLngLat(center.geometry.coordinates as [number, number])
                .setPopup(popup)
                .addTo(map);

        })
    })

    useEffect(function () {
        if (libreMapRef.current || !mapElementRef.current) return;

        libreMapRef.current = new maplibregl.Map({
            container: mapElementRef.current,
            style: mapStyle,
            center: [-2.5, 54.0],
            zoom: 5,
        });

        libreMapRef.current.addControl(new maplibregl.NavigationControl(), 'top-right');

        return () => {
            libreMapRef.current?.remove();
            libreMapRef.current = null;
        };
    }, []);


    useMap(libreMapRef.current, (map) => {
        if (geojson) {
            map.addSource('company-locations', {
                type: 'geojson',
                data: geojson,
            });
            map.addLayer({
                id: 'company-locations-layer',
                type: 'line',
                source: 'company-locations',
                paint: {
                    'line-color': 'grey',
                    'line-width': 1.5,
                }
            })
            map.addLayer({
                id: 'company-locations-fill-layer',
                type: 'fill',
                source: 'company-locations',
                paint: {
                    'fill-color': 'blue',
                    'fill-opacity': 0.1,
                }
            });
        }

    });

    return (
        <div
            ref={mapElementRef}
            id="map"
            className="w-screen h-screen"
        />
    );
}
