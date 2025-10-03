import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getJSON, postJSON, patchJSON, delJSON } from './api'
import type { BucketsCount, MediaItemCardRead, IngestPlanItem, IngestRunResponse, ThumbPlanItem,
    ThumbResponse, MediaAssetRead, TagGroupRead, TagGroupCreate, TagGroupUpdate,
    TagRead, TagCreate, TagUpdate } from '@/types'

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

// ---- Tag Groups
export function useTagGroups() {
  return useQuery({
    queryKey: ['tag-groups'],
    queryFn: () => getJSON<TagGroupRead[]>('/tags/groups')
  })
}

export function useUpdateTagGroup() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: TagGroupUpdate }) =>
      patchJSON<TagGroupRead>(`/tags/groups/${id}`, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['tag-groups'] })
  })
}

export function useDeleteTagGroup() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => delJSON<void>(`/tags/groups/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['tag-groups'] })
  })
}

// Tag groups (tree)
export function useTagGroupTree() {
  return useQuery({
    queryKey: ['tag-groups','tree'],
    queryFn: () => getJSON<TagGroupNode[]>('/tags/tag-groups/tree')
  })
}

export function useCreateTagGroup() {
  return useMutation({
    mutationFn: (body: TagGroupCreate) =>
      postJSON<TagGroupNode>('/tags/tag-groups', body)
  })
}

export function useMoveTagGroup() {
  return useMutation({
    mutationFn: (payload: { group_id: string } & TagGroupMove) =>
      postJSON<TagGroupNode>(`/tags/tag-groups/${payload.group_id}/move`, payload)
  })
}

// ---- Tags
export function useTags(groupId?: string | null, search?: string) {
  return useQuery({
    queryKey: ['tags', { groupId: groupId ?? null, search: search ?? '' }],
    queryFn: () =>
      getJSON<TagRead[]>('/tags', {
        ...(groupId ? { group_id: groupId } : {}),
        ...(search ? { q: search } : {})
      })
  })
}

export function useCreateTag() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: TagCreate) => postJSON<TagRead>('/tags', body),
    onSuccess: (_d, vars) => {
      qc.invalidateQueries({ queryKey: ['tags'] })
      qc.invalidateQueries({ queryKey: ['tag-groups'] })
      // Optionally pre-select group refresh
      if (vars.group_id) qc.invalidateQueries({ queryKey: ['tags', { groupId: vars.group_id }] })
    }
  })
}

export function useUpdateTag() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: TagUpdate }) =>
      patchJSON<TagRead>(`/tags/${id}`, body),
    onSuccess: (_d, vars) => {
      qc.invalidateQueries({ queryKey: ['tags'] })
      if (vars.body.group_id) qc.invalidateQueries({ queryKey: ['tags', { groupId: vars.body.group_id }] })
    }
  })
}

export function useDeleteTag() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => delJSON<void>(`/tags/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['tags'] })
  })
}