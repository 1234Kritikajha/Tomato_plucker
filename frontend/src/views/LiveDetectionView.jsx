import { useEffect, useRef, useState } from 'react'
import apiClient from '../api/client.js'
import useRafLoop from '../utils/useRafLoop.js'
import { captureFrameToBlob, getUserMediaStream } from '../utils/cameraCapture.js'


// Minimal overlay helper: draws bounding boxes over the video.
// Uses server-provided detection schema (bounding_box: {x,y,width,height}).
const drawDetections = ({ ctx, detections, video, canvas }) => {
  if (!ctx || !detections || !video) return

  const vW = video.videoWidth
  const vH = video.videoHeight
  if (!vW || !vH) return

  // Canvas is sized to match the displayed video box (via CSS 100%).
  const cW = canvas.width
  const cH = canvas.height
  if (!cW || !cH) return

  ctx.clearRect(0, 0, cW, cH)

  const scale = Math.max(cW / vW, cH / vH)
  const renderedW = vW * scale
  const renderedH = vH * scale
  const offsetX = (cW - renderedW) / 2
  const offsetY = (cH - renderedH) / 2

  for (const d of detections) {
    const bb = d?.bounding_box
    if (!bb) continue

    const x = bb.x * scale + offsetX
    const y = bb.y * scale + offsetY
    const w = bb.width * scale
    const h = bb.height * scale

    ctx.strokeStyle = 'rgba(34, 197, 94, 0.95)'
    ctx.lineWidth = Math.max(2, Math.floor(scale))
    ctx.strokeRect(x, y, w, h)

    const label = d?.classification?.ripeness
    const text = label ? `${label}` : 'Tomato'
    ctx.fillStyle = 'rgba(34, 197, 94, 0.95)'
    ctx.font = '14px sans-serif'
    ctx.fillText(text, x + 4, Math.max(14, y + 18))
  }
}


