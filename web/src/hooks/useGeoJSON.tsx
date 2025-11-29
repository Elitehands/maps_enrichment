import type { FeatureCollection, Geometry } from "geojson";
import { useState, useEffect } from "react";


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
export default function useGeoJSON(url: string) {
    const [data, setData] = useState<FeatureCollection<Geometry> | null>(null);
    useEffect(() => {
        fetchGeojsonData(url)
            .then(fetchedData => setData(fetchedData))
            .catch(error => console.error("Error loading geojson data:", error));
    }, [url]);
    return data;
}