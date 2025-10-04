import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getJSON, postJSON, patchJSON, delJSON, rateItem } from './api'
import type { BucketsCount, MediaItemCardRead, IngestPlanItem, IngestRunResponse, ThumbPlanItem,
    ThumbResponse, MediaAssetRead, TagGroupRead, TagGroupCreate, TagGroupUpdate,
    TagRead, TagCreate, TagUpdate, TagGroupNode, TagGroupMove } from '@/types'

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
// export function useBucketCards(bucket: string, include = 'assets,persons,tags,ratings') {
//   return useQuery({
//     queryKey: ['bucket', bucket, include],
//     queryFn: () => getJSON<MediaItemCardRead[]>(`/media-items/by-bucket/${bucket}`, { include })
//   })
// }
export function useBucketCards(bucket: string, include = 'assets,persons,tags,ratings') {
   return useQuery({
     queryKey: ['bucket', bucket, include],
    queryFn: async () => {
      const data = await getJSON<MediaItemCardRead[]>(`/media-items/by-bucket/${bucket}`, { include })
      // ensure thumb_url present when asset list is provided
      return data.map(it => (it.thumb_url ? it : { ...it, thumb_url: pickThumbURL(it) }))
    }
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
      patchJSON<TagGroupRead>(`/tags/tag-groups/${id}`, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['tag-groups'] })
  })
}

