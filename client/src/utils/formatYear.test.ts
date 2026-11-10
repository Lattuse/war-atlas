import { describe, expect, it } from 'vitest'
import { formatYear } from './formatYear'

describe('formatYear', () => {
  it('formats AD years as plain numbers', () => {
    expect(formatYear(1066)).toBe('1066')
  })

  it('formats BC years with "до н.э."', () => {
    expect(formatYear(-480)).toBe('480 до н.э.')
  })

  it('treats year 0 as a plain number', () => {
    expect(formatYear(0)).toBe('0')
  })
})
