// Front end calls to the Campus Customs backend (backend/main.py).
// In development, Vite forwards /api and /images to http://127.0.0.1:8000.

import type { PageContextData } from './pageContext'

export interface Product {
  product_id: string
  name: string
  garment_type: string
  description: string
  colors: string[]
  search_tags: string[]
  image_url: string
  price: number
  in_stock: boolean
}

export interface SizeStock {
  size: string
  quantity: number
}

export interface ProductDetail extends Product {
  sizes: SizeStock[]
}

// ---- Chat API contract (mirrors backend/models.py) ----

export interface ProductCardData {
  product_id: string
  name: string
  price: number
  image_url: string
  garment_type: string
  short_description: string
  sizes_in_stock: string[]
  in_stock: boolean
}

// Search matches the agent asked the website to show on the Products page
export interface PageResults {
  title: string
  query: string
  total_matches: number
  products: ProductCardData[]
}

export interface FactCheckInfo {
  facts_checked: number
  corrections: number
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  products?: ProductCardData[]
  pageResults?: { title: string; count: number }
  factCheck?: FactCheckInfo
}

export interface ChatReply {
  reply: string
  products: ProductCardData[]
  page_results: PageResults | null
  fact_check: FactCheckInfo | null
  preferred_size: string | null
}

async function getJson<T>(url: string): Promise<T> {
  const res = await fetch(url)
  if (!res.ok) {
    throw new Error(res.status === 404 ? 'not-found' : `Request failed (${res.status})`)
  }
  return res.json() as Promise<T>
}

export function fetchProducts(): Promise<Product[]> {
  return getJson<Product[]>('/api/products')
}

export function fetchProduct(productId: string): Promise<ProductDetail> {
  return getJson<ProductDetail>(`/api/products/${encodeURIComponent(productId)}`)
}

const MAX_HISTORY = 20

// Sends the new message, recent history (text only; the backend uses saved history instead for
// logged-in customers), and what's on screen to the PydanticAI agent behind /api/chat.
export async function sendChatMessage(message: string, history: ChatMessage[], page: PageContextData): Promise<ChatReply> {
  const res = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message,
      history: history.slice(-MAX_HISTORY).map(({ role, content }) => ({ role, content })),
      page,
    }),
  })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) {
    throw new Error(typeof data.detail === 'string' ? data.detail : "Sorry, I couldn't reach the shop right now. Try again in a moment.")
  }
  return data as ChatReply
}

// ---- Accounts ----
// The session lives in an HttpOnly cookie set by the backend, so the browser sends it
// automatically and JavaScript never handles the token itself.

export interface User {
  id: number
  first_name: string
  last_name: string
  name: string
  email: string
  preferred_size: string | null
}

export interface SignupInput {
  first_name: string
  last_name: string
  email: string
  password: string
}

async function postJson<T>(url: string, body?: unknown): Promise<T> {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) {
    throw new Error(typeof data.detail === 'string' ? data.detail : 'Something went wrong. Try again.')
  }
  return data as T
}

export function signup(input: SignupInput): Promise<User> {
  return postJson<User>('/api/signup', input)
}

export function login(email: string, password: string): Promise<User> {
  return postJson<User>('/api/login', { email, password })
}

export async function logout(): Promise<void> {
  await postJson('/api/logout')
}

export async function fetchCurrentUser(): Promise<User | null> {
  const res = await fetch('/api/me')
  return res.ok ? ((await res.json()) as User) : null
}

// ---- Saved chat history (logged-in customers only) ----

interface SavedMessage {
  id: number
  role: 'user' | 'assistant'
  content: string
  products: ProductCardData[]
  created_at: string
}

export async function fetchChatHistory(): Promise<ChatMessage[]> {
  const res = await fetch('/api/chat/history')
  if (!res.ok) return []
  const data = (await res.json()) as { messages: SavedMessage[] }
  return data.messages.map((m) => ({ role: m.role, content: m.content, products: m.products }))
}

export async function clearChatHistory(): Promise<void> {
  await fetch('/api/chat/history', { method: 'DELETE' })
}

// ---- Saved size and back-in-stock waitlist (logged-in customers) ----

async function sendJson<T>(method: string, url: string, body?: unknown): Promise<T> {
  const res = await fetch(url, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Something went wrong. Try again.')
  return data as T
}

export const saveMySize = (size: string) => sendJson<{ preferred_size: string }>('PUT', '/api/me/size', { size })
export const forgetMySize = () => sendJson<{ preferred_size: null }>('DELETE', '/api/me/size')

export interface WaitlistEntry {
  product_id: string
  name: string
  size: string
  created_at: string
  back_in_stock: boolean
}

export const fetchWaitlist = () => sendJson<WaitlistEntry[]>('GET', '/api/waitlist')
export const joinWaitlist = (product_id: string, size: string) => sendJson('POST', '/api/waitlist', { product_id, size })
export const leaveWaitlist = (product_id: string, size: string) =>
  sendJson('DELETE', `/api/waitlist/${encodeURIComponent(product_id)}/${encodeURIComponent(size)}`)

export function formatPrice(price: number): string {
  return `$${price.toFixed(2)}`
}

// The catalogue's garment_type labels are inconsistent ("t-shirt", "short-sleeve T-shirt", ...),
// so group them into a few shopper-friendly categories.
export const CATEGORIES = ['All', 'T-shirts', 'Crewnecks', 'Hoodies', 'Quarter-zips', 'Jackets & fleece', 'Long sleeve'] as const
export type Category = (typeof CATEGORIES)[number]

export function categoryOf(garmentType: string): Category {
  const t = garmentType.toLowerCase()
  if (t.includes('t-shirt')) return 'T-shirts'
  if (t.includes('quarter-zip')) return 'Quarter-zips'
  if (t.includes('hood')) return 'Hoodies'
  if (t.includes('jacket') || t.includes('fleece')) return 'Jackets & fleece'
  if (t.includes('long-sleeve')) return 'Long sleeve'
  return 'Crewnecks'
}
