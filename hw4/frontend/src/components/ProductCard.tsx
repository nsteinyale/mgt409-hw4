import type { CSSProperties } from 'react'
import { Link } from 'react-router-dom'
import { formatPrice } from '../api'
import { swatch } from '../colors'

// Works for catalogue products (Products page, Home) and for cards the chat agent sends.
export interface CardProduct {
  product_id: string
  name: string
  price: number
  image_url: string
  description: string
  in_stock: boolean
  sizes_in_stock?: string[]
  colors?: string[]
}

interface Props {
  product: CardProduct
  className?: string
  style?: CSSProperties
}

export default function ProductCard({ product, className, style }: Props) {
  return (
    <Link to={`/products/${product.product_id}`} className={`product-card${className ? ` ${className}` : ''}`} style={style}>
      <div className="product-card-image">
        <img src={product.image_url} alt={product.name} loading="lazy" />
        {!product.in_stock && <span className="badge">Sold out</span>}
        <span className="card-view">View details →</span>
      </div>
      <div className="product-card-body">
        <h3>{product.name}</h3>
        <div className="card-price-row">
          <p className="price">{formatPrice(product.price)}</p>
          {product.colors && product.colors.length > 0 && (
            <span className="color-dots" aria-label={`Colors: ${product.colors.join(', ')}`}>
              {product.colors.slice(0, 5).map((c) => (
                <span key={c} className="color-dot" style={{ background: swatch(c) }} title={c} />
              ))}
            </span>
          )}
        </div>
        <p className="product-card-desc">{product.description}</p>
        {product.sizes_in_stock && product.sizes_in_stock.length > 0 && (
          <p className="product-card-sizes">In stock: {product.sizes_in_stock.join(' · ')}</p>
        )}
      </div>
    </Link>
  )
}
