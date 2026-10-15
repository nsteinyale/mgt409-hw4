import { useEffect, useState } from 'react'

// "Recently viewed" products, stored ONLY in this browser (localStorage). Nothing is sent to the
// server, and the shopper can clear it with one click.

export interface RecentItem {
  product_id: string
  name: string
  price: number
  image_url: string
}

const KEY = 'cc_recently_viewed'
const MAX_ITEMS = 8
const EVENT = 'cc-recently-viewed-changed'

function read(): RecentItem[] {
  try {
    return JSON.parse(localStorage.getItem(KEY) ?? '[]') as RecentItem[]
  } catch {
    return []
  }
}

function write(items: RecentItem[]) {
  localStorage.setItem(KEY, JSON.stringify(items))
  window.dispatchEvent(new Event(EVENT))
}

export function addRecentlyViewed(item: RecentItem) {
  write([item, ...read().filter((i) => i.product_id !== item.product_id)].slice(0, MAX_ITEMS))
}

export function clearRecentlyViewed() {
  localStorage.removeItem(KEY)
  window.dispatchEvent(new Event(EVENT))
}

export function useRecentlyViewed(): RecentItem[] {
  const [items, setItems] = useState<RecentItem[]>(read)
  useEffect(() => {
    const update = () => setItems(read())
    window.addEventListener(EVENT, update)
    window.addEventListener('storage', update) // other tabs
    return () => {
      window.removeEventListener(EVENT, update)
      window.removeEventListener('storage', update)
    }
  }, [])
  return items
}
