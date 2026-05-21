import { Component, type ErrorInfo, type ReactNode } from "react";

interface Props {
  children: ReactNode;
  label?: string;
}

interface State {
  hasError: boolean;
}

/** Catches render errors in a subtree so one broken panel can't blank the UI. */
export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(): State {
    return { hasError: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error("GLOBEYE UI error:", error, info.componentStack);
  }

  render(): ReactNode {
    if (!this.state.hasError) {
      return this.props.children;
    }
    return (
      <div
        role="alert"
        className="rounded-xl border border-red-300 bg-red-50 p-5 text-sm text-red-700 dark:border-red-800 dark:bg-red-950/40 dark:text-red-300"
      >
        <p className="mb-2 font-medium">
          Something went wrong rendering {this.props.label ?? "this section"}.
        </p>
        <button
          type="button"
          onClick={() => window.location.reload()}
          className="rounded-lg border border-red-400 px-3 py-1.5 hover:bg-red-100 dark:hover:bg-red-900/40"
        >
          Reload
        </button>
      </div>
    );
  }
}
