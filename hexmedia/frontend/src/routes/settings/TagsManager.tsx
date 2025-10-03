import { useMemo, useState } from 'react'
import {
  useTagGroups, useTags,
  useCreateTagGroup, useUpdateTagGroup, useDeleteTagGroup,
  useCreateTag, useUpdateTag, useDeleteTag
} from '@/lib/hooks'
import type { TagGroupRead, TagRead } from '@/types'

export default function TagsManager() {
  const groupsQ = useTagGroups()
  const [selectedGroupId, setSelectedGroupId] = useState<string | null>(null)
  const [search, setSearch] = useState('')

  const flatGroups = useMemo(() => (groupsQ.data ?? []), [groupsQ.data])
  const selectedGroup: TagGroupRead | undefined =
    flatGroups.find(g => g.id === selectedGroupId) ?? flatGroups[0]

  const tagsQ = useTags(selectedGroup?.id ?? null, search)

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="text-xl font-semibold">Master Tag Editor</div>
        <NewGroupButton parentId={null} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Groups list */}
        <aside className="lg:col-span-4 space-y-3">
          <div className="rounded-xl border border-neutral-200 dark:border-neutral-800 overflow-hidden">
            <div className="px-3 py-2 bg-neutral-50/60 dark:bg-neutral-800/60 text-sm font-medium">
              Tag Groups
            </div>
            <div className="divide-y divide-neutral-200 dark:divide-neutral-800">
              {flatGroups.map(g => (
                <button
                  key={g.id}
                  onClick={() => setSelectedGroupId(g.id)}
                  className={`w-full text-left px-3 py-2 hover:bg-neutral-50 dark:hover:bg-neutral-800 ${
                    (selectedGroup?.id === g.id) ? 'bg-neutral-100/70 dark:bg-neutral-800/50' : ''
                  }`}
                >
                  <div className="font-medium">{g.display_name}</div>
                  <div className="text-xs text-neutral-500">{g.key} • {g.cardinality}</div>
                </button>
              ))}
              {!flatGroups.length && <div className="p-3 text-sm text-neutral-500">No groups yet.</div>}
            </div>
          </div>

          {selectedGroup && (
            <GroupEditor group={selectedGroup} />
          )}
        </aside>

        {/* Tags table */}
        <section className="lg:col-span-8 space-y-3">
          <div className="flex items-center justify-between">
            <div className="text-sm text-neutral-500">
              {selectedGroup ? <>Group: <span className="font-medium">{selectedGroup.display_name}</span></> : 'All Tags'}
            </div>
            <div className="flex items-center gap-2">
              <input
                value={search}
                onChange={e => setSearch(e.target.value)}
                placeholder="Search tags…"
                className="px-3 py-1.5 rounded-md border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-900"
              />
              {selectedGroup && <NewTagInline groupId={selectedGroup.id} />}
            </div>
          </div>

          <div className="overflow-auto rounded-xl border border-neutral-200 dark:border-neutral-800">
            <table className="min-w-full text-sm">
              <thead className="bg-neutral-100/70 dark:bg-neutral-800/60">
                <tr>
                  <th className="text-left p-2">Name</th>
                  <th className="text-left p-2">Slug</th>
                  <th className="text-left p-2">Parent</th>
                  <th className="text-left p-2">Description</th>
                  <th className="text-left p-2"></th>
                </tr>
              </thead>
              <tbody>
                {tagsQ.data?.map(tag => (
                  <TagRow key={tag.id} tag={tag} />
                ))}
                {!tagsQ.data?.length && (
                  <tr><td className="p-3 text-neutral-500" colSpan={5}>No tags found.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </div>
  )
}

function GroupEditor({ group }: { group
