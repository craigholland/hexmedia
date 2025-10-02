import type { MediaItemCardRead } from '@/types'

function fmtDuration(sec?: number | null) {
  if (!sec || sec <= 0) return null
  const h = Math.floor(sec / 3600)
  const m = Math.floor((sec % 3600) / 60)
  const s = Math.floor(sec % 60)
  return h
    ? `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
    : `${m}:${s.toString().padStart(2, '0')}`
}

const FALLBACK_DATA_URI =
  'data:image/svg+xml;utf8,' +
  encodeURIComponent(
    `<svg xmlns='http://www.w3.org/2000/svg' width='480' height='270'><rect width='100%' height='100%' fill='#ddd'/><text x='50%' y='50%' dominant-baseline='middle' text-anchor='middle' font-family='sans-serif' font-size='18' fill='#666'>No thumbnail</text></svg>`
  )

export default function MediaCard({ item }: { item: MediaItemCardRead }) {
  const dur = fmtDuration(item.duration_sec)
  const thumb =
    item.thumb_url ??
    item.assets?.find(a => a.kind === 'thumb')?.url ??
    FALLBACK_DATA_URI

  return (
    <article className="rounded-xl overflow-hidden border border-neutral-200 bg-white text-neutral-900 dark:border-neutral-800 dark:bg-neutral-900 dark:text-neutral-100">
      <div className="relative aspect-video bg-neutral-100 dark:bg-neutral-800">
        <img
          src={thumb}
          loading="lazy"
          alt={item.title ?? item.identity.identity_name}
          onError={e => {
            const target = e.currentTarget as HTMLImageElement
            if (target.src !== FALLBACK_DATA_URI) target.src = FALLBACK_DATA_URI
          }}
          className="w-full h-full object-cover block"
        />
        {dur && (
          <span className="absolute right-2 bottom-2 bg-black/70 text-white text-xs px-2 py-0.5 rounded">
            {dur}
          </span>
        )}
      </div>

      <div className="p-3 space-y-2">
        <div className="font-semibold text-sm">
          {item.title ?? item.identity.identity_name}
          {item.release_year ? ` (${item.release_year})` : ''}
        </div>

        <div className="text-xs text-neutral-500 font-mono">
          {item.identity.media_folder}/{item.identity.identity_name}.{item.identity.video_ext}
        </div>

        <div className="text-xs text-neutral-600 dark:text-neutral-400">
          {item.width && item.height ? `${item.width}×${item.height}` : ''}
          {item.duration_sec ? (item.width && item.height ? ' • ' : '') + `${Math.round((item.duration_sec || 0) / 60)}m` : ''}
          {typeof item.rating === 'number' ? ' • ★ ' + item.rating : ''}
        </div>

        {!!item.persons?.length && (
          <div className="flex flex-wrap gap-1.5">
            {item.persons.slice(0, 4).map(p => (
              <span
                key={p.id}
                title={p.normalized_name ?? p.display_name}
                className="border border-neutral-200 dark:border-neutral-700 rounded-full px-2 py-0.5 text-xs text-neutral-700 dark:text-neutral-200 bg-neutral-50 dark:bg-neutral-800"
              >
                {p.display_name}
              </span>
            ))}
            {item.persons.length > 4 && (
              <span className="text-xs text-neutral-500">+{item.persons.length - 4}</span>
            )}
          </div>
        )}

        {!!item.tags?.length && (
          <div className="flex flex-wrap gap-1.5">
            {item.tags.slice(0, 6).map(t => (
              <span
                key={t.id}
                title={t.slug ?? t.name}
                className="bg-indigo-50 text-indigo-800 dark:bg-indigo-900/30 dark:text-indigo-200 rounded px-1.5 py-0.5 text-[11px]"
              >
                {t.name}
              </span>
            ))}
            {item.tags.length > 6 && (
              <span className="text-xs text-neutral-500">+{item.tags.length - 6}</span>
            )}
          </div>
        )}
      </div>
    </article>
  )
}
