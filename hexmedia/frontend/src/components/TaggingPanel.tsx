import { useMemo, useState } from 'react'
import { useTagGroups, useTags, useAttachTag, useDetachTag, useCreateTag, useGroupTags } from '@/lib/hooks'
import MultiSelectPopover from '@/components/Tagging/MultiSelectPopover'
import type { MediaItemCardRead, TagRead, TagGroupRead } from '@/types'

type Treeish = TagGroupRead & { children?: TagGroupRead[] }

function flattenGroups(nodes: Treeish[] = []): TagGroupRead[] {
  const out: TagGroupRead[] = []
  const walk = (arr: Treeish[]) => {
    for (const g of arr) {
      out.push(g)
      if (g.children?.length) walk(g.children as Treeish[])
    }
  }
  walk(nodes)
  return out
}

function slugify(s: string) {
  return s
    .toLowerCase()
    .trim()
    .replace(/\s+/g, '-')
    .replace(/[^a-z0-9_-]/g, '')
    .slice(0, 128)
}

function Chip({ tag, onRemove }: { tag: TagRead; onRemove?: () => void }) {
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs border border-neutral-700">
      {tag.name}
      {onRemove && (
        <button
          className="text-neutral-500 hover:text-red-500"
          title="Remove tag"
          onClick={onRemove}
        >
          ×
        </button>
      )}
    </span>
  )
}

/** Display like: Group :: Parent :: Tag (best-effort, supports id or path) */
function formatTagPath(
  t: TagRead,
  groupsById: Map<string, TagGroupRead>,
  groupsByPath: Map<string, TagGroupRead>,
  tagsIndex: Map<string, TagRead>
) {
  const parts: string[] = []
  if (t.group_id && groupsById.has(String(t.group_id))) {
    parts.push(groupsById.get(String(t.group_id))!.display_name)
  } else if (t.group_path && groupsByPath.has(String(t.group_path))) {
    parts.push(groupsByPath.get(String(t.group_path))!.display_name)
  } else {
    parts.push('Freeform')
  }

  // Parent chain via ids if available (best-effort)
  const chain: string[] = []
  let cur: TagRead | undefined = t
  for (let hop = 0; hop < 5 && cur?.parent_id; hop++) {
    const p = tagsIndex.get(String(cur.parent_id))
    if (!p) break
    chain.unshift(p.name)
    cur = p
  }
  if (chain.length) parts.push(...chain)
  parts.push(t.name)
  return parts.join(' :: ')
}

