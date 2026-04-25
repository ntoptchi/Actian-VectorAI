# RouteWise Frontend

Next.js 15 + React 19 + TypeScript frontend for RouteWise.

## Stack

- **Framework:** Next.js 15 (App Router, Turbopack dev)
- **UI:** React 19, Tailwind CSS, shadcn/ui components
- **Maps:** Leaflet + protomaps-leaflet (local PMTiles, no external tile server)
- **State:** React hooks + URL params

## Development

```bash
npm install
npm run dev        # starts on http://localhost:3000 (Turbopack)
```

The frontend expects the FastAPI backend running on `http://localhost:8080`.

## Key pages

| Route | File | Description |
|---|---|---|
| `/` | `src/app/page.tsx` | Origin/destination entry form |
| `/trip` | `src/app/trip/page.tsx` | Trip briefing view (map + sidebar + cards) |
| `/trip/briefing` | `src/app/trip/briefing/` | Briefing sub-route |

## Key components

| Component | Description |
|---|---|
| `RouteMap` | Leaflet map with route polylines, risk coloring, hotspot pins, news markers |
| `BriefingCard` | Slide-out card for hotspot details or news articles |
| `AlternatesPanel` | Route alternates with crash counts and duration |
| `SidebarSections` | Right sidebar: conditions, hotspots, lessons, media coverage |
| `PlanCard` | Fatigue/rest-stop plan display |
| `SiteHeader` | Top navigation bar |

## API integration

All backend calls go through `src/lib/api.ts` and `src/lib/client-api.ts`,
hitting the FastAPI backend's `/trip/brief` endpoint. Types are defined in
`src/lib/types.ts`.
