import { useEffect, useRef, useState } from 'react'

// Illustrated (not to scale) map of downtown New Haven on the historic nine-square grid.
// When it scrolls into view it "flies in": the view zooms toward 57 Broadway while a gold
// path traces from Old Campus to the shop. No outside map service needed.

const STORE = { x: 96, y: 84 }

export default function CampusMap() {
  const ref = useRef<HTMLDivElement>(null)
  const [inView, setInView] = useState(false)

  useEffect(() => {
    const el = ref.current
    if (!el) return
    const io = new IntersectionObserver(([entry]) => entry.isIntersecting && setInView(true), { threshold: 0.35 })
    io.observe(el)
    return () => io.disconnect()
  }, [])

  return (
    <div ref={ref} className={`campus-map${inView ? ' in-view' : ''}`} data-in-view={inView ? 'true' : 'false'}>
      <svg viewBox="0 0 600 380" role="img" aria-label="Illustrated map of downtown New Haven showing Campus Customs at 57 Broadway, near Old Campus and the New Haven Green">
        <defs>
          <pattern id="grass" width="10" height="10" patternUnits="userSpaceOnUse">
            <rect width="10" height="10" fill="#cfe3c4" />
            <circle cx="3" cy="3" r="1" fill="#b6d3a7" />
          </pattern>
        </defs>
        <rect width="600" height="380" fill="#f7f1e3" />
        <g className="map-zoom">
          {/* city blocks of the nine-square grid */}
          {[0, 1, 2].map((r) =>
            [0, 1, 2].map((c) => (
              <rect key={`${r}-${c}`} x={130 + c * 150} y={50 + r * 110} width={130} height={92} rx="6" fill="#ece3cf" />
            )),
          )}
          {/* the New Haven Green (center square) */}
          <rect x="280" y="160" width="130" height="92" rx="6" fill="url(#grass)" />
          <text x="345" y="210" className="map-label park">The Green</text>
          {/* Old Campus (Yale) */}
          <rect x="130" y="160" width="130" height="92" rx="6" fill="#dbe5f1" />
          <text x="195" y="203" className="map-label campus">Old Campus</text>
          <text x="195" y="218" className="map-label small">Yale</text>
          {/* streets */}
          <g className="streets">
            <path d="M0 155 H600" /> <path d="M0 257 H600" />
            <path d="M125 0 V380" /> <path d="M275 0 V380" /> <path d="M415 0 V380" />
            <path d="M125 155 L20 40" className="broadway" />
          </g>
          <text x="520" y="150" className="map-label street">Elm St</text>
          <text x="500" y="272" className="map-label street">Chapel St</text>
          <text x="118" y="360" className="map-label street" transform="rotate(-90 118 360)">York St</text>
          <text x="268" y="360" className="map-label street" transform="rotate(-90 268 360)">College St</text>
          <text x="408" y="360" className="map-label street" transform="rotate(-90 408 360)">Church St</text>
          <text x="40" y="74" className="map-label street" transform="rotate(48 40 74)">Broadway</text>
          {/* route from Old Campus to the shop */}
          <path className="map-route" d={`M195 190 C 175 150, 130 120, ${STORE.x} ${STORE.y}`} />
          {/* store pin */}
          <g className="map-pin" transform={`translate(${STORE.x} ${STORE.y})`}>
            <circle r="18" className="pin-pulse" />
            <path d="M0 0 C -12 -14 -12 -30 0 -32 C 12 -30 12 -14 0 0 Z" fill="#00356b" stroke="#d4af37" strokeWidth="2.5" />
            <circle cy="-21" r="5" fill="#d4af37" />
          </g>
          <g className="map-callout" transform={`translate(${STORE.x + 18} ${STORE.y - 50})`}>
            <rect width="150" height="40" rx="8" fill="#00356b" />
            <text x="10" y="17" className="map-callout-title">Campus Customs</text>
            <text x="10" y="31" className="map-callout-sub">57 Broadway</text>
          </g>
        </g>
        <text x="12" y="372" className="map-label small note">Illustration, not to scale</text>
      </svg>
      <a
        className="map-directions"
        href="https://www.google.com/maps/search/?api=1&query=57+Broadway+New+Haven+CT"
        target="_blank"
        rel="noopener noreferrer"
      >
        Get directions ↗
      </a>
    </div>
  )
}
