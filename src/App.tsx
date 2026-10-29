import { useState } from 'react'
import battlesData from './data/battles.json'
import type { Battle } from './types/battle'
import type { YearRange } from './types/timeline'
import MapView from './components/MapView'
import TimelineSlider from './components/TimelineSlider'

const battles: Battle[] = battlesData

const minYear = Math.min(...battles.map((battle) => battle.startYear))
const maxYear = Math.max(...battles.map((battle) => battle.endYear))

function App() {
  const [range, setRange] = useState<YearRange>({ from: minYear, to: maxYear })

  const visibleBattles = battles.filter(
    (battle) => battle.startYear <= range.to && battle.endYear >= range.from,
  )

  return (
    <div className="flex h-screen flex-col">
      <header className="space-y-3 p-4">
        <h1 className="text-2xl font-bold text-blue-600">War Atlas</h1>
        <TimelineSlider range={range} min={minYear} max={maxYear} onChange={setRange} />
      </header>
      <main className="flex-1">
        <MapView battles={visibleBattles} />
      </main>
    </div>
  )
}

export default App