export default function LiveDetectionView() {
  const videoRef = useRef(null)
  const canvasRef = useRef(null)
  const streamRef = useRef(null)


  const [running, setRunning] = useState(false)
  const [status, setStatus] = useState('Idle')
  const [fps, setFps] = useState(0)
  const [detectionsCount, setDetectionsCount] = useState(0)
  const [modelLabel, setModelLabel] = useState('')

  const [facingMode, setFacingMode] = useState('environment')
  const [isOpen, setIsOpen] = useState(false)

  const dropdownRef = useRef(null)


  // Throttle server calls; mobile webcams can produce many frames.
  const [minFrameIntervalMs, setMinFrameIntervalMs] = useState(700)
  const pendingRef = useRef(false)
  const lastCallAtRef = useRef(0)

  // Last detection boxes for overlay.
  const [detections, setDetections] = useState([])

  const [error, setError] = useState(null)

  const stopCamera = async () => {
    setRunning(false)
    setStatus('Stopping')
    pendingRef.current = false

    try {
      const stream = streamRef.current
      if (stream) {
        stream.getTracks().forEach((t) => t.stop())
      }
    } catch (e) {
      // ignore
    } finally {
      streamRef.current = null
      if (videoRef.current) {
        try {
          videoRef.current.srcObject = null
        } catch (_) {}
      }
      setStatus('Idle')
    }
  }

  const startCamera = async (nextFacingMode = facingMode) => {
    setError(null)
    setDetectionsCount(0)
    pendingRef.current = false
    lastCallAtRef.current = 0

    try {

      setStatus('Starting camera')
      const stream = await getUserMediaStream({
        facingMode: nextFacingMode,
      })


      streamRef.current = stream
      if (videoRef.current) {
        videoRef.current.srcObject = stream
        await videoRef.current.play()
      }

      setRunning(true)
      setStatus('Running')
    } catch (e) {
      setRunning(false)
      setStatus('Camera error')
      const msg = e?.message || ''
      if (msg.includes('HTTPS')) {
        setError('Camera access requires HTTPS (or localhost).')
      } else if (msg.toLowerCase().includes('permission')) {
        setError('Camera permission denied. Enable camera access in your browser settings.')
      } else if (msg.toLowerCase().includes('not supported')) {
        setError('Your browser does not support camera capture (getUserMedia).')
      } else {
        setError(msg ? `Camera error: ${msg}` : 'Camera permission denied or camera unavailable.')
      }
      console.error(e)

    }
  }

  const switchCamera = async (nextFacingMode) => {
    setFacingMode(nextFacingMode)
    setIsOpen(false)
    if (!running) return

    await stopCamera()
    await startCamera(nextFacingMode)
  }

  // FPS estimate (local render loop)
  useRafLoop(running, (dtMs) => {
    if (!dtMs || dtMs <= 0) return
    const currentFps = Math.round(1000 / dtMs)
    setFps((prev) => (Number.isFinite(currentFps) ? currentFps : prev))
  })

  // Keep canvas aligned with the current rendered video size.
  useEffect(() => {
    const canvas = canvasRef.current
    const video = videoRef.current
    if (!canvas || !video) return

    const syncSize = () => {
      // Use the element's client size so our overlay matches object-fit cover.
      const rect = video.getBoundingClientRect()
      const dpr = window.devicePixelRatio || 1
      canvas.width = Math.max(1, Math.floor(rect.width * dpr))
      canvas.height = Math.max(1, Math.floor(rect.height * dpr))
      const ctx = canvas.getContext('2d')
      if (ctx) ctx.setTransform(1, 0, 0, 1, 0, 0)
    }

    syncSize()
    window.addEventListener('resize', syncSize)
    return () => window.removeEventListener('resize', syncSize)
  }, [running])

  useRafLoop(running, async () => {
    if (pendingRef.current) return

    const now = Date.now()
    if (now - lastCallAtRef.current < minFrameIntervalMs) return

    const video = videoRef.current
    if (!video) return
    if (!video.videoWidth || !video.videoHeight) return

    pendingRef.current = true
    lastCallAtRef.current = now
    try {
      setStatus('Analyzing...')

      const blob = await captureFrameToBlob({ video, mimeType: 'image/jpeg', quality: 0.85 })
      if (!blob) throw new Error('Failed to capture frame')

      const file = new File([blob], `frame_${now}.jpg`, { type: 'image/jpeg' })
      const formData = new FormData()
      formData.append('file', file)

      const result = await apiClient.upload('/predict', formData)
      const nextDetections = result?.detections ?? []

      setDetectionsCount(result?.summary?.total_tomatoes_detected ?? 0)
      setModelLabel(result?.model_info?.localization_source ? `Model: ${result.model_info.localization_source}` : '')
      setDetections(nextDetections)

      const canvas = canvasRef.current
      const videoEl = videoRef.current
      if (canvas && videoEl) {
        const ctx = canvas.getContext('2d')
        drawDetections({ ctx, detections: nextDetections, video: videoEl, canvas })
      }

      setStatus('Running')


    } catch (e) {
      console.error('Live detection failed', e)
      setStatus('Error')
      setError('Live detection failed. Retrying may work.')
      // allow next frame
      pendingRef.current = false
      return
    }

    pendingRef.current = false
  })

  useEffect(() => {
    const onDocMouseDown = (e) => {
      if (!isOpen) return
      const el = dropdownRef.current
      if (!el) return
      if (!el.contains(e.target)) setIsOpen(false)
    }

    const onKeyDown = (e) => {
      if (e.key === 'Escape') setIsOpen(false)
    }

    document.addEventListener('mousedown', onDocMouseDown)
    document.addEventListener('keydown', onKeyDown)

    return () => {
      document.removeEventListener('mousedown', onDocMouseDown)
      document.removeEventListener('keydown', onKeyDown)
    }
  }, [isOpen])

  useEffect(() => {
    return () => {
      // cleanup on unmount
      stopCamera()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])


  return (
    <section className="animate-fadeIn">
      <div className="mb-8">
        <h1 className="text-3xl font-bold bg-gradient-to-r from-[var(--text-primary)] to-[var(--text-secondary)] bg-clip-text text-transparent">
          Live Detection
        </h1>
        <p className="mt-2 text-sm text-[var(--text-muted)]">
          Real-time tomato detection and classification using mobile/webcam feed
        </p>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <div className="card">
            <div className="card-header">

              <div className="flex items-center gap-3">
                <div className="rounded-lg bg-green-100 p-2 dark:bg-green-900/30">


                  <svg className="h-5 w-5 text-green-600 dark:text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                  </svg>
                </div>
                <h3 className="card-title">Camera Feed</h3>
              </div>
              <div className="flex flex-wrap gap-2 items-center">
                <div ref={dropdownRef} className="relative">
                  <button
                    type="button"
                    className={
                      'inline-flex w-full items-center justify-between gap-2 rounded-lg border px-3 py-2 text-sm font-medium transition shadow-sm focus:outline-none focus:ring-2 focus:ring-emerald-400/70 dark:focus:ring-emerald-400/70 ' +
                      'hover:shadow-[0_0_10px_rgba(16,185,129,0.12)] ' +
                      (isOpen
                        ? 'shadow-[0_0_10px_rgba(16,185,129,0.2)] '
                        : '') +
                      ' ' +
                      'border-[var(--border-color)] bg-[var(--bg-card)] text-[var(--text-primary)]'
                    }
                    onClick={() => {
                      setIsOpen((v) => !v)
                    }}
                    aria-haspopup="listbox"
                    aria-expanded={isOpen}
                  >
                    <span className="truncate">
                      {facingMode === 'user' ? 'Front camera' : 'Rear camera'}
                    </span>
                    <span
                      aria-hidden="true"
                      className={
                        'inline-flex h-5 w-5 items-center justify-center transition-transform duration-200 rotate-0 ' +
                        (isOpen ? 'rotate-180' : '')
                      }
                    >
                      <span className="text-base leading-none">v</span>
                    </span>

                  </button>

                  {isOpen && (
                    <div
                      className="absolute z-50 mt-2 w-full overflow-hidden rounded-lg border border-[var(--border-color)] bg-[var(--bg-card)] shadow-lg"
                      role="listbox"
                      aria-label="Camera facing mode options"
                    >
                      <button
                        type="button"
                        className="block w-full px-3 py-2 text-left text-sm text-[var(--text-primary)] transition hover:bg-[var(--bg-card-hover)] hover:text-[var(--accent-primary)]"
                        role="option"
                        aria-selected={facingMode === 'environment'}
                        onClick={() => switchCamera('environment')}
                      >
                        Rear camera
                      </button>
                      <button
                        type="button"
                        className="block w-full px-3 py-2 text-left text-sm text-[var(--text-primary)] transition hover:bg-[var(--bg-card-hover)] hover:text-[var(--accent-primary)]"
                        role="option"
                        aria-selected={facingMode === 'user'}
                        onClick={() => switchCamera('user')}
                      >
                        Front camera
                      </button>
                    </div>
                  )}
                </div>

                <button className="btn btn-primary" onClick={startCamera} disabled={running}>
                  Start Camera
                </button>

                <button className="btn btn-secondary" onClick={stopCamera} disabled={!running}>
                  Stop
                </button>
              </div>

            </div>
            <div className="card-body">
              <div className="aspect-video rounded-xl bg-[var(--bg-card-hover)] flex items-center justify-center border-2 border-dashed border-[var(--border-color)] relative overflow-hidden">

                {/* Canvas overlay for bounding boxes */}
                <canvas
                  ref={canvasRef}
                  className="absolute inset-0 w-full h-full pointer-events-none"
                />

                {running ? (
                  <video
                    ref={videoRef}
                    className="absolute inset-0 w-full h-full object-cover"
                    playsInline
                    muted
                  />
                ) : (

                  <div className="text-center">
                    <div className="text-6xl mb-4 animate-pulse">📷</div>
                    <div className="text-lg font-medium text-[var(--text-secondary)]">Camera Preview</div>
                    <div className="text-sm mt-2 text-[var(--text-muted)]">Click "Start Camera" to begin detection</div>
                  </div>
                )}
              </div>

              {error && (
                <div className="mt-3 rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-red-600 dark:text-red-400 text-sm">
                  {error}
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="space-y-6">
          <div className="card">
            <div className="card-header">
              <div className="flex items-center gap-3">
                <div className="rounded-lg bg-blue-100 p-2 dark:bg-blue-900/30">
                  <svg className="h-5 w-5 text-blue-600 dark:text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                  </svg>
                </div>
                <h3 className="card-title">Detection Status</h3>
              </div>
            </div>
            <div className="card-body space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm text-[var(--text-secondary)]">Status</span>
                <span className="status-badge neutral">{status}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-[var(--text-secondary)]">FPS</span>
                <span className="text-sm font-medium text-[var(--text-primary)]">{fps}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-[var(--text-secondary)]">Detections</span>
                <span className="text-sm font-medium text-[var(--text-primary)]">{detectionsCount}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-[var(--text-secondary)]">Model</span>
                <span className="text-sm font-medium text-[var(--text-primary)]">{modelLabel || 'OpenCV Fallback'}</span>
              </div>
            </div>
          </div>

          <div className="card">
            <div className="card-header">
              <div className="flex items-center gap-3">
                <div className="rounded-lg bg-purple-100 p-2 dark:bg-purple-900/30">
                  <svg className="h-5 w-5 text-purple-600 dark:text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31-2.37-2.37a1.724 1.724 0 00-2.572 1.065c-.996.608 2.296.07 2.572-1.065z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                  </svg>
                </div>
                <h3 className="card-title">Current Settings</h3>
              </div>
            </div>
            <div className="card-body space-y-4">
              <div>
                <label className="text-sm text-[var(--text-secondary)]">Detection interval</label>
                <input
                  type="range"
                  min="300"
                  max="1500"
                  step="50"
                  value={minFrameIntervalMs}
                  onChange={(e) => setMinFrameIntervalMs(parseInt(e.target.value, 10))}
                  className="mt-2 w-full h-2 bg-[var(--bg-secondary)] rounded-lg appearance-none cursor-pointer"
                />
                <div className="mt-1 text-xs text-[var(--text-muted)]">{minFrameIntervalMs}ms (slower = cheaper)</div>
              </div>
              <div className="text-xs text-[var(--text-muted)]">
                Uses your backend <span className="font-semibold">POST /api/predict</span> for each sampled frame.
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
