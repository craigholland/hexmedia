// src/components/RouteBoundary.tsx
import { ErrorBoundary } from 'react-error-boundary'
import { useLocation } from 'react-router-dom'

function Fallback({ error }: { error: any }) {
  return (
    <div className="rounded-lg border border-red-300 bg-red-50 text-red-900 p-3">
      <div className="font-semibold mb-1">Route error</div>
      <div className="text-sm">
        {error?.message ? error.message : 'Unknown error'}
      </div>
      {error?.stack && (
        <pre className="mt-2 p-2 text-xs whitespace-pre-wrap bg-white/60 rounded border border-red-200 overflow-auto">
          {String(error.stack)}
        </pre>
      )}
      <div className="text-xs text-red-700 mt-2">
        Check the browser console for more details.
      </div>
    </div>
  )
}

export default function RouteBoundary({ children }: { children: React.ReactNode }) {
  // Keying by pathname ensures the boundary resets on each navigation.
  const { pathname } = useLocation()
  return (
    <ErrorBoundary key={pathname} FallbackComponent={Fallback}>
      {children}
    </ErrorBoundary>
  )
}
