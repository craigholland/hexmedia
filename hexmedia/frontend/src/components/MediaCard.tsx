import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import StarRating from '@/components/StarRating'
import { useRateItem } from '@/lib/hooks'
import type { MediaItemCardRead } from '@/types'
import TagChipsCompact from "@/components/TagChipsCompact";


type Props = {
  item: MediaItemCardRead
  // Optional: pass bucket from parent. If omitted, we'll try to read it from the URL (/bucket/:bucket)
  bucket?: string
}

function fmtDuration(sec?: number | null) {
  if (!sec || sec <= 0) return null
  const h = Math.floor(sec / 3600)
  const m = Math.floor((sec % 3600) / 60)
  const s = sec % 60
  return h ? `${h}:${m.toString().padStart(2,'0')}:${s.toString().padStart(2,'0')}` : `${m}:${s.toString().padStart(2,'0')}`
}

export default function MediaCard({ item, bucket: bucketProp }: Props) {
  // If parent didn’t pass bucket, try to infer from the URL (/bucket/:bucket)
  const params = useParams()
  const bucket = bucketProp ?? params.bucket ?? item.identity.media_folder

  const thumb = useMemo(
    () => item.thumb_url || item.assets?.find(a => a.kind === 'thumb')?.url || null,
    [item.thumb_url, item.assets]
  )
  const title = item.title || item.identity.identity_name
  const duration = fmtDuration(item.duration_sec)

  // Optimistic local rating state
  const [score, setScore] = useState<number>(item.rating ?? 0)
  useEffect(() => {
    if (typeof item.rating === 'number') setScore(item.rating)
  }, [item.rating])

  const rateM = useRateItem(bucket)

  const onRate = (n: number) => {
    const prev = score;
    const clamped = Math.max(0, Math.min(5, n));
    if (clamped !== (item.rating ?? 0)) {
        setScore(n) // optimistic
        rateM.mutate(
            {id: String(item.id), score: n},
            {onError: () => setScore(prev)}
        )
    }
  }

  return (
    <article className="rounded-xl overflow-hidden border border-neutral-800 bg-neutral-900">

      <Link to={`/bucket/${bucket}/item/${item.id}`} state={{ item }}>
        <div className="aspect-video bg-neutral-800">
          {thumb ? (
            <img src={thumb} className="w-full h-full object-cover" />
          ) : (
            <div className="w-full h-full flex items-center justify-center text-neutral-500 text-sm">
              no thumb
            </div>
          )}
        </div>
      </Link>

      <div className="p-3 space-y-2">
        {/* Top row: title left, stars right (upper-right of the technical/details area) */}
        <div className="flex items-start justify-between gap-3">
          <div className="text-sm line-clamp-1">{title}</div>
          <StarRating
            value={score}
            onChange={onRate}
            disabled={rateM.isPending}
            size={18}
          />
        </div>
        <TagChipsCompact tags={item.tags} maxVisible={6} />
        {/* Path */}
        <div className="text-xs text-neutral-500 font-mono">
          {item.identity.media_folder}/{item.identity.identity_name}.{item.identity.video_ext}
        </div>

        {/* Tiny technical line */}
        <div className="text-xs text-neutral-400">
          {duration ? `${duration}` : ''}
          {item.width && item.height ? ` • ${item.width}×${item.height}` : ''}
        </div>

      </div>
    </article>
  )
}
