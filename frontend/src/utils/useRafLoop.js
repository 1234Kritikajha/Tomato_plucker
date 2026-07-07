import { useCallback, useEffect, useRef } from 'react'

// Simple requestAnimationFrame loop utility.
// tick(dtMs) will be called each frame.
export default function useRafLoop(enabled, tick) {
  const rafRef = useRef(null)
  const lastRef = useRef(null)

  const stop = useCallback(() => {
    if (rafRef.current) cancelAnimationFrame(rafRef.current)
    rafRef.current = null
    lastRef.current = null
  }, [])

  const start = useCallback(() => {
    if (!enabled) return
    if (rafRef.current) return

    lastRef.current = performance.now()

    const loop = (now) => {
      if (!enabled) return
      const last = lastRef.current ?? now
      const dt = now - last
      lastRef.current = now
      tick?.(dt)
      rafRef.current = requestAnimationFrame(loop)
    }

    rafRef.current = requestAnimationFrame(loop)
  }, [enabled, tick])

  useEffect(() => {
    if (enabled) start()
    else stop()

    return () => stop()
  }, [enabled, start, stop])
}