export default function TaggingPanel({ item, bucket }: { item: MediaItemCardRead; bucket: string }) {
  const groupsQ = useTagGroups()
  const groupsTree = groupsQ.data ?? []
  const groupsFlat = useMemo(() => flattenGroups(groupsTree as Treeish[]), [groupsTree])

  // Lookup maps from flattened list
  const groupsById = useMemo(() => {
    const m = new Map<string, TagGroupRead>()
    for (const g of groupsFlat) m.set(String(g.id), g)
    return m
  }, [groupsFlat])

  const groupsByPath = useMemo(() => {
    const m = new Map<string, TagGroupRead>()
    for (const g of groupsFlat) if (g.path) m.set(String(g.path), g)
    return m
  }, [groupsFlat])

  const detachM = useDetachTag(bucket)
  const attachM = useAttachTag(bucket)
  const createTagM = useCreateTag()

  // Group selected tags by **resolved group id**; freeform under null
  const tagsByGroup = useMemo(() => {
    const map = new Map<string | null, TagRead[]>()
    const ensure = (k: string | null) => {
      if (!map.has(k)) map.set(k, [])
      return map.get(k)!
    }

    for (const t of item.tags ?? []) {
      if (t.group_id) {
        ensure(String(t.group_id)).push(t)
      } else if (t.group_path && groupsByPath.has(String(t.group_path))) {
        // resolve to actual group id via path
        const gid = String(groupsByPath.get(String(t.group_path))!.id)
        ensure(gid).push(t)
      } else {
        ensure(null).push(t) // freeform
      }
    }
    return map
  }, [item.tags, groupsByPath])

  /** GROUPED SECTION */
  function GroupSection({ group }: { group: TagGroupRead }) {
    const groupId = String(group.id)
    const isMulti = String(group.cardinality ?? '').toUpperCase() === 'MULTI'
    const selected = tagsByGroup.get(groupId) ?? []

    if (isMulti) {
      // MULTI: debounced search + checklist popover
      const { items, isLoading, q, setQ } = useGroupTags(groupId, { limit: 50 })
      const selectedIds = useMemo(() => selected.map((t) => String(t.id)), [selected])

      // Index to resolve TagRead from id for attach (merge fetched + selected)
      const byId = useMemo(() => {
        const m = new Map<string, TagRead>()
        for (const t of items ?? []) m.set(String(t.id), t)
        for (const t of selected) m.set(String(t.id), t)
        return m
      }, [items, selected])

      const onChangeSelectedIds = (nextIds: string[]) => {
        const prev = new Set(selectedIds)
        const next = new Set(nextIds)

        // Detach removed
        for (const id of prev) {
          if (!next.has(id)) {
            detachM.mutate({ mediaId: String(item.id), tagId: String(id) })
          }
        }
        // Attach added
        for (const id of next) {
          if (!prev.has(id)) {
            const tag = byId.get(String(id))
            if (tag) attachM.mutate({ mediaId: String(item.id), tag })
          }
        }
      }

      return (
        <section className="space-y-2">
          <div className="flex items-center justify-between gap-3">
            <div className="text-sm font-semibold">{group.display_name}</div>
            <MultiSelectPopover
              items={items ?? []}
              selectedIds={selectedIds}
              onChange={onChangeSelectedIds}
              loading={isLoading}
              searchValue={q}
              onSearchChange={setQ}
              trigger={({ open }) => (
                <button
                  type="button"
                  onClick={open}
                  className="rounded-md border px-2 py-1 text-sm bg-white/5 border-neutral-700"
                  title="Add / Edit tags"
                >
                  + Add / Edit
                </button>
              )}
            />
          </div>

          <div className="flex flex-wrap gap-2">
            {selected.length ? (
              selected.map((t) => (
                <Chip
                  key={t.id}
                  tag={t}
                  onRemove={() => detachM.mutate({ mediaId: String(item.id), tagId: String(t.id) })}
                />
              ))
            ) : (
              <div className="text-xs text-neutral-500">No tags selected.</div>
            )}
          </div>
        </section>
      )
    }

    // SINGLE: keep your current dropdown UX
    const groupTagsQ = useTags(groupId)
    const options = (groupTagsQ.data ?? []).filter(
      (t) => !selected.some((s) => String(s.id) === String(t.id))
    )

    return (
      <section className="space-y-2">
        <div className="flex items-center justify-between gap-3">
          <div className="text-sm font-semibold">{group.display_name}</div>
          <div className="flex items-center gap-2">
            <select
              className="rounded-md border px-2 py-1 text-sm bg-white/5 border-neutral-700"
              defaultValue=""
              onChange={(e) => {
                const tagId = e.target.value
                if (tagId) {
                  const tag = options.find((t) => String(t.id) === tagId)
                  if (tag) attachM.mutate({ mediaId: String(item.id), tag })
                }
                e.currentTarget.value = ''
              }}
              disabled={groupTagsQ.isLoading || !options.length}
              title={groupTagsQ.isLoading ? 'Loading…' : undefined}
            >
              <option value="" disabled>+ Add tag</option>
              {options.map((t) => (
                <option key={t.id} value={String(t.id)}>{t.name}</option>
              ))}
            </select>
          </div>
        </div>

        <div className="flex flex-wrap gap-2">
          {selected.length ? (
            selected.map((t) => (
              <Chip
                key={t.id}
                tag={t}
                onRemove={() => detachM.mutate({ mediaId: String(item.id), tagId: String(t.id) })}
              />
            ))
          ) : (
            <div className="text-xs text-neutral-500">No tag selected.</div>
          )}
        </div>
      </section>
    )
  }

  /** FREEFORM SECTION (typeahead with navy dropdown) */
  function FreeformSection() {
    const [q, setQ] = useState('')
    const freeformQ = useTags(undefined, q || undefined)

    const tagsIndex = useMemo(() => {
      const m = new Map<string, TagRead>()
      for (const t of freeformQ.data ?? []) m.set(String(t.id), t)
      return m
    }, [freeformQ.data])

    const freeformSelected = tagsByGroup.get(null) ?? []
    const showPanel = q.trim().length > 0

    const onCreateAndAttach = () => {
      const name = q.trim()
      if (!name) return
      const body = { name, slug: slugify(name), description: null as string | null }
      createTagM.mutate({ body }, {
        onSuccess: (newTag) => {
          attachM.mutate({ mediaId: String(item.id), tag: newTag })
          setQ('')
        }
      })
    }

    return (
      <section className="space-y-2 relative">
        <div className="text-sm font-semibold">Freeform (Ungrouped)</div>

        <div className="flex flex-wrap gap-2">
          {freeformSelected.length ? (
            freeformSelected.map((t) => (
              <Chip
                key={t.id}
                tag={t}
                onRemove={() => detachM.mutate({ mediaId: String(item.id), tagId: String(t.id) })}
              />
            ))
          ) : (
            <div className="text-xs text-neutral-500">No freeform tags.</div>
          )}
        </div>

        <div className="relative">
          <input
            className="w-full rounded-md border px-3 py-2 text-sm bg-white/5 border-neutral-700"
            placeholder="Type to search or create…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />

          {showPanel && (
            <div
              className="absolute z-10 mt-1 w-full rounded-md shadow-lg max-h-64 overflow-auto border"
              style={{
                backgroundColor: '#001f3f', // navy
                color: 'white',
                borderColor: '#001a35',
              }}
            >
              {(freeformQ.data ?? []).length > 0 ? (
                <ul className="py-1">
                  {(freeformQ.data ?? []).map((t) => (
                    <li key={t.id}>
                      <button
                        className="w-full text-left px-3 py-2 text-sm"
                        style={{ backgroundColor: 'transparent' }}
                        onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = '#004080')}
                        onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
                        onClick={() => {
                          attachM.mutate({ mediaId: String(item.id), tag: t })
                          setQ('')
                        }}
                        title={t.slug}
                      >
                        {formatTagPath(t, groupsById, groupsByPath, tagsIndex)}
                      </button>
                    </li>
                  ))}
                </ul>
              ) : (
                <div className="px-3 py-2 text-sm" style={{ color: '#cbd5e1' }}>
                  No matches
                </div>
              )}

              <div style={{ borderTop: '1px solid #0b2447' }} />

              <button
                className="w-full text-left px-3 py-2 text-sm font-medium"
                style={{ backgroundColor: 'transparent' }}
                onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = '#004080')}
                onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
                onClick={onCreateAndAttach}
                disabled={!q.trim() || createTagM.isPending}
                title="Create a new freeform tag and attach it"
              >
                + Add new tag “{q.trim()}”
              </button>
            </div>
          )}
        </div>
      </section>
    )
  }

  return (
    <div className="space-y-6">
      {groupsFlat.map((g) => (
        <GroupSection key={g.id} group={g} />
      ))}
      <FreeformSection />
    </div>
  )
}
