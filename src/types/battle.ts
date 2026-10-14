export interface BattleSide {
  name: string
  commanders: string[]
}

export interface Battle {
  id: string
  name: string
  war: string
  startYear: number
  endYear: number
  coordinates: {
    lat: number
    lng: number
  }
  sides: BattleSide[]
  outcome: string
  description: string
}
