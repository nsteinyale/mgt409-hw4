import { Link } from 'react-router-dom'
import BulldogDash from '../components/BulldogDash'

export default function Play() {
  return (
    <div className="page narrow center">
      <p className="eyebrow">Break time</p>
      <h1>Bulldog Dash</h1>
      <p className="muted">Help the bulldog dodge Harvard pennants. How far can you run?</p>
      <BulldogDash autoFocus />
      <Link to="/products" className="btn">
        Back to shopping
      </Link>
    </div>
  )
}
