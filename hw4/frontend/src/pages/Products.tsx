import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { CATEGORIES, categoryOf, fetchProducts, type Category, type Product } from '../api'
import { useChatResults } from '../chatResults'
import { COLLECTIONS, inCollection, isCollectionKey, type CollectionKey } from '../collections'
import ChatResultsView from '../components/ChatResultsView'
import ProductCard from '../components/ProductCard'
import RecentlyViewed from '../components/RecentlyViewed'
import { usePublishPageContext } from '../pageContext'
import { triggerHarvardChase } from '../harvardChase'

export default function Products() {
  const [products, setProducts] = useState<Product[]>([])
  const [status, setStatus] = useState<'loading' | 'ready' | 'error'>('loading')
  const [params, setParams] = useSearchParams()
  const { results: chatResults, clear: clearChatResults } = useChatResults()

  const query = params.get('q') ?? ''
  const category = (CATEGORIES as readonly string[]).includes(params.get('type') ?? '') ? (params.get('type') as Category) : 'All'
  const collectionParam = params.get('collection')
  const collection: CollectionKey | null = isCollectionKey(collectionParam) ? collectionParam : null

  // Searching for Harvard sets off the chase (once each time the search turns to Harvard)
  const harvardSearch = /harvard/i.test(query)
  useEffect(() => {
    if (harvardSearch) triggerHarvardChase()
  }, [harvardSearch])

  useEffect(() => {
    fetchProducts()
      .then((data) => {
        setProducts(data)
        setStatus('ready')
      })
      .catch(() => setStatus('error'))
  }, [])

  function setParam(key: string, value: string | null) {
    const next = new URLSearchParams(params)
    if (value) next.set(key, value)
    else next.delete(key)
    setParams(next, { replace: true })
  }

  const visible = useMemo(() => {
    const words = query.toLowerCase().split(/\s+/).filter(Boolean)
    return products.filter((p) => {
      if (category !== 'All' && categoryOf(p.garment_type) !== category) return false
      if (collection && !inCollection(p, collection)) return false
      const haystack = [p.name, p.garment_type, p.description, ...p.colors, ...p.search_tags].join(' ').toLowerCase()
      return words.every((w) => haystack.includes(w))
    })
  }, [products, query, category, collection])

  const showingChat = params.get('view') === 'chat' && chatResults !== null
  const filters = [collection && COLLECTIONS[collection].label, category !== 'All' && category, query && `search "${query}"`].filter(Boolean)
  usePublishPageContext(
    showingChat
      ? null // ChatResultsView describes the page instead
      : {
          page_type: 'catalogue',
          title: filters.length ? `Filtered: ${filters.join(', ')}` : 'All products',
          product_ids: visible.map((p) => p.product_id),
        },
  )

  // The chat agent sent search results: show those instead of the full catalogue
  if (params.get('view') === 'chat' && chatResults) {
    return (
      <div className="page">
        <ChatResultsView
          results={chatResults}
          onShowAll={() => {
            clearChatResults()
            setParam('view', null)
          }}
        />
      </div>
    )
  }

  return (
    <div className="page">
      <div className="page-head">
        <h1>{collection ? COLLECTIONS[collection].label : 'All products'}</h1>
        <p className="muted">Officially licensed Yale apparel. Click any item for sizes and stock.</p>
      </div>

      <div className="filters">
        <input
          type="search"
          className="search"
          value={query}
          onChange={(e) => setParam('q', e.target.value)}
          placeholder="Search hoodies, colors, colleges…"
          aria-label="Search products"
        />
        <select value={category} onChange={(e) => setParam('type', e.target.value === 'All' ? null : e.target.value)} aria-label="Product type">
          {CATEGORIES.map((c) => (
            <option key={c} value={c}>
              {c === 'All' ? 'All types' : c}
            </option>
          ))}
        </select>
      </div>
      <div className="chips">
        <button type="button" className={collection ? 'chip' : 'chip active'} onClick={() => setParam('collection', null)}>
          Everything
        </button>
        {(Object.keys(COLLECTIONS) as CollectionKey[]).map((key) => (
          <button
            key={key}
            type="button"
            className={collection === key ? 'chip active' : 'chip'}
            onClick={() => setParam('collection', key)}
          >
            {COLLECTIONS[key].label}
          </button>
        ))}
      </div>

      <RecentlyViewed />

      {status === 'loading' && <p className="muted">Loading products…</p>}
      {status === 'error' && <p className="form-error">Couldn't load products. Make sure the backend is running on port 8000.</p>}
      {status === 'ready' && (
        <>
          <p className="muted small">
            {visible.length} {visible.length === 1 ? 'item' : 'items'}
          </p>
          {visible.length === 0 ? (
            <p className="muted">No products match. Try a different search, or ask the chat assistant for help.</p>
          ) : (
            <div className="product-grid">
              {visible.map((p) => (
                <ProductCard key={p.product_id} product={p} />
              ))}
            </div>
          )}
        </>
      )}
    </div>
  )
}
