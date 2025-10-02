import { useMemo } from 'react'
import type { MediaAssetRead } from '@/types'

function fmtBytes(bytes?: number | null) {
  if (!bytes || bytes <= 0) return '—'
  const u = ['B','KB','MB','GB','TB']
  let i = 0
  let n = bytes
  while (n >= 1024 && i < u.length - 1) { n /= 1024; i++ }
  return `${n.toFixed(n >= 10 ? 0 : 1)} ${u[i]}`
}

function fmtDims(w?: number | null, h?: number | null) {
  return w && h ? `${w}×${h}` : '—'
}

export default function AssetsPanel({ assets }: { assets: MediaAssetRead[] }) {
  const ordered = useMemo(() => {
    const order = ['contact','contact_sheet','contactsheet','collage','thumb','proxy','video','image','sidecar','other']
    return [...(assets ?? [])].sort((a,b) => {
      const ai = order.indexOf(a.kind ?? '') ; const bi = order.indexOf(b.kind ?? '')
      return (ai === -1 ? 999 : ai) - (bi === -1 ? 999 : bi)
    })
  }, [assets])

  if (!ordered.length) return null

  const copy = async (url: string) => {
    try {
      await navigator.clipboard.writeText(url)
      // lightweight feedback—replace with a toast if you add one later
      console.info('Copied:', url)
    } catch {
      alert('Could not copy to clipboard.')
    }
  }

  return (
    <div className="space-y-2">
      <div className="text-sm font-semibold">Assets</div>
      <div className="overflow-auto rounded-xl border border-neutral-200 dark:border-neutral-800">
        <table className="min-w-full text-sm">
          <thead className="bg-neutral-50/70 dark:bg-neutral-800/60">
            <tr>
              <th className="text-left p-2">Kind</th>
              <th className="text-left p-2">URL</th>
              <th className="text-left p-2">MIME</th>
              <th className="text-left p-2">Size</th>
              <th className="text-left p-2">Dims</th>
              <th className="text-left p-2"></th>
            </tr>
          </thead>
          <tbody>
            {ordered.map(a => (
              <tr key={a.id} className="border-t border-neutral-100 dark:border-neutral-800">
                <td className="p-2 font-mono">{a.kind ?? '—'}</td>
                <td className="p-2 max-w-[42rem]">
                  <div className="truncate text-blue-600 dark:text-blue-400">
                    <a href={a.url} target="_blank" rel="noreferrer">{a.url}</a>
                  </div>
                </td>
                <td className="p-2">{a.mime ?? '—'}</td>
                <td className="p-2">{fmtBytes(a.bytes)}</td>
                <td className="p-2">{fmtDims(a.width, a.height)}</td>
                <td className="p-2">
                  <div className="flex gap-2">
                    <a
                      className="px-2 py-1 rounded-md border border-neutral-300 dark:border-neutral-700"
                      href={a.url} target="_blank" rel="noreferrer"
                    >
                      Open
                    </a>
                    <button
                      className="px-2 py-1 rounded-md border border-neutral-300 dark:border-neutral-700"
                      onClick={() => a.url && copy(a.url)}
                      disabled={!a.url}
                    >
                      Copy URL
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
