import { useApiHealth } from '@/lib/hooks'

export default function HealthDot() {
  const { isFetching, isError } = useApiHealth()

  const color = isError ? 'bg-red-500'
    : isFetching ? 'bg-yellow-400'
    : 'bg-emerald-500'

  const label = isError ? 'API: down'
    : isFetching ? 'API: checking…'
    : 'API: up'

  return (
    <div className="flex items-center gap-2 text-xs text-neutral-600 dark:text-neutral-300" title={label}>
      <span className={`inline-block w-2.5 h-2.5 rounded-full ${color}`} />
      <span className="hidden sm:inline">{label}</span>
    </div>
  )
}
