import type { Battle } from '../types/battle'

interface BattleCardProps {
  battle: Battle
}

function BattleCard({ battle }: BattleCardProps) {
  return (
    <div className="rounded-lg border border-gray-200 p-4 shadow-sm">
      <h2 className="text-xl font-semibold">{battle.name}</h2>
      <p className="text-sm text-gray-500">
        {battle.war} · {battle.startYear === battle.endYear ? battle.startYear : `${battle.startYear}-${battle.endYear}`}
      </p>
      <p className="mt-2 text-sm">{battle.outcome}</p>
    </div>
  )
}

export default BattleCard