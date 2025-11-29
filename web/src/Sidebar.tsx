import Location from './Location'
import Nestle from '/Nestle.svg'
import useGeoJSON from './hooks/useGeoJSON'
import { centroid } from '@turf/turf'
import { useMap } from './context/MapContext/MapContext'

export default function Sidebar() {
    const { map } = useMap()
    const data = useGeoJSON('/api/geodata')
    const locations = data?.features.map((feature, index) => (
        <Location
            key={index}
            name={feature.properties?.company_name || 'N/A'}
            type={feature.properties?.entity_type || 'N/A'}
            country={feature.properties?.address || 'N/A'}
            clickHandler={() => {
                const center = centroid(feature as any);
                const [lng, lat] = center.geometry.coordinates as [number, number];
                map?.flyTo({
                    zoom: 15,
                    duration: 1500,
                    center: [lng, lat],
                })
            }}
        />
    ))
    return (
        <section className="h-screen w-1/2 overflow-hidden">
            <header className='flex flex-col gap-1 justify-center p-8 items-center border-b border-gray-200'>
                <img src={Nestle} alt="Nestle-Logo" className='h-16' />
                <p className='text-gray-500'>Nestlé Corporate Locations POC</p>
            </header>
            <div className="overflow-y-auto h-full scrollbar-hidden">
                {locations}
            </div>
        </section>
    )
}
