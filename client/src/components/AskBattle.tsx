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
    <div className="mt-3 border-t border-gray-200 pt-3">
      <p className="text-sm font-medium">Спросить AI про эту битву</p>

      <div className="mt-2 flex flex-wrap gap-1">
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

      {isLoading && <p className="mt-2 text-xs text-gray-500">Думаю...</p>}
      {error && (
        <p role="alert" className="mt-2 text-sm text-red-600">
          {error}
        </p>
      )}
      {answer && (
        <p className="mt-2 max-h-48 overflow-y-auto whitespace-pre-line rounded bg-gray-50 p-2 text-sm">
          {answer}
        </p>
      )}
      <p className="mt-1 text-[10px] text-gray-400">
        Ответ генерирует AI и может содержать неточности
      </p>
    </div>
  )
}

export default AskBattle
