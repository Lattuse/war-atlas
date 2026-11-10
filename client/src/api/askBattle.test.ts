import { describe, expect, it, vi } from 'vitest'
import { askBattle, AskBattleError } from './askBattle'

function mockFetch(status: number, body: unknown = {}) {
  return vi.fn().mockResolvedValue(
    new Response(JSON.stringify(body), {
      status,
      headers: { 'Content-Type': 'application/json' },
    }),
  )
}

describe('askBattle', () => {
  it('sends the question and returns the answer', async () => {
    const fetchImpl = mockFetch(200, { battleId: 'battle-of-hastings', answer: 'Norman victory.' })

    const answer = await askBattle('battle-of-hastings', 'Who won?', fetchImpl)

    expect(answer).toBe('Norman victory.')
    expect(fetchImpl).toHaveBeenCalledWith(
      '/api/battles/battle-of-hastings/ask',
      expect.objectContaining({
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: 'Who won?' }),
        signal: expect.any(AbortSignal),
      }),
    )
  })

  it('encodes the battle id in the URL', async () => {
    const fetchImpl = mockFetch(200, { battleId: 'x', answer: 'ok' })

    await askBattle('a/b', 'Who won?', fetchImpl)

    expect(fetchImpl.mock.calls[0][0]).toBe('/api/battles/a%2Fb/ask')
  })

  it.each([
    [404, 'Битва не найдена'],
    [422, 'Вопрос должен быть от 3 до 500 символов'],
    [429, 'Слишком много вопросов, подождите минуту'],
    [502, 'AI-помощник не смог ответить, попробуйте ещё раз'],
    [503, 'AI-помощник сейчас не настроен на сервере'],
    [504, 'AI-помощник сейчас перегружен, попробуйте через пару минут'],
    [500, 'Что-то пошло не так'],
  ])('maps HTTP %i to a readable error', async (status, message) => {
    const promise = askBattle('battle-of-hastings', 'Who won?', mockFetch(status))

    await expect(promise).rejects.toEqual(new AskBattleError(message, status))
  })

  it('reports a timeout as a slow answer', async () => {
    const fetchImpl = vi
      .fn()
      .mockRejectedValue(new DOMException('The operation timed out.', 'TimeoutError'))

    const promise = askBattle('battle-of-hastings', 'Who won?', fetchImpl)

    await expect(promise).rejects.toMatchObject({
      status: 0,
      message: 'AI-помощник отвечает слишком долго, попробуйте ещё раз',
    })
  })

  it('reports a network failure as server unavailable', async () => {
    const fetchImpl = vi.fn().mockRejectedValue(new TypeError('Failed to fetch'))

    const promise = askBattle('battle-of-hastings', 'Who won?', fetchImpl)

    await expect(promise).rejects.toMatchObject({ status: 0, message: 'Сервер недоступен' })
  })
})
