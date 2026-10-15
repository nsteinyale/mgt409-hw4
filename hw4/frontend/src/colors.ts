// Swatch colors for the catalogue's color names (used by product cards and product pages).

const SWATCHES: [string, string][] = [
  ['light blue', '#93c5fd'],
  ['royal blue', '#1d4ed8'],
  ['navy', '#1f2a44'],
  ['charcoal', '#4b5563'],
  ['heather', '#9ca3af'],
  ['gray', '#9ca3af'],
  ['grey', '#9ca3af'],
  ['white', '#ffffff'],
  ['cream', '#f3ead7'],
  ['ivory', '#f6f1e3'],
  ['black', '#111111'],
  ['red', '#b91c1c'],
  ['green', '#2f6b3a'],
  ['yellow', '#e0b42f'],
  ['gold', '#c9a227'],
  ['coral', '#f08a78'],
  ['blue', '#2563eb'],
]

export function swatch(color: string): string {
  const lower = color.toLowerCase()
  if (lower.includes('multi')) return 'conic-gradient(#b91c1c, #e0b42f, #2f6b3a, #2563eb, #b91c1c)'
  return SWATCHES.find(([name]) => lower.includes(name))?.[1] ?? '#d1d5db'
}

export function hasColor(colors: string[], color: string): boolean {
  const family = color === 'gray' ? ['gray', 'grey', 'heather', 'charcoal'] : color === 'white' ? ['white', 'ivory'] : [color]
  return colors.some((c) => family.some((f) => c.toLowerCase().includes(f)))
}
