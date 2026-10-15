import { useEffect, useRef, useState } from 'react'

// "Bulldog Dash": a tiny endless runner (like Chrome's offline dino game). The bulldog jumps over
// crimson Harvard pennants and "H" blocks. Space / Up arrow / tap to jump. High score stays in this browser.

const W = 720
const H = 200
const GROUND = 168
const GRAVITY = 0.75
const JUMP = -13
const HI_KEY = 'cc_bulldog_dash_hi'

type Phase = 'ready' | 'running' | 'over'
interface Obstacle {
  x: number
  w: number
  h: number
  kind: 'pennant' | 'block'
}

function readHigh(): number {
  return Number(localStorage.getItem(HI_KEY) ?? 0) || 0
}

function drawDog(ctx: CanvasRenderingContext2D, x: number, y: number, frame: number, running: boolean) {
  const legSwing = running ? Math.sin(frame * 0.5) * 5 : 0
  ctx.fillStyle = '#f1dfc4'
  // legs
  ctx.fillRect(x + 8, y + 26, 6, 14 + legSwing)
  ctx.fillRect(x + 20, y + 26, 6, 14 - legSwing)
  ctx.fillRect(x + 34, y + 26, 6, 14 + legSwing)
  ctx.fillRect(x + 44, y + 26, 6, 14 - legSwing)
  // body + navy sweater with gold Y
  ctx.beginPath()
  ctx.ellipse(x + 28, y + 22, 26, 12, 0, 0, Math.PI * 2)
  ctx.fill()
  ctx.fillStyle = '#00356b'
  ctx.fillRect(x + 14, y + 13, 26, 17)
  ctx.fillStyle = '#d4af37'
  ctx.font = 'bold 12px Georgia'
  ctx.fillText('Y', x + 23, y + 27)
  // head
  ctx.fillStyle = '#f1dfc4'
  ctx.beginPath()
  ctx.arc(x + 56, y + 12, 11, 0, Math.PI * 2)
  ctx.fill()
  ctx.fillStyle = '#6b4a32'
  ctx.beginPath()
  ctx.moveTo(x + 50, y + 3)
  ctx.lineTo(x + 47, y - 6)
  ctx.lineTo(x + 56, y + 1)
  ctx.fill()
  ctx.fillStyle = '#1c1c1c'
  ctx.beginPath()
  ctx.arc(x + 59, y + 9, 2, 0, Math.PI * 2)
  ctx.fill()
  ctx.beginPath()
  ctx.arc(x + 66, y + 13, 2.4, 0, Math.PI * 2)
  ctx.fill()
}

function drawObstacle(ctx: CanvasRenderingContext2D, o: Obstacle) {
  ctx.fillStyle = '#a51c30'
  if (o.kind === 'block') {
    ctx.fillRect(o.x, GROUND - o.h, o.w, o.h)
    ctx.fillStyle = '#fff'
    ctx.font = 'bold 18px Georgia'
    ctx.textAlign = 'center'
    ctx.fillText('H', o.x + o.w / 2, GROUND - o.h / 2 + 7)
    ctx.textAlign = 'left'
  } else {
    ctx.fillStyle = '#5b4636'
    ctx.fillRect(o.x, GROUND - o.h, 3, o.h)
    ctx.fillStyle = '#a51c30'
    ctx.beginPath()
    ctx.moveTo(o.x + 3, GROUND - o.h)
    ctx.lineTo(o.x + o.w, GROUND - o.h + 9)
    ctx.lineTo(o.x + 3, GROUND - o.h + 18)
    ctx.fill()
  }
}

