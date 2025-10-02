import { useLocation, useNavigate, useParams, Link } from 'react-router-dom'
import { useMemo, useState } from 'react'
import { useBucketCards, useRateItem } from '@/lib/hooks'
import type { MediaItemCardRead } from '@/types'
import AssetsPanel from '@/components/AssetsPanel'
import StarRating from '@/components/StarRating'


function fmtDuration(sec?: number | null) {
  if (!sec || sec <= 0) return null
  const h = Math.floor(sec / 3600)
  const m = Math.floor((sec % 3600) / 60)
  const s = sec % 60
  return h
    ? `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
    : `${m}:${s.toString().padStart(2, '0')}`
}

export default function ItemDetail() {
  const nav = useNavigate()
  const { bucket = '', id = '' } = useParams()
  const location = useLocation()
  const state = location.state as { item?: MediaItemCardRead } | undefined

  // If navigated from the grid we already have the item in state
  // Otherwise, fetch the bucket and find it
  const cardsQ = useBucketCards(bucket, 'assets,persons,ratings')
  const item = state?.item ?? cardsQ.data?.find(x => String(x.id) === String(id))
  const rateM = useRateItem(bucket)
     const [score, setScore] = useState<number>(item?.rating ?? 0)
    // refresh local score if item changes (e.g., when fetched)
  useMemo(() => { if (typeof item?.rating === 'number') setScore(item.rating) }, [item?.rating])
    const handleRate = (n: number) => {
    const prev = score
    setScore(n) // optimistic
    if (!item) return
    rateM.mutate(
      { id: String(item.id), score: n },
      { onError: () => setScore(prev) }
    )
  }
  // Build prev/next within this bucket (based on returned order)
  const { prev, next } = useMemo(() => {
    if (!cardsQ.data || !item) return { prev: undefined, next: undefined }
    const idx = cardsQ.data.findIndex((x) => String(x.id) === String(item.id))
    const prev = idx > 0 ? cardsQ.data[idx - 1] : undefined
    const next = idx >= 0 && idx < cardsQ.data.length - 1 ? cardsQ.data[idx + 1] : undefined
    return { prev, next }
  }, [cardsQ.data, item])

  if (!state?.item && cardsQ.isLoading) {
    return <div className="text-neutral-500">Loading item…</div>
  }

  if (!item) {
    return (
      <div className="space-y-4">
        <div className="text-lg font-semibold">Item not found</div>
        <p className="text-neutral-600">
          Couldn’t find this item in bucket <span className="font-mono">{bucket}</span>.
        </p>
        <Link
          to={`/bucket/${bucket}`}
          className="px-3 py-2 rounded-md bg-neutral-900 text-white dark:bg-white dark:text-neutral-900"
        >
          Back to bucket {bucket}
        </Link>
      </div>
    )
  }

  const title = item.title ?? item.identity.identity_name
  const duration = fmtDuration(item.duration_sec)
  const getAssetUrl = (kinds: string[]) =>
    item.assets?.find((a) => kinds.includes(a.kind))?.url ?? null

  const videoUrl   = getAssetUrl(['proxy', 'video'])
  const contactUrl = getAssetUrl(['contact', 'contact_sheet', 'contactsheet', 'collage'])
  const thumbUrl   = item.thumb_url ?? getAssetUrl(['thumb'])

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="text-2xl font-semibold">{title}</div>
          <div className="text-sm text-neutral-500 font-mono">
            {item.identity.media_folder}/{item.identity.identity_name}.{item.identity.video_ext}
          </div>
        </div>
        <div className="flex gap-2">
          {prev && (
            <Link
              to={`/bucket/${bucket}/item/${prev.id}`}
              state={{ item: prev }}
              className="px-3 py-2 rounded-md border border-neutral-300 dark:border-neutral-700"
            >
              ← Prev
            </Link>
          )}
          <Link
            to={`/bucket/${bucket}`}
            className="px-3 py-2 rounded-md bg-neutral-900 text-white dark:bg-white dark:text-neutral-900"
          >
            Back to {bucket}
          </Link>
          {next && (
            <Link
              to={`/bucket/${bucket}/item/${next.id}`}
              state={{ item: next }}
              className="px-3 py-2 rounded-md border border-neutral-300 dark:border-neutral-700"
            >
              Next →
            </Link>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <div className="lg:col-span-8 space-y-4">
          {videoUrl ? (
            <video
              src={videoUrl}
              controls
              className="w-full rounded-xl border border-neutral-200 dark:border-neutral-800"
              poster={contactUrl ?? thumbUrl ?? undefined}
            />
          ) : (
            <img
              src={contactUrl ?? thumbUrl ?? ''}
              alt={title}
              className="w-full rounded-xl border border-neutral-200 dark:border-neutral-800"
            />
          )}
        </div>

        <aside className="lg:col-span-4 space-y-4">
            {/*Technical */}
          <div className="rounded-xl border border-neutral-200 dark:border-neutral-800 p-4">
            <div className="text-sm text-neutral-500 mb-2">Technical</div>
            <div className="text-sm space-y-1">
              {duration && <div>Duration: {duration}</div>}
              {item.width && item.height && <div>Resolution: {item.width}×{item.height}</div>}
              {typeof item.fps === 'number' && <div>FPS: {item.fps}</div>}
              {typeof item.bitrate === 'number' && <div>Bitrate: {item.bitrate} kbps</div>}
              {item.assets?.length ? <AssetsPanel assets={item.assets} /> : null}
            </div>
          </div>
            {/* Your Rating */}
          <div className="rounded-xl border border-neutral-200 dark:border-neutral-800 p-4">
            <div className="text-sm text-neutral-500 mb-2">Your Rating</div>
            <div className="flex items-center gap-3">
              <StarRating value={score} onChange={handleRate} disabled={rateM.isPending} />
              {rateM.isPending && <span className="text-xs text-neutral-500">Saving…</span>}
              {rateM.isError && <span className="text-xs text-red-600">Failed to save</span>}
            </div>
          </div>
          {!!item.persons?.length && (
            <div className="rounded-xl border border-neutral-200 dark:border-neutral-800 p-4">
              <div className="text-sm text-neutral-500 mb-2">People</div>
              <div className="flex flex-wrap gap-2">
                {item.persons.map((p) => (
                  <span key={p.id} className="px-2 py-1 rounded-full border text-sm">
                    {p.display_name ?? p.normalized_name ?? 'Unknown'}
                  </span>
                ))}
              </div>
            </div>
          )}

          {!!item.tags?.length && (
            <div className="rounded-xl border border-neutral-200 dark:border-neutral-800 p-4">
              <div className="text-sm text-neutral-500 mb-2">Tags</div>
              <div className="flex flex-wrap gap-2">
                {item.tags.map((t) => (
                  <span key={t.id} className="px-2 py-1 rounded-md bg-indigo-50 text-indigo-950 text-sm">
                    {t.name}
                  </span>
                ))}
              </div>
            </div>
          )}
        </aside>
      </div>
    </div>
  )
}
