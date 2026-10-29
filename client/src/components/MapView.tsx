import { MapContainer, TileLayer } from 'react-leaflet'
import type { Battle } from '../types/battle'
import BattleMarker from './BattleMarker'

interface MapViewProps {
  battles: Battle[]
}

function MapView({ battles }: MapViewProps) {
  return (
    <MapContainer center={[48, 20]} zoom={4} className="h-full w-full">
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {battles.map((battle) => (
        <BattleMarker key={battle.id} battle={battle} />
      ))}
    </MapContainer>
  )
}

export default MapView