export default function BulldogDash({ autoFocus = false }: { autoFocus?: boolean }) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [phase, setPhase] = useState<Phase>('ready')
  const [score, setScore] = useState(0)
  const [high, setHigh] = useState(readHigh)
  const state = useRef({ y: GROUND - 40, vy: 0, obstacles: [] as Obstacle[], speed: 6, score: 0, frame: 0, nextGap: 400, phase: 'ready' as Phase })

  function jump() {
    const s = state.current
    if (s.phase !== 'running') {
      Object.assign(s, { y: GROUND - 40, vy: 0, obstacles: [], speed: 6, score: 0, frame: 0, nextGap: 400, phase: 'running' })
      setPhase('running')
      return
    }
    if (s.y >= GROUND - 40) s.vy = JUMP
  }

  useEffect(() => {
    if (autoFocus) canvasRef.current?.focus()
  }, [autoFocus])

  useEffect(() => {
    const canvas = canvasRef.current
    const ctx = canvas?.getContext('2d')
    if (!canvas || !ctx) return
    let raf = 0

    const tick = () => {
      const s = state.current
      s.frame += 1
      if (s.phase === 'running') {
        s.vy += GRAVITY
        s.y = Math.min(GROUND - 40, s.y + s.vy)
        s.speed += 0.0025
        s.score += s.speed * 0.05
        for (const o of s.obstacles) o.x -= s.speed
        s.obstacles = s.obstacles.filter((o) => o.x + o.w > -10)
        s.nextGap -= s.speed
        if (s.nextGap <= 0) {
          const block = Math.random() < 0.55
          s.obstacles.push(block ? { x: W + 10, w: 26, h: 26 + Math.random() * 18, kind: 'block' } : { x: W + 10, w: 26, h: 38, kind: 'pennant' })
          s.nextGap = 260 + Math.random() * 280 + s.speed * 12
        }
        // collision (slightly forgiving boxes)
        const dog = { x: 64, y: s.y, w: 60, h: 40 }
        const hit = s.obstacles.some(
          (o) => dog.x + dog.w - 8 > o.x && dog.x + 8 < o.x + o.w && dog.y + dog.h - 4 > GROUND - o.h,
        )
        if (hit) {
          s.phase = 'over'
          setPhase('over')
          const final = Math.floor(s.score)
          if (final > readHigh()) {
            localStorage.setItem(HI_KEY, String(final))
            setHigh(final)
          }
        }
        if (s.frame % 6 === 0) setScore(Math.floor(s.score))
      }

      // draw
      ctx.clearRect(0, 0, W, H)
      const sky = ctx.createLinearGradient(0, 0, 0, H)
      sky.addColorStop(0, '#e8f0fb')
      sky.addColorStop(1, '#fbf8f3')
      ctx.fillStyle = sky
      ctx.fillRect(0, 0, W, H)
      // distant Yale skyline (parallax)
      ctx.fillStyle = 'rgba(0, 53, 107, 0.12)'
      const off = (s.frame * (s.phase === 'running' ? 0.6 : 0.1)) % 240
      for (let i = -1; i < 5; i++) {
        const bx = i * 240 - off
        ctx.fillRect(bx + 20, 110, 40, 58)
        ctx.fillRect(bx + 30, 80, 20, 30) // tower
        ctx.beginPath()
        ctx.moveTo(bx + 30, 80)
        ctx.lineTo(bx + 40, 64)
        ctx.lineTo(bx + 50, 80)
        ctx.fill()
        ctx.fillRect(bx + 110, 124, 70, 44)
      }
      ctx.fillStyle = '#2f6b3a'
      ctx.fillRect(0, GROUND, W, 3)
      ctx.fillStyle = '#c9d8c3'
      ctx.fillRect(0, GROUND + 3, W, H - GROUND)
      for (const o of s.obstacles) drawObstacle(ctx, o)
      drawDog(ctx, 64, s.y, s.frame, s.phase === 'running')

      ctx.fillStyle = '#00356b'
      ctx.font = 'bold 14px Georgia'
      ctx.textAlign = 'right'
      ctx.fillText(`HI ${String(readHigh()).padStart(5, '0')}   ${String(Math.floor(s.score)).padStart(5, '0')}`, W - 14, 24)
      ctx.textAlign = 'center'
      if (s.phase === 'ready') ctx.fillText('Press Space or tap to run, Bulldog!', W / 2, 60)
      if (s.phase === 'over') {
        ctx.fillStyle = '#a51c30'
        ctx.font = 'bold 18px Georgia'
        ctx.fillText('Tackled by Harvard!', W / 2, 56)
        ctx.fillStyle = '#00356b'
        ctx.font = '14px Georgia'
        ctx.fillText('Press Space or tap to run again', W / 2, 80)
      }
      ctx.textAlign = 'left'
      raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [])

  return (
    <div className="bulldog-dash" data-phase={phase} data-score={score}>
      <canvas
        ref={canvasRef}
        width={W}
        height={H}
        tabIndex={0}
        aria-label="Bulldog Dash game. Press Space or tap to jump."
        onPointerDown={(e) => {
          e.currentTarget.focus()
          jump()
        }}
        onKeyDown={(e) => {
          if (e.code === 'Space' || e.code === 'ArrowUp') {
            e.preventDefault()
            jump()
          }
        }}
      />
      <p className="bulldog-dash-meta">
        Score <strong>{score}</strong> · Best <strong>{high}</strong> · Space, ↑ or tap to jump
      </p>
    </div>
  )
}
