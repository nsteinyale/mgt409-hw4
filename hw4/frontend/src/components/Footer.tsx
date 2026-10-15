import { Link } from 'react-router-dom'

export default function Footer() {
  return (
    <footer className="site-footer">
      <div className="footer-grid">
        <div>
          <h3>Come see us</h3>
          <p>
            Campus Customs
            <br />
            57 Broadway, New Haven, CT
          </p>
        </div>
        <div>
          <h3>Shop</h3>
          <Link to="/products">All products</Link>
          <Link to="/about">About us</Link>
          <Link to="/play">Play Bulldog Dash</Link>
        </div>
        <div>
          <h3>Your account</h3>
          <Link to="/login">Log in</Link>
          <Link to="/create-account">Create account</Link>
        </div>
      </div>
      <p className="footer-note">
        © {new Date().getFullYear()} Campus Customs. Officially licensed Yale merchandise. Class project for MGT 409.
      </p>
    </footer>
  )
}
