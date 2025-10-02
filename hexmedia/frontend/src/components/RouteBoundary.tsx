import React from 'react'

type Props = { children: React.ReactNode }
type State = { hasError: boolean; error?: unknown }

export default class RouteBoundary extends React.Component<Props, State> {
  state: State = { hasError: false, error: undefined }

  static getDerivedStateFromError(error: unknown) {
    return { hasError: true, error }
  }

  componentDidCatch(error: unknown, info: unknown) {
    // Keep this console so we can see the error if something breaks
    console.error('Route error:', error, info)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="p-6">
          <div className="text-lg font-semibold mb-2">Something went wrong.</div>
          <div className="text-sm text-neutral-500">Check the console for details.</div>
        </div>
      )
    }
    return this.props.children
  }
}
