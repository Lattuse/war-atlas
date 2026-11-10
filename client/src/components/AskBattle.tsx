import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { askBattle, AskBattleError } from '../api/askBattle'

interface AskBattleProps {
  battleId: string
  onContentResize?: () => void
}

const SUGGESTED_QUESTIONS = ['Почему победила эта сторона?', 'Какие были последствия?']

const MIN_LENGTH = 3
const MAX_LENGTH = 500

function AskBattle({ battleId, onContentResize }: AskBattleProps) {
  const [question, setQuestion] = useState('')
  const [answer, setAnswer] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)

  useEffect(() => {
    onContentResize?.()
  }, [answer, error, isLoading, onContentResize])

  const trimmed = question.trim()
  const canSubmit = !isLoading && trimmed.length >= MIN_LENGTH

  async function submit(text: string) {
    setIsLoading(true)
    setError(null)
    setAnswer(null)
    try {
      setAnswer(await askBattle(battleId, text))
    } catch (err) {
      setError(err instanceof AskBattleError ? err.message : 'Что-то пошло не так')
    } finally {
      setIsLoading(false)
    }
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    if (canSubmit) void submit(trimmed)
  }

  function handleSuggestion(text: string) {
    setQuestion(text)
    void submit(text)
  }

  return (
    // Fills the fixed-height tab panel; only the answer area scrolls.
    // <div> instead of <p>: Leaflet's `.leaflet-popup-content p` margin is
    // unlayered CSS and would override Tailwind's spacing utilities.
    <div className="flex h-full flex-col">
      <div className="flex flex-wrap gap-1">
        {SUGGESTED_QUESTIONS.map((text) => (
          <button
            key={text}
            type="button"
            disabled={isLoading}
            onClick={() => handleSuggestion(text)}
            className="rounded-full border border-gray-300 px-2 py-0.5 text-xs text-gray-700 hover:bg-gray-100 disabled:opacity-50"
          >
            {text}
          </button>
        ))}
      </div>

      <form onSubmit={handleSubmit} className="mt-2 flex gap-2">
        <input
          type="text"
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          maxLength={MAX_LENGTH}
          placeholder="Ваш вопрос..."
          aria-label="Вопрос о битве"
          className="min-w-0 flex-1 rounded border border-gray-300 px-2 py-1 text-sm focus:border-blue-600 focus:outline-none"
        />
        <button
          type="submit"
          disabled={!canSubmit}
          className="rounded bg-blue-600 px-3 py-1 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {isLoading ? '...' : 'Спросить'}
        </button>
      </form>

      <div className="mt-2 min-h-0 flex-1">
        {isLoading && <div className="text-xs text-gray-500">Думаю...</div>}
        {error && (
          <div role="alert" className="text-sm text-red-600">
            {error}
          </div>
        )}
        {answer && (
          <div className="h-full overflow-y-auto whitespace-pre-line rounded bg-gray-50 p-2 text-sm">
            {answer}
          </div>
        )}
      </div>
      <div className="mt-1 text-[10px] text-gray-400">
        Ответ генерирует AI и может содержать неточности
      </div>
    </div>
  )
}

export default AskBattle
