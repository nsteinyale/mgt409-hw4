import { Link } from 'react-router-dom'
import CampusMap from '../components/CampusMap'

export default function About() {
  return (
    <div className="page narrow">
      <p className="eyebrow">About us</p>
      <h1>Your neighborhood Yale shop</h1>
      <p className="lead">
        Campus Customs is a New Haven shop dedicated to one thing: helping the Yale community wear its pride. Our store
        sits at 57 Broadway, right in the heart of campus life, and our online shop brings the same selection to
        Bulldogs wherever they are.
      </p>

      <h2>What we carry</h2>
      <p>
        Everything we sell is officially licensed Yale merchandise. You'll find hoodies, crewnecks, quarter-zips,
        tees, and fleece jackets, with designs for:
      </p>
      <ul className="check-list">
        <li>Yale's residential colleges, so you can show off your crest</li>
        <li>Bulldog sports teams, from football and hockey to sailing and fencing</li>
        <li>Yale's graduate and professional schools</li>
        <li>Proud family members: Yale Mom, Dad, Grandma, Grandpa, Aunt, Uncle, and more</li>
      </ul>

      <h2>Why shop with us</h2>
      <p>
        We think college gear should feel as good as it looks. We pick soft fabrics and classic designs that hold up
        from first-year move-in to reunion weekend. If you aren't sure what to pick, ask our shopping assistant in
        the chat window. It can help you compare styles, check sizes, and see what's in stock.
      </p>

      <h2>Visit us</h2>
      <p>
        Campus Customs
        <br />
        57 Broadway, New Haven, CT
      </p>
      <div className="about-map">
        <CampusMap />
      </div>

      <Link to="/products" className="btn">
        Browse the collection
      </Link>
    </div>
  )
}
