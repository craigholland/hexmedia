import { useIngestPlan, useIngestRun } from '@/lib/hooks'
import { useMemo, useState } from 'react'
import { useToasts } from '@/providers/ToastProvider'

export default function IngestPage() {
  const [limit, setLimit] = useState(10)
  const planQ = useIngestPlan(limit)
  const runM  = useIngestRun()
  const { success, error } = useToasts()

  const files = useMemo(() => {
    const rows = planQ.data ?? []
    // prefer source_path; fall back to path (defensive)
    return rows
      .map((r: any) => r?.source_path ?? r?.path)
      .filter((p: unknown): p is string => typeof p === 'string' && p.length > 0)
  }, [planQ.data])

  const onPlanRefresh = () =>
    planQ.refetch({ throwOnError: true })
      .then(() => success('Plan refreshed'))
      .catch(() => error('Failed to refresh plan'))

  const onRun = () => {
    if (!files.length) return
    runM.mutate(
      { files, limit },
      {
        onSuccess: (d: any) => success(`Ingest complete: Created ${d?.created_count ?? 0} • Skipped ${d?.skipped_count ?? 0}`),
        onError: () => error('Ingest failed'),
      }
    )
  }

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold">Ingest</h1>

      <div className="flex items-end gap-3">
        <div>
          <label className="block text-sm text-neutral-600 mb-1">Plan limit</label>
          <input
            type="number"
            min={1}
            value={limit}
            onChange={e => setLimit(Math.max(1, parseInt(e.target.value || '1', 10)))}
            className="rounded-md border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-900 px-3 py-1.5 w-28"
          />
        </div>

        <button
          className="px-3 py-2 rounded-md bg-neutral-900 text-white dark:bg-white dark:text-neutral-900 disabled:opacity-50"
          onClick={onPlanRefresh}
          disabled={planQ.isFetching}
        >
          {planQ.isFetching ? 'Planning…' : 'Refresh Plan'}
        </button>

        <button
          className="px-3 py-2 rounded-md bg-indigo-600 text-white disabled:opacity-50"
          onClick={onRun}
          disabled={!files.length || runM.isPending}
        >
          {runM.isPending ? 'Running…' : `Run Ingest (${files.length})`}
        </button>
      </div>

      {/* States */}
      {planQ.isLoading && <div>Loading plan…</div>}
      {planQ.error && <div className="text-red-600">Failed to load ingest plan.</div>}

      {!!planQ.data?.length && (
        <div className="overflow-auto rounded-xl border border-neutral-200 dark:border-neutral-800">
          <table className="min-w-full text-sm">
            <thead className="bg-neutral-100/70 dark:bg-neutral-800/60">
              <tr>
                <th className="text-left p-2">#</th>
                <th className="text-left p-2">Source</th>
                <th className="text-left p-2">Dest Folder</th>
                <th className="text-left p-2">Identity</th>
                <th className="text-left p-2">Video Ext</th>
              </tr>
            </thead>
            <tbody>
              {planQ.data.map((row: any, i: number) => (
                <tr key={(row.source_path ?? row.path ?? i) as string} className="border-t border-neutral-100 dark:border-neutral-800">
                  <td className="p-2 w-12 text-neutral-500">{i + 1}</td>
                  <td className="p-2 font-mono text-xs">{row.source_path ?? row.path ?? '—'}</td>
                  <td className="p-2">{row.identity?.media_folder ?? '—'}</td>
                  <td className="p-2">{row.identity?.identity_name ?? '—'}</td>
                  <td className="p-2">{row.identity?.video_ext ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {!planQ.isLoading && !planQ.error && !(planQ.data?.length) && (
        <div className="p-3 text-neutral-500">No items in plan.</div>
      )}

      {/* Results */}
      {runM.data && (
        <div className="rounded-lg border border-green-300 bg-green-50 text-green-900 p-3 space-y-2">
          <div className="font-semibold">Ingest complete</div>
          <div className="text-sm">
            Created: {runM.data.created_count ?? 0} • Skipped: {runM.data.skipped_count ?? 0}
          </div>

          {!!(runM.data.imported?.length) && (
            <div className="text-sm">
              <div className="font-medium mb-1">Imported</div>
              <ul className="list-disc ml-5 space-y-0.5">
                {runM.data.imported.slice(0, 15).map((p: string, i: number) => (
                  <li key={i} className="font-mono text-xs">{p}</li>
                ))}
                {runM.data.imported.length > 15 && (
                  <li className="text-xs text-neutral-600">…and {runM.data.imported.length - 15} more</li>
                )}
              </ul>
            </div>
          )}

          {!!(runM.data.skipped?.length) && (
            <div className="text-sm">
              <div className="font-medium mb-1">Skipped</div>
              <ul className="list-disc ml-5 space-y-0.5">
                {runM.data.skipped.slice(0, 10).map((p: string, i: number) => (
                  <li key={i} className="font-mono text-xs">{p}</li>
                ))}
                {runM.data.skipped.length > 10 && (
                  <li className="text-xs text-neutral-600">…and {runM.data.skipped.length - 10} more</li>
                )}
              </ul>
            </div>
          )}
        </div>
      )}

      {runM.error && (
        <div className="rounded-lg border border-red-300 bg-red-50 text-red-900 p-3">
          Ingest failed.
        </div>
      )}
    </div>
  )
}
