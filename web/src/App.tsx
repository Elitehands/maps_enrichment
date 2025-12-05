import { MapContextWrapper } from './context/MapContext/MapContext'
import './index.css'
import Map from './Map'
import Sidebar from './Sidebar'

export default function App() {
  const style = 'https://api.maptiler.com/maps/dataviz-v4/style.json?key=YO2kLvJC32plHgHYih5v';
  const focus: [number, number] = [0.1276, 51.5072]
  const zoom = 1
  return (
    <MapContextWrapper id='map' center={focus} style={style} zoom={zoom}>
      <div className='flex flex-row-reverse'>
        <Sidebar />
        <Map />
      </div>
    </MapContextWrapper>
  )
}
