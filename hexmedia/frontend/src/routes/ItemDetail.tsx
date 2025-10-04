import { Link, useLocation, useNavigate, useParams } from 'react-router-dom'
import { useEffect, useMemo, useState } from 'react'
import { useBucketCards, useRateItem } from '@/lib/hooks'
import type { MediaItemCardRead } from '@/types'
import AssetsPanel from '@/components/AssetsPanel'
import StarRating from '@/components/StarRating'
import TaggingPanel from '@/components/TaggingPanel'

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

  // Always include tags so UI reflects updates
  const include = 'assets,persons,tags,ratings'
  const cardsQ = useBucketCards(bucket, include)

  // Prefer fresh query data; fall back to state only until data arrives
  const itemFromData = useMemo(
    () => cardsQ.data?.find((x) => String(x.id) === String(id)),
    [cardsQ.data, id]
  )
  const item = itemFromData ?? state?.item

  const rateM = useRateItem(bucket)
  const [score, setScore] = useState<number>(item?.rating ?? 0)

  // keep local score synced when item refetches
  useEffect(() => {
    if (typeof item?.rating === 'number') setScore(item.rating)
  }, [item?.rating])

  const handleRate = (n: number) => {
    if (!item) return
    const prev = score
    setScore(n) // optimistic
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

  const getAssetUrl = (kinds: string[]) => item.assets?.find((a) => kinds.includes(a.kind))?.url ?? null
  const videoUrl = getAssetUrl(['proxy', 'video'])
  const contactUrl = getAssetUrl(['contact', 'contact_sheet', 'contactsheet', 'collage'])
  const thumbUrl = item.thumb_url ?? getAssetUrl(['thumb'])

  // compact technical line
  const techParts: string[] = []
  if (duration) techParts.push(`Duration: ${duration}`)
  if (item.width && item.height) techParts.push(`Resolution: ${item.width}×${item.height}`)
  if (typeof item.fps === 'number') techParts.push(`FPS: ${item.fps}`)
  if (typeof item.bitrate === 'number') techParts.push(`Bitrate: ${item.bitrate} kbps`)
  const techLine = techParts.join(' • ')

  return (
    <div className="space-y-6">
      {/* Title + path + navigation */}
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

      {/* Two-column layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* LEFT side: header (tech + rating) above collage, then collage, then assets */}
        <div className="lg:col-span-8 space-y-4">
          {/* Row above collage: technical (left) and rating (right) */}
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            {/* Technical line */}
            <div className="rounded-lg border border-neutral-200 dark:border-neutral-800 px-3 py-2 text-sm text-neutral-800 dark:text-neutral-200 bg-white/50 dark:bg-neutral-900/50">
              {techLine || <span className="text-neutral-500">No technical data</span>}
            </div>
            {/* Rating */}
            <div className="rounded-lg border border-neutral-200 dark:border-neutral-800 px-3 py-2">
              <div className="text-xs text-neutral-500 mb-1">Your Rating</div>
              <div className="flex items-center gap-3">
                <StarRating value={score} onChange={handleRate} disabled={rateM.isPending} />
                {rateM.isPending && <span className="text-xs text-neutral-500">Saving…</span>}
                {rateM.isError && <span className="text-xs text-red-600">Failed to save</span>}
              </div>
            </div>
          </div>

          {/* Collage / video */}
          <div>
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

          {/* Assets section (below collage) */}
          {item.assets?.length ? (
            <div className="rounded-xl border border-neutral-200 dark:border-neutral-800 p-4">
              <div className="text-sm text-neutral-500 mb-2">Assets</div>
              <AssetsPanel assets={item.assets} />
            </div>
          ) : null}
        </div>

        {/* RIGHT side: Tags occupy the entire sidebar */}
        <aside className="lg:col-span-4 space-y-4">
          <div className="rounded-xl border border-neutral-200 dark:border-neutral-800 p-4">
            <div className="text-base font-semibold mb-2">Tags</div>
            <TaggingPanel item={item} bucket={String(bucket)} />
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
        </aside>
      </div>
    </div>
  )
}
