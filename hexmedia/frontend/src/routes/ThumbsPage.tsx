import { useState } from 'react'
import { useThumbPlan, useThumbRun } from '@/lib/hooks'
import { useToasts } from '@/providers/ToastProvider'

export default function ThumbsPage() {
  const [limit, setLimit] = useState(20)
  const [missing, setMissing] = useState<'either' | 'both'>('either')
  const [regen, setRegen] = useState(false)
  const [includeMissing, setIncludeMissing] = useState(true)

  const planQ = useThumbPlan(limit, missing)
  const runM = useThumbRun()
  const { success, error } = useToasts()

  const onRun = () => {
    runM.mutate(
      {
        limit,
        regenerate: regen,
        include_missing: includeMissing,
        upscale_policy: 'if_smaller_than'
      },
      {
        onSuccess: (d: any) => success(`Thumbs complete: Generated ${d?.generated_count ?? 0} • Skipped ${d?.skipped_count ?? 0}`),
        onError: () => error('Thumbnail job failed'),
      }
    )
  }

  const onRefreshPlan = () =>
    planQ.refetch({ throwOnError: true })
      .then(() => success('Plan refreshed'))
      .catch(() => error('Failed to refresh plan'))

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4 items-end">
        <div>
          <label className="block text-sm text-neutral-600 mb-1">Plan limit</label>
          <input
            type="number"
            value={limit}
            min={1}
            className="rounded-md border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-900 px-3 py-1.5 w-28"
            onChange={e => setLimit(parseInt(e.target.value || '1', 10))}
          />
        </div>
        <div>
          <label className="block text-sm text-neutral-600 mb-1">Missing condition</label>
          <select
            value={missing}
            onChange={e => setMissing(e.target.value as 'either' | 'both')}
            className="rounded-md border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-900 px-3 py-1.5"
          >
            <option value="either">Either thumb/collage missing</option>
            <option value="both">Both missing</option>
          </select>
        </div>
        <label className="inline-flex items-center gap-2">
          <input type="checkbox" checked={regen} onChange={e => setRegen(e.target.checked)} />
          <span>Regenerate existing</span>
        </label>
        <label className="inline-flex items-center gap-2">
          <input type="checkbox" checked={includeMissing} onChange={e => setIncludeMissing(e.target.checked)} />
          <span>Include items missing outputs</span>
        </label>
      </div>

      <div className="flex gap-3">
        <button
          className="px-3 py-2 rounded-md bg-neutral-900 text-white dark:bg-white dark:text-neutral-900 disabled:opacity-50"
          onClick={onRefreshPlan}
          disabled={planQ.isFetching}
        >
          {planQ.isFetching ? 'Planning…' : 'Refresh Plan'}
        </button>
        <button
          className="px-3 py-2 rounded-md bg-indigo-600 text-white disabled:opacity-50"
          onClick={onRun}
          disabled={runM.isPending}
        >
          {runM.isPending ? 'Running…' : 'Run Thumbs'}
        </button>
      </div>

      <div className="overflow-auto rounded-xl border border-neutral-200 dark:border-neutral-800">
        <table className="min-w-full text-sm">
          <thead className="bg-neutral-100/70 dark:bg-neutral-800/60">
            <tr>
              <th className="text-left p-2">Identity</th>
              <th className="text-left p-2">Thumb?</th>
              <th className="text-left p-2">Collage?</th>
            </tr>
          </thead>
          <tbody>
            {planQ.data?.map((row, i) => (
              <tr key={i} className="border-t border-neutral-100 dark:border-neutral-800">
                <td className="p-2">
                  {row.identity.media_folder}/{row.identity.identity_name}.{row.identity.video_ext}
                </td>
                <td className="p-2">{row.thumb_exists ? '✅' : '—'}</td>
                <td className="p-2">{row.collage_exists ? '✅' : '—'}</td>
              </tr>
            ))}
            {!planQ.data?.length && (
              <tr><td className="p-3 text-neutral-500" colSpan={3}>No items in plan.</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {runM.data && (
        <div className="rounded-lg border border-green-300 bg-green-50 text-green-900 p-3">
          <div className="font-semibold mb-1">Thumbs job complete</div>
          <div className="text-sm">
            Generated: {runM.data.generated_count} • Skipped: {runM.data.skipped_count}
          </div>
        </div>
      )}
      {runM.error && (
        <div className="rounded-lg border border-red-300 bg-red-50 text-red-900 p-3">
          Thumbnail job failed.
        </div>
      )}
    </div>
  )
}
