'use client'

import React, { useEffect, useRef, useState } from 'react'
import { api } from '@/lib/api'

export type Suggestion = {
  label?: string
  lat?: number
  lon?: number
  placeId?: string
  eLoc?: string
  address?: string
  raw?: any
}

export default function MapplsAutosuggest({ onSelect }: { onSelect?: (s: Suggestion) => void }) {
  const [q, setQ] = useState('')
  const [items, setItems] = useState<Suggestion[]>([])
  const [loading, setLoading] = useState(false)
  const [open, setOpen] = useState(false)
  const timer = useRef<number | null>(null)

  useEffect(() => {
    if (!q || q.trim().length < 2) {
      setItems([])
      setOpen(false)
      return
    }

    setLoading(true)
    if (timer.current) window.clearTimeout(timer.current)
    timer.current = window.setTimeout(async () => {
      try {
        const res = await api.mapplsAutosuggest(q, 6)
        const raw = res?.items
        const suggestions: Suggestion[] = []

        function pickLatLon(obj: any): { lat?: number; lon?: number } {
          if (!obj) return {}
          if (obj.latitude || obj.longitude) return { lat: Number(obj.latitude), lon: Number(obj.longitude) }
          if (obj.lat || obj.lng) return { lat: Number(obj.lat), lon: Number(obj.lng) }
          if (obj.location && Array.isArray(obj.location.coordinates)) {
            const [lon, lat] = obj.location.coordinates
            return { lat: Number(lat), lon: Number(lon) }
          }
          if (obj.geometry && Array.isArray(obj.geometry.coordinates)) {
            const [lon, lat] = obj.geometry.coordinates
            return { lat: Number(lat), lon: Number(lon) }
          }
          return {}
        }

        function pickLabel(obj: any): string {
          return (
            obj?.placeName || obj?.name || obj?.displayName || obj?.formatted_address || obj?.address || obj?.label || obj?.vicinity || ''
          )
        }

        let candidates: any[] = []
        if (Array.isArray(raw)) candidates = raw
        else if (raw?.copResults) candidates = Array.isArray(raw.copResults) ? raw.copResults : [raw.copResults]
        else if (raw?.results) candidates = raw.results
        else if (raw?.items) candidates = raw.items
        else if (raw?.candidates) candidates = raw.candidates
        else if (raw?.suggestions) candidates = raw.suggestions
        else if (raw) candidates = [raw]

        candidates
          .filter(Boolean)
          .slice(0, 8)
          .forEach((it: any) => {
            const { lat, lon } = pickLatLon(it)
            const placeId = it?.placeId || it?.place_id || it?.id || it?.pid || undefined
            const eLoc = it?.eloc || it?.eLoc || it?.e_loc || undefined
            const address = it?.formatted_address || it?.address || it?.vicinity || undefined
            const label = pickLabel(it) || address || String(it)
            if (!label) return
            suggestions.push({ label, lat: lat ?? undefined, lon: lon ?? undefined, placeId, eLoc, address, raw: it })
          })

        setItems(suggestions)
        setOpen(suggestions.length > 0)
      } catch (e) {
        setItems([])
        setOpen(false)
      } finally {
        setLoading(false)
      }
    }, 250)

    return () => {
      if (timer.current) window.clearTimeout(timer.current)
    }
  }, [q])

  function handleSelect(s: Suggestion) {
    setQ(s.label || '')
    setOpen(false)
    if (onSelect) onSelect(s)
  }

  return (
    <div className="relative">
      <input
        value={q}
        onChange={(e) => setQ(e.target.value)}
        onFocus={() => { if (items.length) setOpen(true) }}
        placeholder="Search places"
        className="w-full rounded border px-3 py-2 text-sm"
        aria-autocomplete="list"
      />

      {open && (
        <ul className="absolute z-40 mt-1 max-h-56 w-full overflow-auto rounded border bg-card p-1 text-sm">
          {loading && <li className="px-2 py-1 text-muted-foreground">Searching…</li>}
          {!loading && items.length === 0 && <li className="px-2 py-1 text-muted-foreground">No results</li>}
          {items.map((it, idx) => (
            <li
              key={idx}
              className="cursor-pointer px-2 py-1 hover:bg-accent/20"
              onMouseDown={(e) => e.preventDefault()}
              onClick={() => handleSelect(it)}
            >
              <div className="truncate">{it.label}</div>
              {(it.lat || it.lon) && <div className="text-xs text-muted-foreground">{it.lat?.toFixed(5)},{it.lon?.toFixed(5)}</div>}
              {it.address && <div className="text-xs text-muted-foreground">{it.address}</div>}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