export function useDeleteTagGroup() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id }: { id: string }) => delJSON<void>(`/tags/tag-groups/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['tag-groups'] })
      qc.invalidateQueries({ queryKey: ['tag-groups','tree'] })
    }
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
    const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: TagGroupCreate) =>
      postJSON<TagGroupNode>('/tags/tag-groups', body),
    onSuccess: () => {
      // Your tree UI uses useTagGroups() (GET /tags/groups)
      // so we must invalidate that cache key to refetch.
      qc.invalidateQueries({ queryKey: ['tag-groups'] })
      // If anywhere else uses the tree endpoint, refresh that too.
      qc.invalidateQueries({ queryKey: ['tag-groups', 'tree'] })
    }
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

// export function useCreateTag() {
//   const qc = useQueryClient()
//   return useMutation({
//     mutationFn: (body: TagCreate) => postJSON<TagRead>('/tags', body),
//     onSuccess: (_d, vars) => {
//       qc.invalidateQueries({ queryKey: ['tags'] })
//       qc.invalidateQueries({ queryKey: ['tag-groups'] })
//       // Optionally pre-select group refresh
//       if (vars.group_id) qc.invalidateQueries({ queryKey: ['tags', { groupId: vars.group_id }] })
//     }
//   })
// }

export function useCreateTag() {
   const qc = useQueryClient()
   return useMutation({

      mutationFn: (args: { body: TagCreate & { group_path?: string | null; parent_path?: string | null } }) => {

      return postJSON<TagRead>('/tags', args.body)
    },
    onSuccess: (_d, args) => {
       qc.invalidateQueries({ queryKey: ['tags'] })
       qc.invalidateQueries({ queryKey: ['tag-groups'] })
      if (args.body.group_id) {
        qc.invalidateQueries({ queryKey: ['tags', { groupId: args.body.group_id }] })
      }
     }
   })
 }

// export function useUpdateTag() {
//   const qc = useQueryClient()
//   return useMutation({
//     mutationFn: ({ id, body }: { id: string; body: TagUpdate }) =>
//       patchJSON<TagRead>(`/tags/${id}`, body),
//     onSuccess: (_d, vars) => {
//       qc.invalidateQueries({ queryKey: ['tags'] })
//       if (vars.body.group_id) qc.invalidateQueries({ queryKey: ['tags', { groupId: vars.body.group_id }] })
//     }
//   })
// }
export function useUpdateTag() {
   const qc = useQueryClient()
   return useMutation({

       mutationFn: (args: { id: string; body: TagUpdate & { group_path?: string | null; parent_path?: string | null } }) => {
      return patchJSON<TagRead>(`/tags/${args.id}`, args.body)
    },
    onSuccess: (_d, args) => {
       qc.invalidateQueries({ queryKey: ['tags'] })

      if (args.body.group_id) {
        qc.invalidateQueries({ queryKey: ['tags', { groupId: args.body.group_id }] })
      }
     }
   })
 }

export function useDeleteTag() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id }: { id: string }) => delJSON<void>(`/tags/${id}`),
    onMutate: async ({ id }) => {
      // cancel incoming fetches and snapshot
      await qc.cancelQueries({ queryKey: ['tags'] })
      const prev = qc.getQueriesData<TagRead[]>({ queryKey: ['tags'] })
      // optimistically remove from any cached tag lists
      prev.forEach(([key, list]) => {
        if (Array.isArray(list)) {
          qc.setQueryData(
            key as any,
            list.filter(t => t.id !== id)
          )
        }
      })
      return { prev }
    },
    onError: (_err, _vars, ctx) => {
      // rollback on error
      if (ctx?.prev) {
        ctx.prev.forEach(([key, list]) => qc.setQueryData(key as any, list))
      }
    },
    onSettled: () => {
      qc.invalidateQueries({ queryKey: ['tags'] })
    }
  })
}
// attach tag
export function useAttachTag(bucket?: string, include = 'assets,persons,tags,ratings') {
  const qc = useQueryClient()
  return useMutation({
    
          // pass the whole tag so we can optimistically update the UI
    mutationFn: (args: { mediaId: string; tag: TagRead }) =>
      postJSON<{ media_item_id: string; tag_id: string }>(
        `/media-tags/media-items/${args.mediaId}/tags`,
        { tag_id: args.tag.id }
      ),
    onMutate: async ({ mediaId, tag }) => {
      if (!bucket) return
      await qc.cancelQueries({ queryKey: ['bucket', bucket, include] })
      const prev = qc.getQueryData<import('@/types').MediaItemCardRead[]>(['bucket', bucket, include])
      // optimistic update: add/replace in SINGLE groups, add if not present in MULTI/freeform
        const getGroupKey = (t: import('@/types').TagRead) =>
        (t.group_id ?? t.group_path ?? null) as string | null
      qc.setQueryData<import('@/types').MediaItemCardRead[]>(['bucket', bucket, include], (list) => {
        if (!list) return list
        return list.map((it) => {
          if (String(it.id) !== String(mediaId)) return it
          const existing = it.tags ?? []
            const key = getGroupKey(tag)
          const sameGroup = key ? existing.filter(t => getGroupKey(t) === key) : []
          let nextTags = existing.slice()
            if (key && sameGroup.length > 0) {
            // replace all tags from that group (safe for SINGLE; also fine UX for MULTI)
            nextTags = nextTags.filter(t => getGroupKey(t) !== key)
          }
          if (!nextTags.find(t => String(t.id) === String(tag.id))) {
            nextTags.push(tag)
          }
          return { ...it, tags: nextTags }
        })
      })
      return { prev }
    },
    onError: (_err, _vars, ctx) => {
      if (!bucket) return
      // rollback
      if (ctx?.prev) qc.setQueryData(['bucket', bucket, include], ctx.prev)
    },
    onSettled: () => {
      if (bucket) qc.invalidateQueries({ queryKey: ['bucket', bucket, include] })
    },
  })
}

// detach tag
export function useDetachTag(bucket?: string, include = 'assets,persons,tags,ratings') {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (args: { mediaId: string; tagId: string }) =>
      delJSON<void>(`/media-tags/media-items/${args.mediaId}/tags/${args.tagId}`),
      onMutate: async ({ mediaId, tagId }) => {
        if (!bucket) return
          await qc.cancelQueries({ queryKey: ['bucket', bucket, include] })
          const prev = qc.getQueryData<import('@/types').MediaItemCardRead[]>(['bucket', bucket, include])
          qc.setQueryData<import('@/types').MediaItemCardRead[]>(['bucket', bucket, include], (list) => {
            if (!list) return list
            return list.map((it) => {
              if (String(it.id) !== String(mediaId)) return it
              const nextTags = (it.tags ?? []).filter(t => String(t.id) !== String(tagId))
              return { ...it, tags: nextTags }
            })
          })
          return { prev }
    },
    onError: (_err, _vars, ctx) => {
      if (!bucket) return
      if (ctx?.prev) qc.setQueryData(['bucket', bucket, include], ctx.prev)
    },
    onSuccess: (_d, vars) => {
      if (bucket) {
        qc.invalidateQueries({ queryKey: ['bucket', bucket, include] })
      }
    }
  })
}