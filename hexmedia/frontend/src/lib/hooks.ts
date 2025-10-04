/**
 * Hexmedia Frontend Hooks
 *
 * This module centralizes React Query hooks for the app. Hooks are grouped roughly
 * by feature area and follow a few conventions:
 *
 * Categories
 * ----------
 * - Buckets
 *    - useBucketOrder(): ordered list of bucket names for navigation.
 *    - useBucketCounts(): counts per bucket for badges/filters.
 *    - useBucketCards(bucket, include): media cards; normalizes thumb_url.
 *
 * - Ingest
 *    - useIngestPlan(limit): preview which files would be ingested next.
 *    - useIngestRun(): run an ingest; invalidates bucket metadata.
 *
 * - Thumbnails
 *    - useThumbPlan(limit, missing): list of items needing thumbs/collages.
 *    - useThumbRun(): trigger thumbnail/collage generation.
 *
 * - Health
 *    - useApiHealth(): lightweight API reachability check (boolean).
 *
 * - Ratings
 *    - useRateItem(bucket, include): set item rating; optimistic update.
 *
 * - Tag Groups
 *    - useTagGroups(): list of tag *groups* (containers/categories).
 *    - useTagGroupTree(): hierarchical tree of groups for navigation/UX.
 *    - useCreateTagGroup(): create new group; invalidates lists/tree.
 *    - useUpdateTagGroup(): update group properties (name/cardinality/etc.).
 *    - useDeleteTagGroup(): delete group; refresh lists/tree.
 *    - useMoveTagGroup(): re-parent/reorder a group via backend.
 *
 * - Tags
 *    - useTags(groupId?, search?): list of tags; optionally filter by group or search.
 *    - useGroupTags(groupId, opts): tags *within a specific group* with debounced search.
 *    - useCreateTag(): create freeform or grouped tag; refresh caches.
 *    - useUpdateTag(): update tag fields/grouping; refresh caches.
 *    - useDeleteTag(): delete tag with optimistic removal and rollback on error.
 *    - useAttachTag(bucket, include): attach tag to a media item (SINGLE groups replace).
 *    - useDetachTag(bucket, include): detach tag from a media item.
 *
 * Conventions
 * -----------
 * - No empty query params: query builders skip undefined/null/blank values to avoid noisy CORS preflights.
 * - Optimistic UI: mutations that affect bucket cards update local cache first, then revalidate.
 * - Query Keys: include stable identifiers (e.g., bucket name, include string, groupId, search).
 * - Pagination: where supported, expose {cursor, fetchNext, hasMore}; otherwise return full arrays.
 * - Error Handling: hooks surface {error} for UI toasts; some mutations roll back on error.
 *
 * Tip
 * ---
 * If you add or refactor hooks, keep names specific and scan for unused imports/vars/methods.
 * When in doubt about existing file contents, prefer pasting the current code in chat to align changes.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getJSON, postJSON, patchJSON, delJSON, rateItem } from './api'
import { useEffect, useMemo, useRef, useState } from 'react' // used by useGroupTags
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

type Args = {
    mediaId: string;
    nextIds: string[];
    prevIds: string[];
}

// Buckets list (ordered) + counts
export function useBucketOrder() {
  // Purpose: Fetch the ordered list of bucket names for navigation/filters.
  return useQuery({
    queryKey: ['buckets', 'order'],
    queryFn: () => getJSON<string[]>('/media-items/buckets/order'),
  })
}

export function useBucketCounts() {
  // Purpose: Fetch the item counts per bucket for badges/overview.
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
  // Purpose: Fetch a bucket’s media cards and ensure each has a usable thumb URL.
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
  // Purpose: Request the next batch of files to ingest (preview plan).
  return useQuery({
    queryKey: ['ingest', 'plan', limit],
    queryFn: () => postJSON<IngestPlanItem[]>('/ingest/plan', null, { limit }),
  })
}

export function useIngestRun() {
  // Purpose: Kick off the ingest process and refresh bucket metadata on success.
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
  // Purpose: Fetch a plan of items that need thumbs/collages (with filters).
  return useQuery({
    queryKey: ['thumb', 'plan', { limit, missing }],
    queryFn: () => getJSON<ThumbPlanItem[]>('/ingest/thumb_plan', { limit, missing }),
  })
}

export function useThumbRun() {
  // Purpose: Trigger thumbnail/collage generation with the selected options.
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
  // Purpose: Lightweight check that the API is reachable (returns boolean).
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
  // Purpose: Rate a media item and optimistically update its card in the active bucket.
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
  // Purpose: Fetch all tag groups (containers) for settings and grouping logic.
  return useQuery({
    queryKey: ['tag-groups'],
    queryFn: () => getJSON<TagGroupRead[]>('/tags/groups')
  })
}

export function useUpdateTagGroup() {
  // Purpose: Update an existing tag group’s properties (name, cardinality, etc.).
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: TagGroupUpdate }) =>
      patchJSON<TagGroupRead>(`/tags/tag-groups/${id}`, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['tag-groups'] })
  })
}

export function useDeleteTagGroup() {
  // Purpose: Delete a tag group and refresh group lists/tree.
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
  // Purpose: Fetch the hierarchical tree view of tag groups for UI navigation.
  return useQuery({
    queryKey: ['tag-groups','tree'],
    queryFn: () => getJSON<TagGroupNode[]>('/tags/tag-groups/tree')
  })
}

export function useCreateTagGroup() {
  // Purpose: Create a new tag group and refresh group lists/tree.
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
  // Purpose: Move a tag group in the tree (re-parent/reorder) via backend endpoint.
  return useMutation({
    mutationFn: (payload: { group_id: string } & TagGroupMove) =>
      postJSON<TagGroupNode>(`/tags/tag-groups/${payload.group_id}/move`, payload)
  })
}

// ---- Tags
export function useTags(groupId?: string | null, search?: string) {
  // Purpose: Fetch tags (optionally filtered by a specific group and/or search query).
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
  // Purpose: Create a tag (freeform or grouped) and refresh relevant caches.
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

export function useUpdateTag() {
  // Purpose: Update a tag (name/grouping/etc.) and refresh relevant caches.
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
  // Purpose: Delete a tag with optimistic UI removal and fallback on error.
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
  // Purpose: Attach a tag to a media item with optimistic update (SINGLE group replace).
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
  // Purpose: Detach a tag from a media item with optimistic removal and cache refresh.
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

/* ------------------------- New: useGroupTags (debounced) ------------------------- */

