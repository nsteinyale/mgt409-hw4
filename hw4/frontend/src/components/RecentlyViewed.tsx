import { Link } from 'react-router-dom'
import { formatPrice } from '../api'
import { clearRecentlyViewed, useRecentlyViewed } from '../recentlyViewed'

// "Recently viewed" strip (usability improvement). Data lives only in this browser.
export default function RecentlyViewed({ excludeId }: { excludeId?: string }) {
  const items = useRecentlyViewed().filter((i) => i.product_id !== excludeId)
  if (items.length === 0) return null
  return (
    <section className="recently-viewed" aria-label="Recently viewed">
      <div className="recently-viewed-head">
        <h2>Recently viewed</h2>
        <span className="muted small">Saved only in this browser</span>
        <button type="button" className="link-button" onClick={clearRecentlyViewed}>
          Clear
        </button>
      </div>
      <div className="recently-viewed-row">
        {items.map((i) => (
          <Link key={i.product_id} to={`/products/${i.product_id}`} className="recent-card">
            <img src={i.image_url} alt="" loading="lazy" />
            <span className="recent-name">{i.name}</span>
            <span className="recent-price">{formatPrice(i.price)}</span>
          </Link>
        ))}
      </div>
    </section>
  )
}
