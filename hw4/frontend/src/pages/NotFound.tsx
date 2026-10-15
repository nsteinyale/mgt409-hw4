import { Link } from 'react-router-dom'
import BulldogDash from '../components/BulldogDash'

export default function NotFound() {
  return (
    <div className="page narrow center">
      <h1>Page not found</h1>
      <p className="muted">That page wandered off campus. While you're here, take the bulldog for a run:</p>
      <BulldogDash autoFocus />
      <Link to="/" className="btn">
        Back to home
      </Link>
    </div>
  )
}
