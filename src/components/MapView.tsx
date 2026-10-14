import { MapContainer, TileLayer } from 'react-leaflet'

function MapView() {
  return (
    <MapContainer center={[48, 20]} zoom={4} className="h-full w-full">
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
    </MapContainer>
  )
}

export default MapView