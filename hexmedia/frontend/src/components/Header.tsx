import { NavLink } from 'react-router-dom'
import HealthDot from '@/components/HealthDot'


const linkBase =
  'px-3 py-2 rounded-md text-sm font-medium transition-colors hover:bg-neutral-200/60 dark:hover:bg-neutral-800/60'
const active =
  'bg-neutral-900 text-white dark:bg-white dark:text-neutral-900'
const inactive =
  'text-neutral-700 dark:text-neutral-200'

// Reusable className helper for NavLink
const navClass = ({ isActive }: { isActive: boolean }) =>
  `${linkBase} ${isActive ? active : inactive}`

export default function Header() {
  return (
    <header className="border-b border-neutral-200 dark:border-neutral-800 bg-white/75 dark:bg-neutral-900/75 backdrop-blur">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-14 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="font-semibold">Hexmedia</div>
          <nav className="flex items-center gap-1">
            <NavLink to="/buckets" className={navClass}>
              Buckets
            </NavLink>
            <NavLink to="/tools/ingest" className={navClass}>
              Ingest
            </NavLink>
            <NavLink to="/tools/thumbs" className={navClass}>
              Thumbs
            </NavLink>
          </nav>
        </div>

        {/* RIGHT SIDE */}
        <div className="flex items-center gap-3">
          <HealthDot />
        </div>
      </div>
    </header>
  )
}
