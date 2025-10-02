import { useParams } from 'react-router-dom'
import { useBucketCards } from '@/lib/hooks'
import MediaCard from '@/components/MediaCard'

export default function BucketView() {
  const { bucket = '' } = useParams()
  const { data, isLoading } = useBucketCards(bucket, 'assets,persons,ratings')

  if (isLoading) return <div className="text-neutral-400">Loading…</div>
  if (!data?.length) return <div>No items in bucket {bucket}.</div>

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      {data.map(card => (
        <MediaCard key={card.id} item={card} bucket={bucket} />
      ))}
    </div>
  )
}
