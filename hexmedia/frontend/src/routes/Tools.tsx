import { useState } from 'react'
import { useIngestPlan, useIngestRun, useThumbPlan, useThumbRun } from '@/lib/hooks'

export default function Tools() {
  const [limit, setLimit] = useState(10)
  const { data: plan } = useIngestPlan(limit)
  const runIngest = useIngestRun()

  const { data: tplan } = useThumbPlan(10, 'either')
  const runThumbs = useThumbRun()

  return (
    <div className="space-y-8">
      <section>
        <h2 className="text-lg font-semibold mb-2">Ingest</h2>
        <div className="flex items-center gap-3">
          <label className="text-sm">Limit</label>
          <input value={limit} onChange={e => setLimit(parseInt(e.target.value||'0')||0)} type="number" min={1} className="bg-neutral-900 border border-neutral-800 rounded px-2 py-1 w-24"/>
          <button className="px-3 py-1 rounded bg-blue-600 hover:bg-blue-500" onClick={() => runIngest.mutate({ files: [], limit })}>
            Run
          </button>
        </div>
        <div className="text-xs text-neutral-400 mt-2">{plan?.length ?? 0} planned</div>
        {runIngest.data && (
          <div className="text-xs text-neutral-300 mt-2">
            moved: {runIngest.data.moved} • copied: {runIngest.data.copied} • skipped: {runIngest.data.skipped} • errors: {runIngest.data.errors}
          </div>
        )}
      </section>

      <section>
        <h2 className="text-lg font-semibold mb-2">Thumbnails</h2>
        <div className="flex items-center gap-3">
          <button className="px-3 py-1 rounded bg-emerald-600 hover:bg-emerald-500" onClick={() => runThumbs.mutate({ limit: 10, regenerate: false, include_missing: false })}>
            Generate (limit 10)
          </button>
          <div className="text-xs text-neutral-400">{tplan?.length ?? 0} candidates</div>
        </div>
        {runThumbs.data && (
          <div className="text-xs text-neutral-300 mt-2">
            generated: {runThumbs.data.generated} • updated: {runThumbs.data.updated} • skipped: {runThumbs.data.skipped} • errors: {runThumbs.data.errors}
          </div>
        )}
      </section>
    </div>
  )
}
