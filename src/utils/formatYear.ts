export function formatYear(year: number): string {
  return year < 0 ? `${Math.abs(year)} до н.э.` : `${year}`
}