"use client"

import { useEffect } from 'react'

export default function GlobalUnhandledRejection() {
  useEffect(() => {
    function handler(ev: PromiseRejectionEvent) {
      try {
        const reason: any = ev.reason
        const name = reason?.name ?? (reason && reason.constructor && reason.constructor.name) ?? ''
        const message = typeof reason === 'string' ? reason : reason?.message ?? ''
        // Suppress AbortError rejections (common for fetch timeouts/aborts)
        if (name === 'AbortError' || String(message).toLowerCase().includes('signal is aborted')) {
          ev.preventDefault()
          return
        }
      } catch {
        // ignore
      }
    }

    window.addEventListener('unhandledrejection', handler)
    return () => window.removeEventListener('unhandledrejection', handler)
  }, [])

  return null
}
