export function getPreferredMimeType() {
  // Helps some mobile browsers decide format.
  if (typeof MediaRecorder === 'undefined') return null
  const candidates = [
    'video/webm;codecs=vp9',
    'video/webm;codecs=vp8',
    'video/webm',
  ]
  for (const c of candidates) {
    try {
      if (MediaRecorder.isTypeSupported && MediaRecorder.isTypeSupported(c)) return c
    } catch (_) {}
  }
  return null
}

export async function getUserMediaStream({
  facingMode = 'environment',
  width,
  height,
  // Optional additional constraints for mobile stability.
  // e.g. { ideal: 1280 } for iOS camera-like behavior.
  frameRate,
} = {}) {
  if (!navigator.mediaDevices?.getUserMedia) {
    throw new Error('getUserMedia is not supported in this browser.')
  }

  const videoConstraints = {
    facingMode,
  }

  if (width) videoConstraints.width = width
  if (height) videoConstraints.height = height

  if (frameRate) {
    // Prefer { ideal: fps } style; but accept a raw number too.
    videoConstraints.frameRate =
      typeof frameRate === 'number' ? { ideal: frameRate } : frameRate
  }

  const constraints = {
    video: videoConstraints,
    audio: false,
  }

  // Some browsers fail silently if called from non-secure origins.
  // This surfaces a friendlier error.
  if (typeof window !== 'undefined' && window.location) {
    const isSecure = window.location.protocol === 'https:' || window.location.hostname === 'localhost'
    if (!isSecure) {
      throw new Error('Camera access requires HTTPS (or localhost) in this browser.')
    }
  }

  return await navigator.mediaDevices.getUserMedia(constraints)
}


export function captureFrameToBlob({
  video,
  mimeType = 'image/jpeg',
  quality = 0.85,
} = {}) {
  const w = video.videoWidth
  const h = video.videoHeight
  if (!w || !h) return null

  const canvas = document.createElement('canvas')
  canvas.width = w
  canvas.height = h

  const ctx = canvas.getContext('2d')
  if (!ctx) return null
  ctx.drawImage(video, 0, 0, w, h)

  // toBlob is async; wrap in promise.
  return new Promise((resolve) => {
    canvas.toBlob(
      (blob) => {
        resolve(blob)
      },
      mimeType,
      quality
    )
  })
}

