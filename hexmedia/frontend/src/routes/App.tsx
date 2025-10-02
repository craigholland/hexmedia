import { NavLink, Outlet } from 'react-router-dom'

export default function App() {
  return (
    <div className="min-h-screen">
      <header className="border-b border-neutral-800 sticky top-0 z-10 bg-neutral-950/80 backdrop-blur">
        <div className="max-w-6xl mx-auto px-4 py-3 flex items-center gap-6">
          <div className="font-semibold">HexMedia</div>
          <nav className="text-sm flex gap-4">
            <NavLink to="/" className={({isActive}) => isActive ? 'text-white' : 'text-neutral-400 hover:text-white'}>Buckets</NavLink>
            <NavLink to="/tools" className={({isActive}) => isActive ? 'text-white' : 'text-neutral-400 hover:text-white'}>Tools</NavLink>
          </nav>
          <div className="ml-auto text-xs text-neutral-500">API: {import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api'}</div>
        </div>
      </header>
      <main className="max-w-6xl mx-auto px-4 py-6">
        <Outlet />
      </main>
    </div>
  )
}
