import { useMemo, useState } from 'react'
import {
  useTagGroups, useCreateTagGroup, useUpdateTagGroup, useDeleteTagGroup,
  useTags, useCreateTag, useUpdateTag, useDeleteTag
} from '@/lib/hooks'
import type { TagGroupRead, TagRead } from '@/types'

function slugify(s: string) {
  return s.toLowerCase().trim()
    .replace(/\s+/g, '-')
    .replace(/[^a-z0-9_-]/g, '')
    .slice(0, 128)
}

type TreeNode = TagGroupRead & { children: TreeNode[] }

function buildTree(groups?: TagGroupRead[]): TreeNode[] {
  if (!groups?.length) return []
  const byParent = new Map<string | null, TagGroupRead[]>()
  groups.forEach(g => {
    const key = g.parent_id ?? null
    if (!byParent.has(key)) byParent.set(key, [])
    byParent.get(key)!.push(g)
  })
  const toNode = (g: TagGroupRead): TreeNode => ({
    ...g, children: (byParent.get(g.id) || []).map(toNode),
  })
  return (byParent.get(null) || []).map(toNode)
}

export default function SettingsTags() {
  const groupsQ = useTagGroups()
  const [selectedGroupId, setSelectedGroupId] = useState<string | null>(null)

  const tree = useMemo(() => buildTree(groupsQ.data), [groupsQ.data])

  const tagsQ = useTags(selectedGroupId)

  // --- Group mutations ---
  const createGroupM = useCreateTagGroup()
  const updateGroupM = useUpdateTagGroup()
  const deleteGroupM = useDeleteTagGroup()

  // --- Tag mutations ---
  const createTagM = useCreateTag()
  const updateTagM = useUpdateTag()
  const deleteTagM = useDeleteTag()

  // Local forms
  const [gForm, setGForm] = useState<{ id?: string; parent_id: string | null; key: string; display_name: string; cardinality: 'MULTI'|'SINGLE'; description?: string }>({
    parent_id: null, key: '', display_name: '', cardinality: 'MULTI', description: ''
  })

  const [tForm, setTForm] = useState<{ id?: string; name: string; slug: string; description?: string; parent_id?: string | null }>({
    name: '', slug: '', description: '', parent_id: null
  })

  const onSelectGroup = (id: string | null) => {
    setSelectedGroupId(id)
    // reset tag form with group context
    setTForm({ id: undefined, name: '', slug: '', description: '', parent_id: null })
  }

  const startNewGroup = (parent_id: string | null) => {
    setGForm({ id: undefined, parent_id, key: '', display_name: '', cardinality: 'MULTI', description: '' })
  }

  const startEditGroup = (g: TagGroupRead) => {
    setGForm({
      id: g.id,
      parent_id: g.parent_id,
      key: g.key,
      display_name: g.display_name,
      cardinality: g.cardinality,
      description: g.description || ''
    })
  }

  const submitGroup = () => {
    const body = {
      parent_id: gForm.parent_id ?? null,
      key: gForm.key.trim(),
      display_name: gForm.display_name.trim(),
      cardinality: gForm.cardinality,
      description: gForm.description?.trim() || null,
    }
    if (!body.key || !body.display_name) return alert('Key and Display Name are required.')

    if (gForm.id) {
      updateGroupM.mutate({ id: gForm.id, body })
    } else {
      createGroupM.mutate(body)
    }
    setGForm({ parent_id: selectedGroupId, key: '', display_name: '', cardinality: 'MULTI', description: '' })
  }

  const removeGroup = (g: TagGroupRead) => {
    if (!confirm(`Delete group "${g.display_name}"?\n(Will fail if it has children or tags.)`)) return
    deleteGroupM.mutate(g.id)
    if (selectedGroupId === g.id) setSelectedGroupId(null)
  }

  const startNewTag = () => {
    setTForm({ id: undefined, name: '', slug: '', description: '', parent_id: null })
  }

  const startEditTag = (t: TagRead) => {
    setTForm({
      id: t.id,
      name: t.name,
      slug: t.slug,
      description: t.description || '',
      // only allow parent selection within same group; keep it for UI completeness
      parent_id: t.parent_id ?? null
    })
  }

  const submitTag = () => {
    const name = tForm.name.trim()
    const slug = (tForm.slug || slugify(name)).trim()
    if (!name || !slug) return alert('Name and Slug are required.')
    const body = {
      group_id: selectedGroupId ?? null,
      name,
      slug,
      description: tForm.description?.trim() || null,
      parent_id: tForm.parent_id ?? null
    }

    if (tForm.id) {
      updateTagM.mutate({ id: tForm.id, body })
    } else {
      createTagM.mutate(body)
    }
    startNewTag()
  }

  const removeTag = (t: TagRead) => {
    if (!confirm(`Delete tag "${t.name}"?`)) return
    deleteTagM.mutate({ id: t.id })
  }

  const renderTree = (nodes: TreeNode[], level = 0) => (
    <ul className="space-y-1">
      {nodes.map(n => (
        <li key={n.id}>
          <div
            className={`flex items-center justify-between gap-2 px-2 py-1 rounded-md cursor-pointer
              ${selectedGroupId === n.id ? 'bg-neutral-200 dark:bg-neutral-800' : 'hover:bg-neutral-100 dark:hover:bg-neutral-900'}`}
            onClick={() => onSelectGroup(n.id)}
            style={{ paddingLeft: level * 12 + 8 }}
          >
            <div className="flex-1">
              <div className="font-medium">{n.display_name}</div>
              <div className="text-xs text-neutral-500 font-mono">{n.key} • {n.cardinality}</div>
            </div>
            <div className="flex items-center gap-2">
              <button className="text-xs px-2 py-1 border rounded-md" onClick={(e) => { e.stopPropagation(); startNewGroup(n.id) }}>+ Child</button>
              <button className="text-xs px-2 py-1 border rounded-md" onClick={(e) => { e.stopPropagation(); startEditGroup(n) }}>Edit</button>
              <button className="text-xs px-2 py-1 border rounded-md" onClick={(e) => { e.stopPropagation(); removeGroup(n) }}>Delete</button>
            </div>
          </div>
          {n.children?.length ? renderTree(n.children, level + 1) : null}
        </li>
      ))}
    </ul>
  )

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
      {/* Left: Group tree + group form */}
      <aside className="lg:col-span-5 space-y-4">
        <div className="flex items-center justify-between">
          <div className="text-lg font-semibold">Tag Groups</div>
          <button className="px-2 py-1 border rounded-md" onClick={() => startNewGroup(null)}>+ Root Group</button>
        </div>

        <div className="rounded-xl border border-neutral-200 dark:border-neutral-800 p-3">
          {groupsQ.isLoading && <div>Loading groups…</div>}
          {groupsQ.error && <div className="text-red-600">Failed to load groups</div>}
          {!!tree.length ? renderTree(tree) : !groupsQ.isLoading && <div className="text-neutral-500">No groups yet.</div>}
        </div>

        <div className="rounded-xl border border-neutral-200 dark:border-neutral-800 p-4 space-y-2">
          <div className="text-sm text-neutral-500">{gForm.id ? 'Edit group' : 'Create group'}</div>
          <div className="grid grid-cols-2 gap-3">
            <div className="col-span-2">
              <label className="block text-sm mb-1">Display name</label>
              <input className="w-full rounded-md border px-3 py-1.5 bg-white dark:bg-neutral-900"
                value={gForm.display_name}
                onChange={e => setGForm(s => ({ ...s, display_name: e.target.value }))}
              />
            </div>
            <div>
              <label className="block text-sm mb-1">Key (slug-like)</label>
              <input className="w-full rounded-md border px-3 py-1.5 bg-white dark:bg-neutral-900"
                value={gForm.key}
                onChange={e => setGForm(s => ({ ...s, key: e.target.value }))}
                placeholder="e.g. people, genre…"
              />
            </div>
            <div>
              <label className="block text-sm mb-1">Cardinality</label>
              <select className="w-full rounded-md border px-3 py-1.5 bg-white dark:bg-neutral-900"
                value={gForm.cardinality}
                onChange={e => setGForm(s => ({ ...s, cardinality: e.target.value as 'MULTI'|'SINGLE' }))}
              >
                <option value="MULTI">MULTI</option>
                <option value="SINGLE">SINGLE</option>
              </select>
            </div>
            <div className="col-span-2">
              <label className="block text-sm mb-1">Parent group</label>
              <select
                className="w-full rounded-md border px-3 py-1.5 bg-white dark:bg-neutral-900"
                value={gForm.parent_id ?? ''}
                onChange={e => setGForm(s => ({ ...s, parent_id: e.target.value || null }))}
              >
                <option value="">(root)</option>
                {groupsQ.data?.map(g => (
                  <option key={g.id} value={g.id}>{g.display_name} ({g.key})</option>
                ))}
              </select>
            </div>
            <div className="col-span-2">
              <label className="block text-sm mb-1">Description</label>
              <textarea className="w-full rounded-md border px-3 py-1.5 bg-white dark:bg-neutral-900"
                rows={2}
                value={gForm.description}
                onChange={e => setGForm(s => ({ ...s, description: e.target.value }))}
              />
            </div>
          </div>
          <div className="flex gap-2">
            <button className="px-3 py-2 rounded-md bg-neutral-900 text-white dark:bg-white dark:text-neutral-900" onClick={submitGroup}>
              {gForm.id ? 'Save Group' : 'Create Group'}
            </button>
            <button className="px-3 py-2 rounded-md border" onClick={() => startNewGroup(selectedGroupId ?? null)}>Reset</button>
          </div>
        </div>
      </aside>

      {/* Right: Tags for selected group (or ungrouped) */}
      <section className="lg:col-span-7 space-y-4">
        <div className="flex items-center justify-between">
          <div className="text-lg font-semibold">
            {selectedGroupId ? 'Tags in selected group' : 'Ungrouped Tags'}
          </div>
          <button className="px-2 py-1 border rounded-md" onClick={startNewTag}>+ New Tag</button>
        </div>

        <div className="rounded-xl border border-neutral-200 dark:border-neutral-800 overflow-auto">
          <table className="min-w-full text-sm">
            <thead className="bg-neutral-100/70 dark:bg-neutral-800/60">
              <tr>
                <th className="text-left p-2">Name</th>
                <th className="text-left p-2">Slug</th>
                <th className="text-left p-2">Parent</th>
                <th className="text-left p-2 w-40">Actions</th>
              </tr>
            </thead>
            <tbody>
              {tagsQ.data?.map(t => (
                <tr key={t.id} className="border-t border-neutral-100 dark:border-neutral-800">
                  <td className="p-2">{t.name}</td>
                  <td className="p-2 font-mono">{t.slug}</td>
                  <td className="p-2">{t.parent_id ? '(nested)' : '—'}</td>
                  <td className="p-2">
                    <div className="flex gap-2">
                      <button className="px-2 py-1 border rounded-md" onClick={() => startEditTag(t)}>Edit</button>
                      <button className="px-2 py-1 border rounded-md" onClick={() => removeTag(t)}>Delete</button>
                    </div>
                  </td>
                </tr>
              ))}
              {!tagsQ.data?.length && (
                <tr><td colSpan={4} className="p-3 text-neutral-500">No tags.</td></tr>
              )}
            </tbody>
          </table>
        </div>

        <div className="rounded-xl border border-neutral-200 dark:border-neutral-800 p-4 space-y-2">
          <div className="text-sm text-neutral-500">{tForm.id ? 'Edit tag' : 'Create tag'}</div>
          <div className="grid grid-cols-2 gap-3">
            <div className="col-span-2">
              <label className="block text-sm mb-1">Name</label>
              <input
                className="w-full rounded-md border px-3 py-1.5 bg-white dark:bg-neutral-900"
                value={tForm.name}
                onChange={e => setTForm(s => ({ ...s, name: e.target.value, slug: s.id ? s.slug : slugify(e.target.value) }))}
                placeholder="e.g. Action, VideoGame, Portrait…"
              />
            </div>
            <div>
              <label className="block text-sm mb-1">Slug</label>
              <input
                className="w-full rounded-md border px-3 py-1.5 bg-white dark:bg-neutral-900 font-mono"
                value={tForm.slug}
                onChange={e => setTForm(s => ({ ...s, slug: e.target.value }))}
              />
            </div>
            <div>
              <label className="block text-sm mb-1">Parent (within group)</label>
              <select
                className="w-full rounded-md border px-3 py-1.5 bg-white dark:bg-neutral-900"
                value={tForm.parent_id ?? ''}
                onChange={e => setTForm(s => ({ ...s, parent_id: e.target.value || null }))}
                disabled={!selectedGroupId}
                title={!selectedGroupId ? 'Parent requires a Tag Group' : undefined}
              >
                <option value="">(none)</option>
                {/* Only allow selecting parent among current group’s tags */}
                {tagsQ.data?.map(t => (
                  <option key={t.id} value={t.id}>{t.name}</option>
                ))}
              </select>
            </div>
            <div className="col-span-2">
              <label className="block text-sm mb-1">Description</label>
              <textarea
                className="w-full rounded-md border px-3 py-1.5 bg-white dark:bg-neutral-900"
                rows={2}
                value={tForm.description ?? ''}
                onChange={e => setTForm(s => ({ ...s, description: e.target.value }))}
              />
            </div>
          </div>
          <div className="flex gap-2">
            <button className="px-3 py-2 rounded-md bg-neutral-900 text-white dark:bg-white dark:text-neutral-900" onClick={submitTag}>
              {tForm.id ? 'Save Tag' : 'Create Tag'}
            </button>
            <button className="px-3 py-2 rounded-md border" onClick={startNewTag}>Reset</button>
          </div>
        </div>
      </section>
    </div>
  )
}
