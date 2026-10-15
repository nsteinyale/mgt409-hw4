import { Link, NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth'
import { useChatResults } from '../chatResults'

const MAIN_LINKS = [
  { to: '/', label: 'Home', end: true },
  { to: '/products', label: 'Products', end: false },
  { to: '/about', label: 'About us', end: false },
]

const navClass = ({ isActive }: { isActive: boolean }) => (isActive ? 'nav-link active' : 'nav-link')

export default function NavBar() {
  const { user, loading, logout } = useAuth()
  const { clear: clearChatResults } = useChatResults()
  const navigate = useNavigate()

  async function handleLogout() {
    await logout()
    clearChatResults() // don't leave the last customer's search results on screen
    navigate('/')
  }

  return (
    <header className="site-header">
      <div className="announcement">Officially licensed Yale merchandise · Visit us at 57 Broadway, New Haven</div>
      <nav className="navbar" aria-label="Main">
        <Link to="/" className="brand">
          <span className="brand-mark">CC</span>
          <span className="brand-text">
            Campus Customs
            <small>Yale Bulldog Blue</small>
          </span>
        </Link>
        <div className="nav-links">
          {MAIN_LINKS.map((link) => (
            <NavLink key={link.to} to={link.to} end={link.end} className={navClass}>
              {link.label}
            </NavLink>
          ))}
        </div>
        <div className="nav-account">
          {loading ? null : user ? (
            <>
              <span className="nav-greeting">Hi, {user.first_name}</span>
              <button type="button" className="btn btn-small btn-outline" onClick={handleLogout}>
                Log out
              </button>
            </>
          ) : (
            <>
              <NavLink to="/login" className={navClass}>
                Log in
              </NavLink>
              <NavLink to="/create-account" className="btn btn-small">
                Create account
              </NavLink>
            </>
          )}
        </div>
      </nav>
    </header>
  )
}
