'use client'

import dynamic from 'next/dynamic'
import type { EmergencyRoute } from '@/lib/types'
import { Skeleton } from '@/components/ui/skeleton'
import { MAP_DEFAULT_CENTER, MAP_ROUTE_ZOOM } from '@/lib/constants'

const LeafletMap = dynamic(() => import('./leaflet-map'), {
  ssr: false,
  loading: () => <Skeleton className="h-full w-full rounded-xl" />,
})

export function RouteMap({ route }: { route: EmergencyRoute }) {
  return (
    <div className="relative h-[420px] overflow-hidden rounded-xl border border-border/60">
      <LeafletMap
        center={route.path[Math.floor(route.path.length / 2)] ?? MAP_DEFAULT_CENTER}
        zoom={MAP_ROUTE_ZOOM}
        route={route}
        layers={{ corridors: false, hotspots: false, events: false, heatmap: false, routes: true }}
      />
    </div>
  )
}
