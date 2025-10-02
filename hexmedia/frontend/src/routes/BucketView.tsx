import { Link, useParams } from 'react-router-dom'
import { useBucketCards } from '@/lib/hooks'
import MediaCard from '@/components/MediaCard'
import SkeletonCard from '@/components/SkeletonCard'

export default function BucketView() {
  const { bucket = '' } = useParams()
  const { data, isLoading, isError, error } = useBucketCards(bucket)

  return (
    <div className="p-4 space-y-4">
      <header className="flex items-center gap-3">
        <Link to="/" className="text-blue-500 hover:underline">← Buckets</Link>
        <h1 className="m-0 text-lg font-semibold">Bucket {bucket}</h1>
        {!isLoading && !!data?.length && (
          <span className="text-neutral-500">{data.length} items</span>
        )}
      </header>

      {isError && (
        <div className="border border-red-300/50 bg-red-50 text-red-800 rounded-md p-3">
          Failed to load items: {String((error as Error)?.message || error)}
        </div>
      )}

      {isLoading && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {Array.from({ length: 12 }).map((_, i) => <SkeletonCard key={i} />)}
        </div>
      )}

      {!isLoading && !!data?.length && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {data.map(item => <MediaCard key={item.id} item={item} />)}
        </div>
      )}

      {!isLoading && !data?.length && !isError && (
        <div className="text-neutral-500">This bucket is empty.</div>
      )}
    </div>
  )
}
