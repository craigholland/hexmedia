import { useMemo, useState } from 'react'
import { useParams } from 'react-router-dom'
import { useBucketCards } from '@/lib/hooks'
import MediaCard from '@/components/MediaCard'
import type { MediaItemCardRead } from '@/types'

type SortKey = 'title' | 'rating' | 'duration' | 'date'
type SortDir = 'asc' | 'desc'

function norm(s?: string | null) {
  return (s ?? '').toLowerCase()
}

function matchesQuery(item: MediaItemCardRead, q: string) {
  if (!q) return true
  const needle = q.trim().toLowerCase()
  const fields: string[] = []

  fields.push(item.title ?? '')
  fields.push(item.identity.identity_name)
  fields.push(item.identity.media_folder)
  item.persons?.forEach(p => fields.push(p.display_name ?? p.normalized_name ?? ''))
  item.tags?.forEach(t => fields.push(t.name ?? t.slug ?? ''))

  const hay = fields.join(' ').toLowerCase()
  return hay.includes(needle)
}

function compare(a: MediaItemCardRead, b: MediaItemCardRead, key: SortKey, dir: SortDir) {
  const mul = dir === 'asc' ? 1 : -1
  switch (key) {
    case 'title': {
      const ta = norm(a.title ?? a.identity.identity_name)
      const tb = norm(b.title ?? b.identity.identity_name)
      return ta < tb ? -1 * mul : ta > tb ? 1 * mul : 0
    }
    case 'rating': {
      const ra = typeof a.rating === 'number' ? a.rating : -1
      const rb = typeof b.rating === 'number' ? b.rating : -1
      return (ra - rb) * mul
    }
    case 'duration': {
      const da = a.duration_sec ?? -1
      const db = b.duration_sec ?? -1
      return (da - db) * mul
    }
    case 'date': {
      // If you later add created_at/last_updated, swap it in here.
      // For now, keep a stable order using id as a proxy.
      const ia = String(a.id)
      const ib = String(b.id)
      return ia < ib ? -1 * mul : ia > ib ? 1 * mul : 0
    }
  }
}

export default function BucketView() {
  const { bucket = '' } = useParams()
  const { data, isLoading, error } = useBucketCards(bucket, 'assets,persons,ratings')

  const [q, setQ] = useState('')
  const [sortKey, setSortKey] = useState<SortKey>('title')
  const [sortDir, setSortDir] = useState<SortDir>('asc')
  const [minRating, setMinRating] = useState(0)

  const filtered = useMemo(() => {
    const arr = (data ?? []).filter(i => matchesQuery(i, q))
                             .filter(i => (i.rating ?? 0) >= minRating)
    return arr.sort((a, b) => compare(a, b, sortKey, sortDir))
  }, [data, q, sortKey, sortDir, minRating])

  if (isLoading) return <div className="text-neutral-400">Loading…</div>
  if (error) return <div className="text-red-600">Failed to load items.</div>

  return (
    <div className="space-y-4">
      {/* Toolbar */}
      <div className="flex flex-wrap items-end gap-3">
        <div className="flex-1 min-w-[12rem]">
          <label className="block text-sm text-neutral-600 mb-1">Search</label>
          <input
            value={q}
            onChange={e => setQ(e.target.value)}
            placeholder="Title, person, tag…"
            className="w-full rounded-md border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-900 px-3 py-1.5"
          />
        </div>

        <div>
          <label className="block text-sm text-neutral-600 mb-1">Sort</label>
          <div className="flex items-center gap-2">
            <select
              value={sortKey}
              onChange={e => setSortKey(e.target.value as SortKey)}
              className="rounded-md border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-900 px-3 py-1.5"
            >
              <option value="title">Title</option>
              <option value="rating">Rating</option>
              <option value="duration">Duration</option>
              <option value="date">ID (stable)</option>
            </select>
            <button
              onClick={() => setSortDir(d => (d === 'asc' ? 'desc' : 'asc'))}
              className="px-3 py-1.5 rounded-md border border-neutral-300 dark:border-neutral-700"
              title={`Toggle sort (${sortDir})`}
            >
              {sortDir === 'asc' ? '↑' : '↓'}
            </button>
          </div>
        </div>

        <div className="w-48">
          <label className="block text-sm text-neutral-600 mb-1">Min rating</label>
          <input
            type="range"
            min={0}
            max={5}
            step={1}
            value={minRating}
            onChange={e => setMinRating(parseInt(e.target.value, 10))}
            className="w-full"
          />
          <div className="text-xs text-neutral-500 mt-1">{minRating}★ and up</div>
        </div>
      </div>

      {/* Stats line */}
      <div className="text-sm text-neutral-600 dark:text-neutral-400">
        Showing <span className="font-semibold">{filtered.length}</span> of {data?.length ?? 0} item(s) in bucket <span className="font-mono">{bucket}</span>
        {q ? <> • filtered by “{q}”</> : null}
        {minRating > 0 ? <> • min {minRating}★</> : null}
      </div>

      {/* Grid */}
      {filtered.length ? (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {filtered.map(item => (
            <MediaCard key={item.id} item={item} bucket={bucket} />
          ))}
        </div>
      ) : (
        <div className="text-neutral-500">No items match your filters.</div>
      )}
    </div>
  )
}
