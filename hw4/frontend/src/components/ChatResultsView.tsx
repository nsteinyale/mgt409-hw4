import type { ShownResults } from '../chatResults'
import { usePublishPageContext } from '../pageContext'
import ProductCard from './ProductCard'

interface Props {
  results: ShownResults
  onShowAll: () => void
}

// The Products page while it's showing search results from the chat agent.
export default function ChatResultsView({ results, onShowAll }: Props) {
  const shown = results.products.length
  usePublishPageContext({
    page_type: 'search_results',
    title: results.title,
    product_ids: results.products.map((p) => p.product_id),
  })
  return (
    // key: a new search remounts this section so the entrance animation plays again
    <section key={results.id} className="chat-results" aria-live="polite" aria-label="Results from the shopping assistant">
      <div className="chat-results-banner">
        <div className="chat-results-icon" aria-hidden="true">
          <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
          </svg>
        </div>
        <div className="chat-results-text">
          <p className="eyebrow">From your shopping assistant</p>
          <h1>{results.title}</h1>
          <p>
            {results.total_matches} {results.total_matches === 1 ? 'match' : 'matches'}
            {shown < results.total_matches ? ` · showing the first ${shown}` : ''} · searched for “{results.query}”
          </p>
        </div>
        <button type="button" className="btn btn-light btn-small" onClick={onShowAll}>
          Show all products
        </button>
      </div>

      <div className="product-grid">
        {results.products.map((p, i) => (
          <ProductCard
            key={p.product_id}
            product={{ ...p, description: p.short_description }}
            className="card-enter"
            style={{ animationDelay: `${Math.min(i, 15) * 45}ms` }}
          />
        ))}
      </div>
    </section>
  )
}
