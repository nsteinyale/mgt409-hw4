// Original cartoon bulldog artwork for Campus Customs ("Dan", the chat assistant).
// Inspired by the Yale bulldog tradition, but our own drawing (not the official mascot).

interface FaceProps {
  size?: number
  talking?: boolean // mouth moves while a reply "plays"
  thinking?: boolean // head tilts while the assistant is working
}

export function BulldogFace({ size = 44, talking = false, thinking = false }: FaceProps) {
  return (
    <svg
      className={`bulldog-face${talking ? ' talking' : ''}${thinking ? ' thinking' : ''}`}
      width={size}
      height={size}
      viewBox="0 0 120 120"
      role="img"
      aria-label={talking ? 'Dan the bulldog, talking' : 'Dan the bulldog'}
      data-talking={talking ? 'true' : 'false'}
    >
      <g className="bd-head">
        {/* ears */}
        <path d="M20 36 Q8 10 38 20 Q34 32 30 42 Z" fill="#6b4a32" />
        <path d="M100 36 Q112 10 82 20 Q86 32 90 42 Z" fill="#6b4a32" />
        {/* head and eye patch */}
        <ellipse cx="60" cy="62" rx="44" ry="40" fill="#f1dfc4" />
        <ellipse cx="41" cy="50" rx="16" ry="14" fill="#c8996a" />
        {/* brow wrinkles */}
        <path d="M46 32 Q60 26 74 32" stroke="#c8996a" strokeWidth="3" fill="none" strokeLinecap="round" />
        <path d="M50 39 Q60 35 70 39" stroke="#c8996a" strokeWidth="2.5" fill="none" strokeLinecap="round" />
        {/* eyes */}
        <g className="bd-eyes">
          <circle cx="42" cy="52" r="6.5" fill="#1c1c1c" />
          <circle cx="78" cy="52" r="6.5" fill="#1c1c1c" />
          <circle cx="44" cy="50" r="2" fill="#fff" />
          <circle cx="80" cy="50" r="2" fill="#fff" />
        </g>
        {/* muzzle and nose */}
        <ellipse cx="60" cy="82" rx="31" ry="20" fill="#fbf3e6" />
        <path d="M49 68 Q60 61 71 68 Q67 77 60 78 Q53 77 49 68 Z" fill="#2b2b2b" />
        <path d="M60 78 L60 85" stroke="#2b2b2b" strokeWidth="2" />
        {/* mouth: a closed smile, plus an open mouth that grows while talking */}
        <ellipse className="bd-mouth-open" cx="60" cy="91" rx="11" ry="7" fill="#5a1f24" />
        <ellipse className="bd-mouth-open" cx="60" cy="94" rx="6.5" ry="3" fill="#e46b7b" />
        <path d="M43 86 Q51 93 60 86 Q69 93 77 86" stroke="#2b2b2b" strokeWidth="2.2" fill="none" strokeLinecap="round" />
        {/* the bulldog underbite */}
        <path d="M47 88 l2.5 -5 l2.5 5 Z" fill="#fff" />
        <path d="M68 88 l2.5 -5 l2.5 5 Z" fill="#fff" />
      </g>
      {/* navy collar with a gold Y tag */}
      <path d="M26 100 Q60 118 94 100 L94 108 Q60 126 26 108 Z" fill="#00356b" />
      <circle cx="60" cy="114" r="6" fill="#d4af37" />
      <text x="60" y="117.5" textAnchor="middle" fontSize="8" fontWeight="700" fill="#00356b" fontFamily="Georgia, serif">
        Y
      </text>
    </svg>
  )
}

interface RunnerProps {
  team: 'yale' | 'harvard'
  size?: number
}

// Side view, running (legs animate with CSS). Used by the Harvard chase.
export function BulldogRunner({ team, size = 110 }: RunnerProps) {
  const coat = team === 'yale' ? '#f1dfc4' : '#b9b2a8'
  const sweater = team === 'yale' ? '#00356b' : '#a51c30'
  const letter = team === 'yale' ? 'Y' : 'H'
  return (
    <svg className={`bulldog-runner ${team}`} width={size} height={size * 0.62} viewBox="0 0 120 74" aria-hidden="true">
      <g className="leg leg-a"><rect x="30" y="46" width="8" height="22" rx="4" fill={coat} /></g>
      <g className="leg leg-b"><rect x="44" y="46" width="8" height="22" rx="4" fill={coat} /></g>
      <g className="leg leg-b"><rect x="72" y="46" width="8" height="22" rx="4" fill={coat} /></g>
      <g className="leg leg-a"><rect x="86" y="46" width="8" height="22" rx="4" fill={coat} /></g>
      <path d="M22 36 Q10 30 12 22" stroke={coat} strokeWidth="5" fill="none" strokeLinecap="round" />
      <ellipse cx="58" cy="40" rx="38" ry="17" fill={coat} />
      <path d="M36 28 Q58 22 82 28 L84 52 Q58 58 34 52 Z" fill={sweater} />
      <text x="59" y="47" textAnchor="middle" fontSize="16" fontWeight="700" fill={team === 'yale' ? '#d4af37' : '#fff'} fontFamily="Georgia, serif">
        {letter}
      </text>
      <circle cx="97" cy="30" r="15" fill={coat} />
      <path d="M90 17 Q86 6 97 12 Z" fill="#6b4a32" />
      <ellipse cx="108" cy="35" rx="7" ry="6" fill="#fbf3e6" />
      <circle cx="113" cy="32" r="2.6" fill="#2b2b2b" />
      <circle cx="100" cy="26" r="2.4" fill="#1c1c1c" />
      <path d="M104 41 Q108 44 112 41" stroke="#2b2b2b" strokeWidth="1.6" fill="none" />
    </svg>
  )
}
