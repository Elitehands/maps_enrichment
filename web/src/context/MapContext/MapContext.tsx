import React, { createContext, useContext, useEffect, useRef, useState } from "react";
import maplibregl, { Map as MapLibreMap } from "maplibre-gl";

interface MapContextType {
    map: MapLibreMap | null
    loading: boolean
}

const MapContext = createContext<MapContextType>({ map: null, loading: true });

interface MapProviderProps {
    id: string;
    style?: string;
    center?: [number, number];
    zoom?: number;
    children: React.ReactNode;
}

export const MapContextWrapper: React.FC<MapProviderProps> = ({ id, style, center, zoom, children, }) => {
    const map = useRef<MapLibreMap | null>(null);
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        if (!map.current) {
            map.current = new maplibregl.Map({
                container: id,
                style: style || "https://raw.githubusercontent.com/go2garret/maps/main/src/assets/json/openStreetMap.json",
                center: center || [0, 0],
                zoom: zoom || 2,
            });

        }

        map.current.on('load', () => setLoading(false))

        return () => {
            map.current?.remove();
            map.current = null;
        };
    }, [id, style]);

    return <MapContext.Provider value={{ map: map.current, loading: loading }}>{children}</MapContext.Provider>;
};


export const useMap = () => {
    const context = useContext(MapContext);
    if (!context) throw new Error("useMap must be used within a MapProvider");
    return context;
};
