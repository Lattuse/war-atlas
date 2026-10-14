import battlesData from './data/battles.json'
import type { Battle } from './types/battle'
import BattleCard from './components/BattleCard'

const battles: Battle[] = battlesData

function App() {
  return (
    <div className="p-8">
      <h1 className="text-3xl font-bold text-blue-600">War Atlas</h1>
      <div className="mt-4 grid gap-4">
        {battles.map((battle) => (
          <BattleCard key={battle.id} battle={battle} />
        ))}
      </div>
    </div>
  )
}

export default App