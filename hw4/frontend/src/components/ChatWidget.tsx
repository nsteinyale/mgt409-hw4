import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import {
  clearChatHistory,
  fetchChatHistory,
  forgetMySize,
  formatPrice,
  sendChatMessage,
  type ChatMessage,
  type User,
} from '../api'
import { useAuth } from '../auth'
import { useChatControl } from '../chatControl'
import { CHAT_RESULTS_PATH, useChatResults } from '../chatResults'
import { maybeTriggerHarvardChase } from '../harvardChase'
import { useCurrentPageContext, type PageContextData } from '../pageContext'
import { BulldogFace } from './Bulldog'

// One-tap suggested questions that fit the page the shopper is on (usability improvement).
function suggestionsFor(page: PageContextData, user: User | null): string[] {
  const size = user?.preferred_size ?? page.selected_size ?? null
  switch (page.page_type) {
    case 'product':
      return [
        size ? `Is this in stock in ${size}?` : 'What sizes are in stock?',
        'Do you have this in gray?',
        'Something similar but cheaper?',
        ...(user && page.selected_size && page.selected_size !== user.preferred_size
          ? [`Remember ${page.selected_size} as my size`]
          : []),
      ]
    case 'search_results':
      return [`Which of these are in stock in ${size ?? 'M'}?`, 'Show me cheaper options', 'Any of these in gray?']
    case 'catalogue':
      return ['Hoodies under $70', 'Gifts for a Yale parent', 'What should I wear to The Game?']
    default:
      return ['Show me your hoodies', 'Anything for Saybrook?', 'Gifts for a Yale mom']
  }
}

