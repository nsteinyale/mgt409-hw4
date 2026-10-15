import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchProducts, type Product } from '../api'
import ProductCard from '../components/ProductCard'
import { usePublishPageContext } from '../pageContext'
import CampusMap from '../components/CampusMap'
import { triggerHarvardChase } from '../harvardChase'

const FEATURED_IDS = [
  'basic-hoodie-big-yale',
  '2025-yale-vs-harvard-t-shirt',
  'branford-1-4-zip',
  'yale-mom-crewneck',
]

const TILES = [
  {
    title: 'Rep your residential college',
    text: 'From Benjamin Franklin to Trumbull, find the crest you call home.',
    link: '/products?collection=colleges',
  },
  {
    title: 'Game day ready',
    text: 'Hoodies, tees, and crewnecks for every Bulldog team.',
    link: '/products?collection=sports',
  },
  {
    title: 'Gear for the whole family',
    text: 'Yale Mom, Yale Dad, Yale Grandpa: everyone gets to cheer.',
    link: '/products?collection=family',
  },
]

export default function Home() {
  const [featured, setFeatured] = useState<Product[]>([])
  usePublishPageContext({ page_type: 'home', title: 'Fan favorites', product_ids: featured.map((p) => p.product_id) })

  // Easter egg: once per visit, a bulldog chases a Harvard dog across the home page
  useEffect(() => {
    if (sessionStorage.getItem('cc_chase_seen')) return
    const t = window.setTimeout(() => {
      sessionStorage.setItem('cc_chase_seen', '1')
      triggerHarvardChase()
    }, 1200)
    return () => window.clearTimeout(t)
  }, [])

  useEffect(() => {
    fetchProducts()
      .then((all) => setFeatured(FEATURED_IDS.map((id) => all.find((p) => p.product_id === id)).filter((p): p is Product => !!p)))
      .catch(() => setFeatured([]))
  }, [])

  return (
    <>
      <section className="hero">
        <div className="hero-inner">
          <p className="eyebrow">Campus Customs · New Haven</p>
          <h1>Bulldog pride, made comfortable.</h1>
          <p>
            Officially licensed Yale apparel for students, alumni, and the families cheering them on. Cozy layers,
            classic crests, and game day favorites, all from our shop on Broadway.
          </p>
          <div className="hero-actions">
            <Link to="/products" className="btn btn-light">
              Shop all products
            </Link>
            <Link to="/about" className="btn btn-outline-light">
              Our story
            </Link>
          </div>
        </div>
      </section>

      <section className="section">
        <div className="tiles">
          {TILES.map((tile) => (
            <Link key={tile.title} to={tile.link} className="tile">
              <h2>{tile.title}</h2>
              <p>{tile.text}</p>
              <span className="tile-link">Shop now →</span>
            </Link>
          ))}
        </div>
      </section>

      <section className="section">
        <div className="section-head">
          <h2>Fan favorites</h2>
          <Link to="/products">View all →</Link>
        </div>
        <div className="product-grid">
          {featured.map((p) => (
            <ProductCard key={p.product_id} product={p} />
          ))}
        </div>
      </section>

      <section className="section visit">
        <div className="visit-grid">
          <div>
            <h2>Stop by the shop</h2>
            <p>
              Want to feel the fleece before you buy? Visit us at 57 Broadway in New Haven, steps from campus. Not
              nearby? Dan, our chat assistant (bottom right), can help you find the right fit online.
            </p>
          </div>
          <CampusMap />
        </div>
      </section>
    </>
  )
}
