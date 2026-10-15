// Easter egg: a Yale bulldog chases a Harvard dog across the bottom of the screen.
// Anyone can trigger it; <HarvardChase /> (in App) listens and plays it.

const EVENT = 'cc-harvard-chase'
const HARVARD = /harvard|the game/i

export function triggerHarvardChase() {
  window.dispatchEvent(new Event(EVENT))
}

export function maybeTriggerHarvardChase(text: string | null | undefined) {
  if (text && HARVARD.test(text)) triggerHarvardChase()
}

export function onHarvardChase(handler: () => void): () => void {
  window.addEventListener(EVENT, handler)
  return () => window.removeEventListener(EVENT, handler)
}