export default function ChatWidget() {
  const { user, refresh } = useAuth()
  const { show: showOnPage } = useChatResults()
  const { open, setOpen, pending, takePending } = useChatControl()
  const page = useCurrentPageContext()
  const navigate = useNavigate()
  const location = useLocation()
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [restored, setRestored] = useState(0) // how many messages came from saved history
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [talking, setTalking] = useState(false) // Dan's mouth moves while a new reply "plays"
  const talkTimer = useRef<number | undefined>(undefined)
  const listRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const userId = user?.id ?? null

  // Logged in: reload the customer's saved chat. Logged out: clear the window so the
  // next person on this computer doesn't see it. Guest chats aren't saved anywhere.
  useEffect(() => {
    let cancelled = false
    setMessages([])
    setRestored(0)
    if (userId !== null) {
      fetchChatHistory().then((saved) => {
        if (cancelled) return
        setMessages(saved)
        setRestored(saved.length)
      })
    }
    return () => {
      cancelled = true
    }
  }, [userId])

  const greeting: ChatMessage = {
    role: 'assistant',
    content: user
      ? restored > 0
        ? `Welcome back, ${user.first_name}! Here's our earlier conversation. Ask me anything about Yale gear.`
        : `Hi, ${user.first_name}! I'm Dan, the Campus Customs shopping bulldog. Ask me about hoodies, sizes, colors, or gifts for your favorite Bulldog.`
      : "Hi! I'm Dan, the Campus Customs shopping bulldog. Ask me about hoodies, sizes, colors, or gifts for your favorite Bulldog. Log in to have me remember our chat.",
  }

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight })
    if (open && !sending) inputRef.current?.focus()
  }, [messages, open, sending])

  function talkFor(reply: string) {
    window.clearTimeout(talkTimer.current)
    setTalking(true)
    // Roughly the time it takes to read the reply aloud, between 1.2 and 6 seconds
    talkTimer.current = window.setTimeout(() => setTalking(false), Math.min(6000, Math.max(1200, reply.length * 35)))
  }

  useEffect(() => () => window.clearTimeout(talkTimer.current), [])

  async function send(text: string) {
    if (!text || sending) return
    maybeTriggerHarvardChase(text)
    const history = messages // earlier turns only; the greeting is local and isn't sent
    setMessages([...history, { role: 'user', content: text }])
    setInput('')
    setSending(true)
    try {
      const reply = await sendChatMessage(text, history, page)
      const results = reply.page_results
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: reply.reply,
          products: reply.products,
          pageResults: results ? { title: results.title, count: results.total_matches } : undefined,
          factCheck: reply.fact_check ?? undefined,
        },
      ])
      talkFor(reply.reply)
      // The agent saved or forgot the customer's size: update the chip and product pages
      if (user && reply.preferred_size !== user.preferred_size) await refresh()
      // The agent searched for a kind of item: put every match on the Products page.
      if (results && results.products.length > 0) {
        showOnPage(results)
        const onResultsPage = location.pathname === '/products' && new URLSearchParams(location.search).get('view') === 'chat'
        if (!onResultsPage) navigate(CHAT_RESULTS_PATH)
      }
    } catch (err) {
      setMessages((prev) => [...prev, { role: 'assistant', content: (err as Error).message }])
    } finally {
      setSending(false)
    }
  }

  // A page asked the chat a question (the "Ask about this item" button or a color swatch)
  useEffect(() => {
    if (pending && !sending) {
      const question = takePending()
      if (question) void send(question)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pending, sending])

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    void send(input.trim())
  }

  async function handleClearHistory() {
    if (!window.confirm('Delete your saved chat history? This cannot be undone.')) return
    await clearChatHistory()
    setMessages([])
    setRestored(0)
  }

  async function handleForgetSize() {
    await forgetMySize()
    await refresh()
  }

  const suggestions = suggestionsFor(page, user)

  return (
    <div className="chat-widget">
      {open && (
        <section className="chat-panel" aria-label="Shopping assistant chat">
          <header className="chat-header">
            <BulldogFace size={46} talking={talking} thinking={sending} />
            <div>
              <strong>Dan, your Campus Customs assistant</strong>
              <small>{user ? 'Your chat is saved to your account' : 'Ask about products, sizes, and stock'}</small>
            </div>
            {user && messages.length > 0 && (
              <button type="button" className="chat-clear" onClick={handleClearHistory}>
                Clear history
              </button>
            )}
            <button type="button" className="chat-close" onClick={() => setOpen(false)} aria-label="Close chat">
              ×
            </button>
          </header>
          {user?.preferred_size && (
            <div className="chat-size-bar">
              <span className="size-chip">
                Your saved size: <strong>{user.preferred_size}</strong>
                <button type="button" onClick={handleForgetSize} aria-label="Forget my saved size">
                  ×
                </button>
              </span>
            </div>
          )}
          <div className="chat-messages" ref={listRef} aria-live="polite">
            {[greeting, ...messages].map((m, i) => (
              <div key={i} className={`chat-turn ${m.role}${i > 0 && i <= restored ? ' restored' : ''}`}>
                <div className={`chat-bubble ${m.role}`}>{m.content}</div>
                {m.pageResults && (
                  <Link to={CHAT_RESULTS_PATH} className="chat-page-link">
                    Showing {m.pageResults.count} on the page: {m.pageResults.title} →
                  </Link>
                )}
                {m.products && m.products.length > 0 && (
                  <div className="chat-products">
                    {m.products.map((p) => (
                      <Link key={p.product_id} to={`/products/${p.product_id}`} className="chat-product">
                        <img src={p.image_url} alt="" />
                        <span>
                          <strong>{p.name}</strong>
                          <small>{formatPrice(p.price)}</small>
                        </span>
                      </Link>
                    ))}
                  </div>
                )}
                {m.factCheck && m.factCheck.facts_checked > 0 && (
                  <div className="fact-check" title="Prices and stock in this reply were checked against the store database">
                    ✓ {m.factCheck.facts_checked} price/stock {m.factCheck.facts_checked === 1 ? 'fact' : 'facts'} checked
                    against live inventory
                    {m.factCheck.corrections > 0 && ` · ${m.factCheck.corrections} fixed before you saw it`}
                  </div>
                )}
              </div>
            ))}
            {sending && <div className="chat-bubble assistant typing">Typing…</div>}
          </div>
          {!sending && (
            <div className="chat-suggestions" aria-label="Suggested questions">
              {suggestions.map((s) => (
                <button key={s} type="button" className="suggestion-chip" onClick={() => void send(s)}>
                  {s}
                </button>
              ))}
            </div>
          )}
          <form className="chat-input" onSubmit={handleSubmit}>
            <input
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Do you have navy hoodies in medium?"
              aria-label="Message"
              maxLength={1000}
            />
            <button type="submit" className="btn" disabled={sending || !input.trim()}>
              Send
            </button>
          </form>
        </section>
      )}
      <button
        type="button"
        className={`chat-toggle${open ? ' is-open' : ''}`}
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        aria-label={open ? 'Close chat' : 'Open chat'}
      >
        {open ? (
          '×'
        ) : (
          <>
            <BulldogFace size={36} />
            Chat with Dan
          </>
        )}
      </button>
    </div>
  )
}
