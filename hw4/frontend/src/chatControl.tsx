import { createContext, useContext, useState, type ReactNode } from 'react'

// Lets any page open the chat panel or send it a question (the "Ask about this item" button,
// color swatches). The chat widget watches `pending` and sends it like a typed message.

interface ChatControlState {
  open: boolean
  setOpen: (open: boolean | ((prev: boolean) => boolean)) => void
  pending: string | null
  ask: (question: string) => void
  takePending: () => string | null
}

const Ctx = createContext<ChatControlState | null>(null)

export function ChatControlProvider({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false)
  const [pending, setPending] = useState<string | null>(null)
  const value: ChatControlState = {
    open,
    setOpen,
    pending,
    ask: (question) => {
      setOpen(true)
      setPending(question)
    },
    takePending: () => {
      const q = pending
      setPending(null)
      return q
    },
  }
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}

export function useChatControl(): ChatControlState {
  const ctx = useContext(Ctx)
  if (!ctx) throw new Error('useChatControl must be used inside <ChatControlProvider>')
  return ctx
}
