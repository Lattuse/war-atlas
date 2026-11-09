import { useCallback, useRef } from 'react'
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
  const popupRef = useRef<L.Popup>(null)

  // Popup content is rendered by React, so Leaflet doesn't notice when it grows
  // (e.g. an AI answer appears). update() re-measures it and pans the map.
  const handleContentResize = useCallback(() => {
    popupRef.current?.update()
  }, [])

  return (
    <Marker position={[lat, lng]} icon={battleIcon}>
      <Popup ref={popupRef} minWidth={280} maxWidth={320}>
        <BattleCard battle={battle} onContentResize={handleContentResize} />
      </Popup>
    </Marker>
  )
}

export default BattleMarker
