import { createContext, useContext, useState, type ReactNode } from 'react'
import type { PageResults } from './api'

// The latest search results the chat agent sent to the page. Shared by the chat widget
// (which receives them) and the Products page (which shows them). Kept in sessionStorage
// so a page reload or the browser's back button doesn't lose them.

export interface ShownResults extends PageResults {
  id: number // changes every time new results arrive, so the page can re-animate
}

interface ChatResultsState {
  results: ShownResults | null
  show: (results: PageResults) => void
  clear: () => void
}

const STORAGE_KEY = 'cc_chat_results'
const ChatResultsContext = createContext<ChatResultsState | null>(null)

function loadSaved(): ShownResults | null {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY)
    return raw ? (JSON.parse(raw) as ShownResults) : null
  } catch {
    return null
  }
}

export function ChatResultsProvider({ children }: { children: ReactNode }) {
  const [results, setResults] = useState<ShownResults | null>(loadSaved)

  const value: ChatResultsState = {
    results,
    show: (next) => {
      const shown = { ...next, id: Date.now() }
      setResults(shown)
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(shown))
    },
    clear: () => {
      setResults(null)
      sessionStorage.removeItem(STORAGE_KEY)
    },
  }

  return <ChatResultsContext.Provider value={value}>{children}</ChatResultsContext.Provider>
}

export function useChatResults(): ChatResultsState {
  const ctx = useContext(ChatResultsContext)
  if (!ctx) throw new Error('useChatResults must be used inside <ChatResultsProvider>')
  return ctx
}

export const CHAT_RESULTS_PATH = '/products?view=chat'
