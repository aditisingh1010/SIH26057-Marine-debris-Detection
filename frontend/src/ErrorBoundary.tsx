import { Component, type ErrorInfo, type ReactNode } from 'react'

type Props = { children: ReactNode }
type State = { error: Error | null }

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null }

  static getDerivedStateFromError(error: Error) {
    return { error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error(error, info.componentStack)
  }

  render() {
    if (this.state.error) {
      return (
        <div style={{ padding: '2.5rem', fontFamily: 'var(--sans)', color: 'var(--text)', background: 'var(--bg)', minHeight: '100vh' }}>
          <h1 style={{ fontFamily: 'var(--serif)', fontSize: '1.5rem', fontWeight: 600, color: 'var(--text)', marginBottom: '0.75rem' }}>
            AquaX encountered an issue
          </h1>
          <pre style={{ whiteSpace: 'pre-wrap', fontFamily: 'var(--mono)', fontSize: '12px', background: 'var(--panel)', border: '1px solid var(--border)', padding: '12px', borderRadius: '3px', color: 'var(--text-muted)' }}>
            {this.state.error.message}
          </pre>
          <p>
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => {
                this.setState({ error: null })
                window.location.href = '/'
              }}
              style={{ marginTop: '1rem' }}
            >
              Reload Workstation
            </button>
          </p>
        </div>
      )
    }
    return this.props.children
  }
}
