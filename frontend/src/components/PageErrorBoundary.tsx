import { Component, type ErrorInfo, type ReactNode } from 'react'

type PageErrorBoundaryProps = {
  children: ReactNode
  pageName: string
}

type PageErrorBoundaryState = {
  hasError: boolean
  error?: Error
}

export class PageErrorBoundary extends Component<PageErrorBoundaryProps, PageErrorBoundaryState> {
  state: PageErrorBoundaryState = { hasError: false }

  static getDerivedStateFromError(error: Error): PageErrorBoundaryState {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error(`${this.props.pageName} crashed:`, error, info)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: 40, textAlign: 'center' }}>
          <div style={{ fontSize: 32, marginBottom: 16 }}>!</div>
          <h3 style={{ color: '#E8F5F2', marginBottom: 8 }}>{this.props.pageName} encountered an error</h3>
          <p style={{ color: '#8BA89F', marginBottom: 20 }}>{this.state.error?.message}</p>
          <button
            onClick={() => this.setState({ hasError: false })}
            style={{
              background: 'rgba(0,200,150,0.15)',
              border: '1px solid rgba(0,200,150,0.3)',
              color: '#00C896',
              padding: '8px 20px',
              borderRadius: 8,
              cursor: 'pointer',
            }}
          >
            Try again
          </button>
        </div>
      )
    }
    return this.props.children
  }
}
