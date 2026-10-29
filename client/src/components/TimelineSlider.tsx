import { Slider } from 'radix-ui'
import type { YearRange } from '../types/timeline'
import { formatYear } from '../utils/formatYear'

interface TimelineSliderProps {
  range: YearRange
  min: number
  max: number
  onChange: (range: YearRange) => void
}

const thumbClass =
  'block size-5 rounded-full border-2 border-blue-600 bg-white shadow focus:outline-none focus-visible:ring-4 focus-visible:ring-blue-200'

function TimelineSlider({ range, min, max, onChange }: TimelineSliderProps) {
  return (
    <div className="space-y-3">
      <p className="text-sm font-medium">
        Период: {formatYear(range.from)} — {formatYear(range.to)}
      </p>
      <div className="flex items-center gap-4">
        <span className="text-sm text-gray-500">{formatYear(min)}</span>
        <Slider.Root
          className="relative flex h-5 flex-1 touch-none select-none items-center"
          min={min}
          max={max}
          step={1}
          value={[range.from, range.to]}
          onValueChange={([from, to]) => onChange({ from, to })}
        >
          <Slider.Track className="relative h-1.5 grow rounded-full bg-gray-200">
            <Slider.Range className="absolute h-full rounded-full bg-blue-600" />
          </Slider.Track>
          <Slider.Thumb className={thumbClass} aria-label="Начало периода" />
          <Slider.Thumb className={thumbClass} aria-label="Конец периода" />
        </Slider.Root>
        <span className="text-sm text-gray-500">{formatYear(max)}</span>
      </div>
    </div>
  )
}

export default TimelineSlider