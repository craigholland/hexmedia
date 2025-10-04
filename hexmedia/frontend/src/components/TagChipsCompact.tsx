import { useState, useMemo } from 'react'
import type { TagRead } from '@/types'

type Props = {
  tags?: TagRead[] | null
  maxVisible?: number
  onClickTag?: (tag: TagRead) => void
}

export default function TagChipsCompact({ tags, maxVisible = 6, onClickTag }: Props) {
  const list = tags ?? []
  const [expanded, setExpanded] = useState(false)
  const visible = useMemo(() => (expanded ? list : list.slice(0, maxVisible)), [expanded, list, maxVisible])
  const hidden = Math.max(0, list.length - visible.length)
  if (!list.length) return null

  return (
    <div className="flex flex-wrap items-center gap-1.5">
      {visible.map(t => (
        <button
          key={t.id}
          type="button"
          onClick={onClickTag ? () => onClickTag(t) : undefined}
          className="inline-flex items-center px-2 py-0.5 rounded-full border text-[11px] leading-5
                     border-neutral-700 text-neutral-200 hover:bg-neutral-800 focus:outline-none focus:ring-1 focus:ring-neutral-500"
          title={t.slug || t.name}
        >
          {t.name}
        </button>
      ))}
      {!expanded && hidden > 0 && (
        <button
          type="button"
          aria-label={`Show ${hidden} more tags`}
          onClick={() => setExpanded(true)}
          className="text-[11px] px-2 py-0.5 rounded-full border border-dashed border-neutral-700 text-neutral-300 hover:bg-neutral-800 focus:outline-none focus:ring-1 focus:ring-neutral-500"
        >
          + {hidden} more…
        </button>
      )}
      {expanded && list.length > maxVisible && (
        <button
          type="button"
          aria-label="Collapse extra tags"
          onClick={() => setExpanded(false)}
          className="text-[11px] px-2 py-0.5 rounded-full border border-dashed border-neutral-700 text-neutral-400 hover:bg-neutral-800 focus:outline-none focus:ring-1 focus:ring-neutral-500"
        >
          collapse
        </button>
      )}
    </div>
  )
}
