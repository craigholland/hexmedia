# HexMedia Frontend (Vite + React + TS)

A minimal frontend scaffold wired to the HexMedia API.

## Quickstart

```bash
# 1) cd into the project
cd hexmedia-fe

# 2) set API base (or keep default http://localhost:8000/api)
echo "VITE_API_BASE_URL=http://localhost:8000/api" > .env

# 3) install deps
npm i

# 4) run dev server
npm run dev
```

Open http://localhost:5173

## Features

- Buckets list (order + counts)
- Bucket grid of media cards
- Tools page: Ingest plan/run, Thumbnail plan/run
- Axios client with `VITE_API_BASE_URL`
- React Query for data fetching / caching
- Tailwind CSS styling

## Expected API routes

- `GET /api/media-items/buckets/order` → `string[]`
- `GET /api/media-items/buckets/count` → `Record<string, number>`
- `GET /api/media-items/by-bucket/{bucket}?include=assets,persons,ratings` → `MediaItemCardRead[]`
- `POST /api/ingest/plan?limit=20` → `IngestPlanItem[]`
- `POST /api/ingest/run?limit=20` body `{ files: string[] }` → `IngestRunResponse`
- `GET /api/ingest/thumb_plan?limit=20&missing=either|both` → `ThumbPlanItem[]`
- `POST /api/ingest/thumb` body with options → `ThumbResponse`

> If you host media files behind a public URL, the backend can populate `thumb_url` / `contact_url` on each card. Otherwise the FE will fall back to embedded `assets[].url` if present.
