import { useEffect, useState } from 'react'
import { onHarvardChase } from '../harvardChase'
import { BulldogRunner } from './Bulldog'

const DURATION_MS = 5200

// Friendly-rivalry easter egg: a Yale bulldog chases a Harvard dog across the bottom of the screen.
// Skipped entirely for shoppers whose device asks for reduced motion.
export default function HarvardChase() {
  const [run, setRun] = useState(0) // changes per chase, so the animation restarts

  useEffect(
    () =>
      onHarvardChase(() => {
        if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
        setRun(Date.now())
      }),
    [],
  )

  useEffect(() => {
    if (!run) return
    const t = window.setTimeout(() => setRun(0), DURATION_MS)
    return () => window.clearTimeout(t)
  }, [run])

  if (!run) return null
  return (
    <div className="harvard-chase" key={run} aria-hidden="true" data-testid="harvard-chase">
      <div className="chase-track">
        <div className="chase-runner harvard">
          <BulldogRunner team="harvard" size={96} />
        </div>
        <div className="chase-runner yale">
          <span className="chase-bubble">Boola boola!</span>
          <BulldogRunner team="yale" size={110} />
        </div>
      </div>
    </div>
  )
}
