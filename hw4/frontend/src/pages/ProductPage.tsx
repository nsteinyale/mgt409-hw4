import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { fetchProduct, fetchWaitlist, formatPrice, joinWaitlist, leaveWaitlist, saveMySize, type ProductDetail } from '../api'
import { useAuth } from '../auth'
import { useChatControl } from '../chatControl'
import { CHAT_RESULTS_PATH, useChatResults } from '../chatResults'
import RecentlyViewed from '../components/RecentlyViewed'
import { usePublishPageContext } from '../pageContext'
import { addRecentlyViewed } from '../recentlyViewed'
import { hasColor, swatch } from '../colors'
import { maybeTriggerHarvardChase } from '../harvardChase'

const LOW_STOCK = 5

const OTHER_COLORS = ['gray', 'navy', 'white', 'black', 'green', 'red', 'cream']

export default function ProductPage() {
  const { productId = '' } = useParams()
  const { user, refresh } = useAuth()
  const { ask } = useChatControl()
  const [product, setProduct] = useState<ProductDetail | null>(null)
  const [status, setStatus] = useState<'loading' | 'ready' | 'not-found' | 'error'>('loading')
  const [selectedSize, setSelectedSize] = useState<string | null>(null)
  const [waitlisted, setWaitlisted] = useState<string[]>([])
  const [notice, setNotice] = useState('')
  const { results: chatResults } = useChatResults()
  // Tell the chat which product (and size) the shopper is looking at, so "this one" works
  usePublishPageContext({ page_type: 'product', product_id: productId, selected_size: selectedSize })

  useEffect(() => {
    setStatus('loading')
    setSelectedSize(null)
    setNotice('')
    fetchProduct(productId)
      .then((data) => {
        setProduct(data)
        setStatus('ready')
        addRecentlyViewed({ product_id: data.product_id, name: data.name, price: data.price, image_url: data.image_url })
        maybeTriggerHarvardChase(data.product_id) // e.g. the Yale vs Harvard "The Game" tee
      })
      .catch((err: Error) => setStatus(err.message === 'not-found' ? 'not-found' : 'error'))
  }, [productId])

  // Pre-select the customer's saved size (if they asked us to remember one)
  useEffect(() => {
    if (status === 'ready' && user?.preferred_size && selectedSize === null) setSelectedSize(user.preferred_size)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status, user?.preferred_size])

  // Which sizes of this product the customer is waiting for
  useEffect(() => {
    if (!user) {
      setWaitlisted([])
      return
    }
    fetchWaitlist()
      .then((entries) => setWaitlisted(entries.filter((e) => e.product_id === productId).map((e) => e.size)))
      .catch(() => setWaitlisted([]))
  }, [user, productId])

  if (status === 'loading') return <div className="page muted">Loading…</div>
  if (status === 'not-found' || status === 'error' || !product) {
    return (
      <div className="page narrow center">
        <h1>{status === 'not-found' ? "We couldn't find that item" : 'Something went wrong'}</h1>
        <Link to="/products" className="btn">
          Back to products
        </Link>
      </div>
    )
  }

  const selected = product.sizes.find((s) => s.size === selectedSize)
  const otherColors = OTHER_COLORS.filter((c) => !hasColor(product.colors, c))

  async function handleRememberSize(size: string) {
    await saveMySize(size)
    await refresh()
    setNotice(`Saved ${size} as your size. We'll pick it for you on every product.`)
  }

  async function handleWaitlist(size: string, join: boolean) {
    try {
      if (join) await joinWaitlist(productId, size)
      else await leaveWaitlist(productId, size)
      setWaitlisted((prev) => (join ? [...prev, size] : prev.filter((s) => s !== size)))
      setNotice(join ? 'Saved. No email is sent, so check this page to see when it is back.' : '')
    } catch (err) {
      setNotice((err as Error).message)
    }
  }

  return (
    <div className="page">
      <div className="back-links">
        {chatResults && (
          <Link to={CHAT_RESULTS_PATH} className="back-link">
            ← Back to {chatResults.title}
          </Link>
        )}
        <Link to="/products" className="back-link">
          {chatResults ? 'All products' : '← All products'}
        </Link>
      </div>
      <div className="product-detail">
        <div className="product-detail-image">
          <img src={product.image_url} alt={product.name} />
        </div>
        <div className="product-detail-info">
          <p className="eyebrow">{product.garment_type}</p>
          <h1>{product.name}</h1>
          <p className="price large">{formatPrice(product.price)}</p>
          <p>{product.description}</p>

          <button type="button" className="btn btn-outline ask-button" onClick={() => ask('Tell me about this one. What sizes are in stock?')}>
            Ask about this item
          </button>

          {product.colors.length > 0 && (
            <div className="detail-block">
              <h2>Colors</h2>
              <div className="swatches">
                {product.colors.map((c) => (
                  <span key={c} className="swatch-label">
                    <span className="swatch" style={{ background: swatch(c) }} aria-hidden="true" />
                    {c}
                  </span>
                ))}
              </div>
              {otherColors.length > 0 && (
                <div className="other-colors">
                  <span className="muted small">Want this style in another color?</span>
                  <div className="swatches">
                    {otherColors.map((c) => (
                      <button
                        key={c}
                        type="button"
                        className="swatch-button"
                        onClick={() => ask(`Do you have this in ${c}?`)}
                        title={`Ask the assistant for this style in ${c}`}
                      >
                        <span className="swatch" style={{ background: swatch(c) }} aria-hidden="true" />
                        {c}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          <div className="detail-block">
            <h2>Sizes</h2>
            {!product.in_stock && <p className="form-error">Sold out in every size.</p>}
            <div className="size-grid">
              {product.sizes.map((s) => (
                <button
                  key={s.size}
                  type="button"
                  className={`size-btn${selectedSize === s.size ? ' selected' : ''}${s.quantity === 0 ? ' sold-out' : ''}${
                    user?.preferred_size === s.size ? ' saved' : ''
                  }`}
                  onClick={() => setSelectedSize(s.size)}
                  title={s.quantity === 0 ? 'Sold out' : `${s.quantity} in stock`}
                  aria-label={`${s.size}${s.quantity === 0 ? ', sold out' : ''}${user?.preferred_size === s.size ? ', your saved size' : ''}`}
                >
                  {s.size}
                </button>
              ))}
            </div>
            <p className="stock-note">
              {selected
                ? selected.quantity === 0
                  ? `Out of stock in ${selected.size} right now.`
                  : selected.quantity <= LOW_STOCK
                    ? `Only ${selected.quantity} left in ${selected.size}. Grab it soon.`
                    : `${selected.quantity} in stock in ${selected.size}.`
                : 'Pick a size to see stock. Crossed-out sizes are sold out.'}
              {selected && user?.preferred_size === selected.size && ' (your saved size)'}
            </p>

            {selected && selected.quantity === 0 && (
              <div className="waitlist">
                {!user ? (
                  <span className="muted small">
                    <Link to="/login">Log in</Link> to join the back-in-stock waitlist for {selected.size}.
                  </span>
                ) : waitlisted.includes(selected.size) ? (
                  <span className="small">
                    You're on the waitlist for {selected.size}.{' '}
                    <button type="button" className="link-button" onClick={() => handleWaitlist(selected.size, false)}>
                      Leave waitlist
                    </button>
                  </span>
                ) : (
                  <button type="button" className="btn btn-small" onClick={() => handleWaitlist(selected.size, true)}>
                    Join the waitlist for {selected.size}
                  </button>
                )}
              </div>
            )}

            {user && selected && selected.size !== user.preferred_size && (
              <button type="button" className="link-button remember-size" onClick={() => handleRememberSize(selected.size)}>
                Remember {selected.size} as my size
              </button>
            )}
            {notice && <p className="form-notice">{notice}</p>}
          </div>
        </div>
      </div>
      <RecentlyViewed excludeId={product.product_id} />
    </div>
  )
}
