import { Tabs } from "radix-ui";
import type { Battle } from "../types/battle";
import { formatYear } from "../utils/formatYear";
import AskBattle from "./AskBattle";

interface BattleCardProps {
  battle: Battle;
  onContentResize?: () => void;
}

const TAB_TRIGGER_CLASS =
  "-mb-px border-b-2 border-transparent px-2 py-1 text-sm text-gray-500 hover:text-gray-800 data-[state=active]:border-blue-600 data-[state=active]:font-medium data-[state=active]:text-gray-900";

// Both panels share a fixed height so the popup doesn't grow when an AI answer
// arrives and doesn't jump under the cursor when switching tabs.
const TAB_PANEL_CLASS = "mt-3 h-60 data-[state=inactive]:hidden";

function BattleCard({ battle, onContentResize }: BattleCardProps) {
  return (
    <div className="rounded-lg border border-gray-200 p-4 shadow-sm">
      <h2 className="text-xl font-semibold">{battle.name}</h2>
      {/* <div> instead of <p>: Leaflet's popup CSS adds large margins to <p> */}
      <div className="text-sm text-gray-500">
        {battle.war} ·{" "}
        {battle.startYear === battle.endYear
          ? formatYear(battle.startYear)
          : `${formatYear(battle.startYear)}–${formatYear(battle.endYear)}`}{" "}
      </div>

      <Tabs.Root defaultValue="info" className="mt-3">
        <Tabs.List
          aria-label="Разделы карточки битвы"
          className="flex gap-2 border-b border-gray-200"
        >
          <Tabs.Trigger value="info" className={TAB_TRIGGER_CLASS}>
            Инфо
          </Tabs.Trigger>
          <Tabs.Trigger value="ask" className={TAB_TRIGGER_CLASS}>
            Спросить AI
          </Tabs.Trigger>
        </Tabs.List>

        <Tabs.Content
          value="info"
          className={`${TAB_PANEL_CLASS} overflow-y-auto text-sm`}
        >
          <div className="font-medium">{battle.outcome}</div>
          <div className="mt-2 text-gray-700">{battle.description}</div>
        </Tabs.Content>

        {/* forceMount keeps the question and answer when switching tabs */}
        <Tabs.Content forceMount value="ask" className={TAB_PANEL_CLASS}>
          <AskBattle battleId={battle.id} onContentResize={onContentResize} />
        </Tabs.Content>
      </Tabs.Root>
    </div>
  );
}

export default BattleCard;
