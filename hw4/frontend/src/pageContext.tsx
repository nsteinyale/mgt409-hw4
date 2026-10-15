import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { useLocation } from 'react-router-dom'

// What the shopper is looking at, sent with every chat message so the agent understands
// "this", "these", or "the first one". Pages publish their details with usePublishPageContext();
// any page that doesn't gets a basic context from its URL.

export type PageType = 'home' | 'catalogue' | 'product' | 'search_results' | 'about' | 'account' | 'other'

export interface PageContextData {
  path: string
  page_type: PageType
  product_id?: string | null
  selected_size?: string | null
  title?: string | null
  product_ids?: string[]
}

type Published = Omit<PageContextData, 'path'>

interface PageContextState {
  published: { pathname: string; data: Published } | null
  publish: (pathname: string, data: Published | null) => void
}

const Ctx = createContext<PageContextState | null>(null)
const MAX_VISIBLE_IDS = 12

export function PageContextProvider({ children }: { children: ReactNode }) {
  const [published, setPublished] = useState<PageContextState['published']>(null)
  const publish: PageContextState['publish'] = (pathname, data) =>
    setPublished((prev) => (data ? { pathname, data } : prev?.pathname === pathname ? null : prev))
  return <Ctx.Provider value={{ published, publish }}>{children}</Ctx.Provider>
}

function useCtx(): PageContextState {
  const ctx = useContext(Ctx)
  if (!ctx) throw new Error('Page context hooks must be used inside <PageContextProvider>')
  return ctx
}

// Called by a page to describe itself. Re-publishes whenever the details change.
// Pass null to publish nothing (e.g. when a child component describes the page instead).
export function usePublishPageContext(data: Published | null) {
  const { publish } = useCtx()
  const { pathname } = useLocation()
  const key = data ? JSON.stringify({ ...data, product_ids: data.product_ids?.slice(0, MAX_VISIBLE_IDS) }) : null
  useEffect(() => {
    if (key === null) return
    publish(pathname, JSON.parse(key) as Published)
    return () => publish(pathname, null)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pathname, key])
}

function typeFromPath(pathname: string): PageType {
  if (pathname === '/') return 'home'
  if (pathname === '/products') return 'catalogue'
  if (pathname.startsWith('/products/')) return 'product'
  if (pathname === '/about') return 'about'
  if (pathname === '/login' || pathname === '/create-account') return 'account'
  return 'other'
}

// Used by the chat widget: the current page's context, published or derived from the URL.
export function useCurrentPageContext(): PageContextData {
  const { published } = useCtx()
  const { pathname, search } = useLocation()
  const path = pathname + search
  if (published && published.pathname === pathname) return { path, ...published.data }
  return {
    path,
    page_type: typeFromPath(pathname),
    product_id: pathname.startsWith('/products/') ? decodeURIComponent(pathname.slice('/products/'.length)) : null,
  }
}
