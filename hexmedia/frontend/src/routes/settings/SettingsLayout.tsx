import { NavLink, Outlet } from 'react-router-dom'

const linkBase =
  'px-3 py-2 rounded-md text-sm font-medium transition-colors hover:bg-neutral-200/60 dark:hover:bg-neutral-800/60'
const active = 'bg-neutral-900 text-white dark:bg-white dark:text-neutral-900'
const inactive = 'text-neutral-700 dark:text-neutral-200'

export default function SettingsLayout() {
  return (
    <div className="space-y-6">
      <div className="text-2xl font-semibold">Settings</div>
      <nav className="flex items-center gap-2">
        <NavLink
          to="/settings/tags"
          className={({ isActive }) => `${linkBase} ${isActive ? active : inactive}`}
        >
          Tags
        </NavLink>
        {/* Add more settings subsections later */}
      </nav>

      <div>
        <Outlet />
      </div>
    </div>
  )
}