export function useGroupTags(
  groupId: string | null | undefined,
  opts: { q?: string; limit?: number; cursor?: string | null; enabled?: boolean } = {}
) {
  // Purpose: Fetch tags that belong to a specific group with debounced search and safe query params.
  const [items, setItems] = useState<TagRead[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<Error | null>(null)

  const [q, setQ] = useState(opts.q ?? "")
  const [cursor, setCursor] = useState<string | null>(opts.cursor ?? null)
  const [hasMore, setHasMore] = useState(false)

  const debouncedQ = (() => {
    const [debounced, setDebounced] = useState(q)
    useEffect(() => {
      const t = setTimeout(() => setDebounced(q), 300)
      return () => clearTimeout(t)
    }, [q])
    return debounced
  })()

  const enabled = !!groupId && (opts.enabled ?? true)
  const limit = opts.limit ?? 50

  const abortRef = useRef<AbortController | null>(null)
  const latestKey = useRef<string>("")

  function buildQuery(params: Record<string, string | number | undefined | null>) {
    const usp = new URLSearchParams()
    for (const [k, v] of Object.entries(params)) {
      if (v === undefined || v === null) continue
      const s = String(v).trim()
      if (!s) continue // avoid empty query params (prevents noisy CORS preflights)
      usp.set(k, s)
    }
    const qs = usp.toString()
    return qs ? `?${qs}` : ""
  }

  async function fetchPage(nextCursor: string | null, replace: boolean) {
    if (!enabled || !groupId) return

    if (abortRef.current) abortRef.current.abort()
    const ac = new AbortController()
    abortRef.current = ac

    setIsLoading(true)
    setError(null)

    const query = buildQuery({
      group_id: groupId,
      q: debouncedQ || undefined,
      limit,
      cursor: nextCursor || undefined,
    })

    const key = `${groupId}|${debouncedQ}|${nextCursor ?? ""}|${limit}|${Date.now()}`
    latestKey.current = key

    try {
      // Using getJSON keeps consistency with the rest of this file.
      const data = await getJSON<TagRead[]>('/tags' + query)
      if (latestKey.current !== key) return // stale
      setItems((prev) => (replace ? data : [...prev, ...data]))
      setIsLoading(false)
      // If backend returns arrays (no cursor), just say no more pages for now.
      setHasMore(false)
      setCursor(null)
    } catch (e: any) {
      if (e?.name === 'AbortError') return
      if (latestKey.current === key) {
        setIsLoading(false)
        setError(e instanceof Error ? e : new Error(String(e)))
      }
    }
  }

  // Refetch when group or debounced search changes
  useEffect(() => {
    setItems([])
    setCursor(null)
    setHasMore(false)
    if (enabled && groupId) {
      void fetchPage(null, true)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [groupId, debouncedQ, enabled, limit])

  const fetchNext = () => {
    if (!hasMore || isLoading) return
    void fetchPage(cursor, false)
  }

  const refetch = () => {
    void fetchPage(null, true)
  }

  return {
    items,
    isLoading,
    error,
    q,
    setQ,
    cursor,
    setCursor,
    fetchNext,
    hasMore,
    refetch,
  }
}
export function useAttachTagsBulk() {
  // Purpose: Fan-out attach/detach diffs for a group to reach desired selection.
  return useMutation({
    mutationFn: async ({ mediaId, nextIds, prevIds }: Args) => {
      const toAttach = nextIds.filter((id) => !prevIds.includes(id));
      const toDetach = prevIds.filter((id) => !nextIds.includes(id));

      // naive fan-out; can parallelize if backend tolerates
      for (const id of toDetach) {
        await delJSON<void>(`/media-tags/media-items/${mediaId}/tags/${id}`);
      }
      for (const id of toAttach) {
        await postJSON(`/media-tags/media-items/${mediaId}/tags`, { tag_id: id });
      }
      return { attached: toAttach, detached: toDetach };
    },
  });
}