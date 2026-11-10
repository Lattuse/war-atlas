// In dev, Vite proxies /api to the FastAPI server (see vite.config.ts).
// In production, set VITE_API_URL to the deployed backend URL.
const API_BASE = import.meta.env.VITE_API_URL ?? ''

export interface AskBattleResponse {
  battleId: string
  answer: string
}

export class AskBattleError extends Error {
  readonly status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = 'AskBattleError'
    this.status = status
  }
}

const MESSAGES_BY_STATUS: Record<number, string> = {
  404: 'Битва не найдена',
  422: 'Вопрос должен быть от 3 до 500 символов',
  429: 'Слишком много вопросов, подождите минуту',
  502: 'AI-помощник не смог ответить, попробуйте ещё раз',
  503: 'AI-помощник сейчас не настроен на сервере',
  504: 'AI-помощник сейчас перегружен, попробуйте через пару минут',
}

// Upper bound on waiting; the backend gives up on the LLM well before this.
export const REQUEST_TIMEOUT_MS = 60_000

export async function askBattle(
  battleId: string,
  question: string,
  fetchImpl: typeof fetch = fetch,
): Promise<string> {
  let response: Response
  try {
    response = await fetchImpl(
      `${API_BASE}/api/battles/${encodeURIComponent(battleId)}/ask`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question }),
        signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
      },
    )
  } catch (err) {
    if (err instanceof DOMException && err.name === 'TimeoutError') {
      throw new AskBattleError('AI-помощник отвечает слишком долго, попробуйте ещё раз', 0)
    }
    throw new AskBattleError('Сервер недоступен', 0)
  }

  if (!response.ok) {
    throw new AskBattleError(
      MESSAGES_BY_STATUS[response.status] ?? 'Что-то пошло не так',
      response.status,
    )
  }

  const data = (await response.json()) as AskBattleResponse
  return data.answer
}
