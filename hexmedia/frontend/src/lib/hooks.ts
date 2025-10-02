import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getJSON, postJSON } from './api'
import type { BucketsCount, MediaItemCardRead, IngestPlanItem, IngestRunResponse, ThumbPlanItem, ThumbResponse, MediaAssetRead } from '@/types'

// --- helpers ---
function pickThumbURL(item: MediaItemCardRead): string | null {
  // prefer direct field
  if (item.thumb_url) return item.thumb_url
  // otherwise derive from assets if backend didn’t set thumb_url
  const thumbAsset: MediaAssetRead | undefined = item.assets?.find(a => a.kind === 'thumb' && (a.url || a.rel_path))
  return thumbAsset?.url ?? null
}

// Buckets list (ordered) + counts
export function useBucketOrder() {
  return useQuery({
    queryKey: ['buckets', 'order'],
    queryFn: () => getJSON<string[]>('/media-items/buckets/order'),
  })
}

export function useBucketCounts() {
  return useQuery({
    queryKey: ['buckets', 'count'],
    queryFn: () => getJSON<BucketsCount>('/media-items/buckets/count'),
  })
}

/**
 * Cards in a bucket.
 * - Always include assets, persons, ratings, *and* tags (for chips)
 * - Normalize each item to ensure `thumb_url` exists (fallback to assets)
 */
export function useBucketCards(bucket: string, include = 'assets,persons,tags,ratings') {
  return useQuery({
    queryKey: ['bucket', bucket, include],
    queryFn: () => getJSON<MediaItemCardRead[]>(`/media-items/by-bucket/${bucket}`, { include })
  })
}

// Ingest
export function useIngestPlan(limit = 20) {
  return useQuery({
    queryKey: ['ingest', 'plan', limit],
    queryFn: () => postJSON<IngestPlanItem[]>('/ingest/plan', null, { limit }),
  })
}

export function useIngestRun() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: { files: string[]; limit?: number }) =>
      postJSON('/ingest/run', payload, payload.limit ? { limit: payload.limit } : undefined),
    onSuccess: () => {
      // Refresh bucket counts/order so the UI reflects new items immediately
      qc.invalidateQueries({ queryKey: ['buckets','count'] })
      qc.invalidateQueries({ queryKey: ['buckets','order'] })
    }
  })
}

// Thumbs
export function useThumbPlan(limit = 20, missing: 'either' | 'both' = 'either') {
  return useQuery({
    queryKey: ['thumb', 'plan', { limit, missing }],
    queryFn: () => getJSON<ThumbPlanItem[]>('/ingest/thumb_plan', { limit, missing }),
  })
}

export function useThumbRun() {
  return useMutation({
    mutationFn: (payload: {
      limit: number
      regenerate: boolean
      include_missing: boolean
      workers?: number
      thumb_format?: string
      collage_format?: string
      thumb_width?: number
      tile_width?: number
      upscale_policy?: 'never' | 'if_smaller_than' | 'always'
    }) => postJSON<ThumbResponse>('/ingest/thumb', payload),
  })
}

// --- API health ping (lightweight: just hits a tiny endpoint) ---
export function useApiHealth() {
  return useQuery({
    queryKey: ['health'],
    // using a small endpoint as a ping; if it 200s, API is "up"
    queryFn: async () => {
      await getJSON<string[]>('/media-items/buckets/order')
      return true
    },
    staleTime: 60_000,
    refetchInterval: 60_000,
    retry: 1,
  })
}

export function useRateItem(bucket?: string, include = 'assets,persons,ratings') {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, score }: { id: string; score: number }) => rateItem(id, score),
    onSuccess: (_data, vars) => {
      if (bucket) {
        qc.setQueryData<MediaItemCardRead[]>(['bucket', bucket, include], (old) => {
          if (!old) return old
          return old.map(it => (String(it.id) === String(vars.id) ? { ...it, rating: vars.score } : it))
        })
      }
    },
  })
}
