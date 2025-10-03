// src/components/BucketToolbar.tsx
import type { SortBy } from '@/routes/BucketView'

type Props = {
  query: string
  setQuery: (v: string) => void
  sortBy: SortBy
  setSortBy: (v: SortBy) => void
  minRating: number
  setMinRating: (v: number) => void
  onlyThumbs: boolean
  setOnlyThumbs: (v: boolean) => void
  total: number
  visible: number
  onClear: () => void
}

export default function BucketToolbar({
  query, setQuery,
  sortBy, setSortBy,
  minRating, setMinRating,
  onlyThumbs, setOnlyThumbs,
  total, visible,
  onClear
}: Props) {
  return (
    <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
      <div className="flex flex-col sm:flex-row gap-3">
        {/* search */}
        <div>
          <label className="block text-xs text-neutral-500 mb-1">Search</label>
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="title, identity, tag, person…"
            className="rounded-md border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-900 px-3 py-1.5 w-64"
          />
        </div>

        {/* sort */}
        <div>
          <label className="block text-xs text-neutral-500 mb-1">Sort by</label>
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as SortBy)}
            className="rounded-md border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-900 px-3 py-1.5"
          >
            <option value="rating">Rating (desc)</option>
            <option value="title">Title (A→Z)</option>
            <option value="duration">Duration (desc)</option>
            <option value="resolution">Resolution (desc)</option>
          </select>
        </div>

        {/* min rating */}
        <div>
          <label className="block text-xs text-neutral-500 mb-1">Min rating</label>
          <select
            value={minRating}
            onChange={(e) => setMinRating(parseInt(e.target.value || '0', 10))}
            className="rounded-md border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-900 px-3 py-1.5"
          >
            <option value={0}>All</option>
            <option value={1}>≥ 1</option>
            <option value={2}>≥ 2</option>
            <option value={3}>≥ 3</option>
            <option value={4}>≥ 4</option>
            <option value={5}>5 only</option>
          </select>
        </div>

        {/* only thumbs */}
        <label className="flex items-center gap-2 mt-6 sm:mt-0">
          <input
            type="checkbox"
            checked={onlyThumbs}
            onChange={(e) => setOnlyThumbs(e.target.checked)}
          />
          <span className="text-sm">Only items with thumbs</span>
        </label>
      </div>

      <div className="flex items-center justify-between gap-3">
        <div className="text-sm text-neutral-500">
          Showing <span className="font-medium text-neutral-900 dark:text-neutral-100">{visible}</span> of {total}
        </div>
        <button
          className="px-3 py-2 rounded-md border border-neutral-300 dark:border-neutral-700"
          onClick={onClear}
        >
          Reset
        </button>
      </div>
    </div>
  )
}
