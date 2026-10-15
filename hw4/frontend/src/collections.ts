import type { Product } from './api'

// Themed collections, matched on product names (like the "Residential Colleges",
// "Sports", and "Relatives" menus on yalebulldogblue.com).
const wordsPattern = (words: string[]) => new RegExp(`\\b(${words.join('|')})\\b`, 'i')

export const COLLECTIONS = {
  colleges: {
    label: 'Residential colleges',
    pattern: wordsPattern([
      'Benjamin Franklin', 'Berkeley', 'Branford', 'Davenport', 'Ezra Stiles', 'Grace Hopper', 'Jonathan Edwards',
      'Morse', 'Pauli Murray', 'Pierson', 'Saybrook', 'Silliman', 'Timothy Dwight', 'Trumbull',
    ]),
  },
  sports: {
    label: 'Sports',
    pattern: wordsPattern([
      'baseball', 'basketball', 'football', 'hockey', 'soccer', 'tennis', 'track', 'diving', 'swimming', 'golf',
      'volleyball', 'lacrosse', 'fencing', 'sailing', 'squash', 'crew', 'sports',
    ]),
  },
  family: {
    label: 'Family',
    pattern: wordsPattern(['mom', 'dad', 'grandma', 'grandpa', 'aunt', 'uncle', 'brother', 'sister', 'cousin']),
  },
} as const

export type CollectionKey = keyof typeof COLLECTIONS

export function isCollectionKey(value: string | null): value is CollectionKey {
  return value !== null && value in COLLECTIONS
}

export function inCollection(product: Product, key: CollectionKey): boolean {
  return COLLECTIONS[key].pattern.test(product.name)
}
