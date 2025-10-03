import {useMemo, useState} from 'react'
import { useParams } from 'react-router-dom'
import { useBucketCards } from '@/lib/hooks'
import type {MediaItemCardRead} from '@/types'
import MediaCard from '@/components/MediaCard'
import BucketToolbar from '@/components/BucketToolbar'

export type SortBy = 'title' | 'rating' | 'duration' | 'resolution'

function norm(s?: string | null) {
  return (s ?? '').toLowerCase()
}
function hasThumb(item: MediaItemCardRead) {
  return Boolean(
    item.thumb_url ||
    item.assets?.some(a => a.kind === 'thumb' && a.url)
  )
}
export default function BucketView() {
  const { bucket = '' } = useParams()
  const include = 'assets,persons,ratings'
  const { data, isLoading, error } = useBucketCards(bucket, include)

  // toolbar state
  const [query, setQuery] = useState('')
  const [sortBy, setSortBy] = useState<SortBy>('rating')
  const [minRating, setMinRating] = useState(0)
  const [onlyThumbs, setOnlyThumbs] = useState(false)

  const items = data ?? []

  const filtered = useMemo(() => {
    let list = items

    // filter: query
    const q = norm(query)
    if (q) {
      list = list.filter(it => {
        const title = norm(it.title) || norm(it.identity.identity_name)
        const idName = norm(it.identity.identity_name)
        const tagBlob = norm(it.tags?.map(t => `${t.name} ${t.slug ?? ''}`).join(' '))
        const peopleBlob = norm(it.persons?.map(p => `${p.display_name ?? ''} ${p.normalized_name ?? ''}`).join(' '))
        return (
          title.includes(q) ||
          idName.includes(q) ||
          tagBlob.includes(q) ||
          peopleBlob.includes(q)
        )
      })
    }

    // filter: min rating
    if (minRating > 0) {
      list = list.filter(it => (it.rating ?? 0) >= minRating)
    }

    // filter: has thumb
    if (onlyThumbs) {
      list = list.filter(it => hasThumb(it))
    }

    // sort
    const collator = new Intl.Collator(undefined, { sensitivity: 'base', numeric: true })
    const scoreRes = (w?: number | null, h?: number | null) => (w ?? 0) * (h ?? 0)

    const sorted = [...list].sort((a, b) => {
      switch (sortBy) {
        case 'title': {
          const aa = a.title ?? a.identity.identity_name ?? ''
          const bb = b.title ?? b.identity.identity_name ?? ''
          return collator.compare(aa, bb) // asc
        }
        case 'duration': {
          const aa = a.duration_sec ?? 0
          const bb = b.duration_sec ?? 0
          return bb - aa // desc
        }
        case 'resolution': {
          const aa = scoreRes(a.width, a.height)
          const bb = scoreRes(b.width, b.height)
          return bb - aa // desc
        }
        case 'rating':
        default: {
          const aa = a.rating ?? 0
          const bb = b.rating ?? 0
          if (bb !== aa) return bb - aa // rating desc
          // tie-break by title asc
          const ta = a.title ?? a.identity.identity_name ?? ''
          const tb = b.title ?? b.identity.identity_name ?? ''
          return collator.compare(ta, tb)
        }
      }
    })

    return sorted
  }, [items, query, sortBy, minRating, onlyThumbs])

  const onClear = () => {
    setQuery('')
    setSortBy('rating')
    setMinRating(0)
    setOnlyThumbs(false)
  }

  if (isLoading) return <div className="text-neutral-400">Loading…</div>
  if (error)     return <div className="text-red-600">Failed to load bucket.</div>
  if (!items.length) return <div>No items in bucket {bucket}.</div>

  return (
    <div>
      <BucketToolbar
        query={query} setQuery={setQuery}
        sortBy={sortBy} setSortBy={setSortBy}
        minRating={minRating} setMinRating={setMinRating}
        onlyThumbs={onlyThumbs} setOnlyThumbs={setOnlyThumbs}
        total={items.length} visible={filtered.length}
        onClear={onClear}
      />

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {filtered.map(card => (
          <MediaCard key={card.id} item={card} />
        ))}
      </div>
    </div>
  )
}