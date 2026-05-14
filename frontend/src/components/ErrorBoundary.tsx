import { Component, type ErrorInfo, type ReactNode } from "react";

interface Props {
  children: ReactNode;
}

interface State {
  error: Error | null;
}

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    // eslint-disable-next-line no-console
    console.error("[ErrorBoundary]", error, info.componentStack);
  }

  reset = () => this.setState({ error: null });

  render() {
    if (!this.state.error) return this.props.children;
    return (
      <div className="min-h-screen flex items-center justify-center bg-dishhome-mist p-6">
        <div className="max-w-md rounded-2xl bg-white border border-black/5 shadow-sm p-8">
          <div className="text-xs uppercase tracking-widest text-rose-600 font-semibold">
            Application error
          </div>
          <h1 className="text-xl font-semibold text-dishhome-blue mt-1">
            Something went wrong
          </h1>
          <p className="text-sm text-dishhome-ink/70 mt-2">
            The portal hit an unexpected error and could not continue rendering
            this page. Your data is safe.
          </p>
          <pre className="mt-4 text-xs font-mono bg-rose-50 border border-rose-200 text-rose-700 p-3 rounded-md overflow-auto max-h-40">
            {this.state.error.message}
          </pre>
          <div className="mt-5 flex gap-2">
            <button
              onClick={this.reset}
              className="rounded-lg bg-dishhome-blue text-white px-4 py-2 text-sm hover:bg-dishhome-blue/90"
            >
              Try again
            </button>
            <button
              onClick={() => window.location.reload()}
              className="rounded-lg bg-white text-dishhome-blue border border-dishhome-blue/20 px-4 py-2 text-sm hover:bg-dishhome-blue/5"
            >
              Reload portal
            </button>
          </div>
        </div>
      </div>
    );
  }
}
