'use client'

import dynamic from 'next/dynamic'
import type { EmergencyRoute } from '@/lib/types'
import { Skeleton } from '@/components/ui/skeleton'
import { MAP_DEFAULT_CENTER, MAP_ROUTE_ZOOM } from '@/lib/constants'
import { isMapplsConfigured } from '@/lib/mappls-loader'

const MapplsMap = dynamic(() => import('./mappls-map'), {
  ssr: false,
  loading: () => <Skeleton className="h-full w-full rounded-xl" />,
})

const LeafletMap = dynamic(() => import('./leaflet-map'), {
  ssr: false,
  loading: () => <Skeleton className="h-full w-full rounded-xl" />,
})

export function RouteMap({ route }: { route: EmergencyRoute }) {
  const mapCenter = route.path[Math.floor(route.path.length / 2)] ?? MAP_DEFAULT_CENTER
  const MapComponent = isMapplsConfigured() ? MapplsMap : LeafletMap

  return (
    <div className="relative h-[420px] overflow-hidden rounded-xl border border-border/60">
      <MapComponent
        center={mapCenter}
        zoom={MAP_ROUTE_ZOOM}
        route={route}
        layers={{ corridors: false, hotspots: false, events: false, heatmap: false, routes: true }}
      />
    </div>
  )
}
