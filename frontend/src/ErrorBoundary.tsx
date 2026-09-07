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
        <div style={{ padding: '2rem', fontFamily: 'Georgia, serif', color: '#1c1917' }}>
          <h1 style={{ fontSize: '1.4rem' }}>Sonar Aqua hit an error</h1>
          <pre style={{ whiteSpace: 'pre-wrap' }}>{this.state.error.message}</pre>
          <p>
            <button
              type="button"
              onClick={() => {
                this.setState({ error: null })
                window.location.href = '/'
              }}
              style={{ marginTop: '1rem', padding: '8px 14px', cursor: 'pointer' }}
            >
              Reload Detect
            </button>
          </p>
        </div>
      )
    }
    return this.props.children
  }
}
