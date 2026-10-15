import { useEffect, useState } from 'react'
import BulldogDash from './BulldogDash'

// When the connection drops, offer Bulldog Dash instead of a dead end (like Chrome's dino game).
export default function OfflineBanner() {
  const [offline, setOffline] = useState(!navigator.onLine)
  const [playing, setPlaying] = useState(false)

  useEffect(() => {
    const down = () => setOffline(true)
    const up = () => {
      setOffline(false)
      setPlaying(false)
    }
    window.addEventListener('offline', down)
    window.addEventListener('online', up)
    return () => {
      window.removeEventListener('offline', down)
      window.removeEventListener('online', up)
    }
  }, [])

  if (!offline) return null
  return (
    <div className="offline-banner" role="status">
      <div className="offline-row">
        <strong>You're offline.</strong> Products and chat will be back when your connection is.
        {!playing && (
          <button type="button" className="btn btn-small btn-light" onClick={() => setPlaying(true)}>
            Play Bulldog Dash while you wait
          </button>
        )}
      </div>
      {playing && <BulldogDash autoFocus />}
    </div>
  )
}
