import { Link } from 'react-router-dom'
import { useBucketOrder, useBucketCounts } from '@/lib/hooks'

export default function Buckets() {
  const { data: order, isLoading: loadingOrder } = useBucketOrder()
  const { data: counts, isLoading: loadingCounts } = useBucketCounts()

  if (loadingOrder || loadingCounts) return <div className="text-neutral-400">Loading…</div>
  if (!order) return <div>No buckets.</div>

  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-6 gap-3">
      {order.map(b => {
        const n = counts?.[b] ?? 0
        return (
          <Link key={b} to={`/bucket/${b}`} className="rounded-xl border border-neutral-800 bg-neutral-900 hover:bg-neutral-800 transition p-4 flex flex-col items-center">
            <div className="text-lg font-mono">{b}</div>
            <div className="text-xs text-neutral-400">{n} items</div>
          </Link>
        )
      })}
    </div>
  )
}
