import { Component, ErrorInfo, ReactNode } from "react";

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

/**
 * ErrorBoundary catches rendering errors that would otherwise produce a blank
 * white screen. When a child component throws during render, this boundary
 * shows a user-friendly error message with the stack trace (in development)
 * instead of leaving the page blank.
 *
 * This is especially important for SPA route transitions (e.g. navigating to
 * /runs/:id after starting an analysis) where a crash in the target page
 * component would otherwise show nothing.
 */
export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    console.error("ErrorBoundary caught an error:", error, errorInfo);
    this.setState({ errorInfo });
  }

  handleReload = (): void => {
    window.location.href = "/";
  };

  render(): ReactNode {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen p-8 flex items-center justify-center bg-gray-50">
          <div className="max-w-2xl w-full glass-card p-8">
            <div className="text-center mb-6">
              <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-red-100 flex items-center justify-center">
                <span className="text-3xl">⚠️</span>
              </div>
              <h1 className="text-2xl font-bold text-gray-800 mb-2">页面渲染出错</h1>
              <p className="text-gray-500">
                页面在渲染过程中遇到了错误。这不影响后端数据，请尝试刷新或返回首页。
              </p>
            </div>

            {this.state.error && (
              <div className="p-4 rounded-xl bg-red-50 mb-4">
                <p className="text-sm font-medium text-red-700 mb-1">
                  {this.state.error.name}: {this.state.error.message}
                </p>
                {this.state.errorInfo?.componentStack && (
                  <pre className="text-xs text-red-600 mt-2 overflow-auto max-h-48 whitespace-pre-wrap">
                    {this.state.errorInfo.componentStack}
                  </pre>
                )}
              </div>
            )}

            <div className="flex gap-3 justify-center">
              <button
                onClick={() => window.location.reload()}
                className="px-6 py-2 rounded-xl bg-gray-100 text-gray-700 hover:bg-gray-200 transition-colors"
              >
                刷新页面
              </button>
              <button
                onClick={this.handleReload}
                className="gradient-btn px-6 py-2"
              >
                返回首页
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
