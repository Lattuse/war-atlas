import MapView from './components/MapView'

function App() {
  return (
    <div className="flex h-screen flex-col">
      <header className="p-4">
        <h1 className="text-2xl font-bold text-blue-600">War Atlas</h1>
      </header>
      <main className="flex-1">
        <MapView />
      </main>
    </div>
  )
}

export default App