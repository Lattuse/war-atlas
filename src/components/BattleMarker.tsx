import L from 'leaflet'
import { Marker, Popup } from 'react-leaflet'
import markerIcon from 'leaflet/dist/images/marker-icon.png'
import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png'
import markerShadow from 'leaflet/dist/images/marker-shadow.png'
import type { Battle } from '../types/battle'
import BattleCard from './BattleCard'

const battleIcon = L.icon({
  iconUrl: markerIcon,
  iconRetinaUrl: markerIcon2x,
  shadowUrl: markerShadow,
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
})

interface BattleMarkerProps {
  battle: Battle
}

function BattleMarker({ battle }: BattleMarkerProps) {
  const { lat, lng } = battle.coordinates

  return (
    <Marker position={[lat, lng]} icon={battleIcon}>
      <Popup>
        <BattleCard battle={battle} />
      </Popup>
    </Marker>
  )
}

export default BattleMarker