import { Link } from 'react-router-dom'
import { useBucketOrder, useBucketCounts } from '@/lib/hooks'

export default function BucketsIndex() {
  const orderQ = useBucketOrder()
  const countsQ = useBucketCounts()

  if (orderQ.isLoading || countsQ.isLoading) {
    return <div className="text-neutral-500">Loading buckets…</div>
  }
  if (orderQ.error || countsQ.error) {
    return <div className="text-red-600">Failed to load buckets.</div>
  }

  const order = orderQ.data ?? []
  const counts = countsQ.data ?? {}

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 lg:grid-cols-7 gap-3">
      {order.map(b => {
        const c = counts[b] ?? 0
        return (
          <Link
            to={`/bucket/${b}`}
            key={b}
            className="rounded-xl border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900 p-4 hover:shadow"
          >
            <div className="text-sm text-neutral-500">Bucket</div>
            <div className="text-2xl font-semibold tracking-tight">{b}</div>
            <div className="text-xs text-neutral-500 mt-1">{c} item{c === 1 ? '' : 's'}</div>
          </Link>
        )
      })}
      {!order.length && <div className="text-neutral-500">No buckets yet.</div>}
    </div>
  )
}
