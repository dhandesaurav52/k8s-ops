import React, { Component, ErrorInfo, ReactNode } from 'react';
import { AlertTriangle, RefreshCw, Terminal } from 'lucide-react';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

export class ErrorBoundary extends React.Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
    errorInfo: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error, errorInfo: null };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('SkyOps UI Error Boundary caught an error:', error, errorInfo);
    this.setState({ error, errorInfo });
  }

  private handleReload = () => {
    window.location.reload();
  };

  public render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-neutral-950 text-neutral-100 font-mono p-6 flex items-center justify-center select-none">
          <div className="max-w-2xl w-full bg-neutral-900 border border-red-900/80 rounded-lg shadow-2xl p-6 space-y-4">
            <div className="flex items-center gap-3 border-b border-neutral-800 pb-4">
              <div className="w-9 h-9 rounded bg-red-950/80 border border-red-800 flex items-center justify-center text-red-400 shrink-0">
                <AlertTriangle className="w-5 h-5 animate-pulse" />
              </div>
              <div>
                <div className="text-base font-bold text-red-200">SkyOps Console UI Exception</div>
                <div className="text-xs text-neutral-400">
                  A React runtime error occurred during application rendering
                </div>
              </div>
            </div>

            <div className="bg-neutral-950 border border-neutral-800 rounded p-3 text-xs text-red-300 overflow-x-auto space-y-1">
              <div className="font-bold text-red-400">{this.state.error?.name}: {this.state.error?.message}</div>
              {this.state.errorInfo?.componentStack && (
                <pre className="text-[10px] text-neutral-500 whitespace-pre-wrap mt-2">
                  {this.state.errorInfo.componentStack}
                </pre>
              )}
            </div>

            <div className="flex items-center justify-between pt-2">
              <div className="text-[11px] text-neutral-500 flex items-center gap-1.5">
                <Terminal className="w-3.5 h-3.5 text-cyan-500" />
                <span>SkyOps Control Plane v1.0.0</span>
              </div>
              <button
                onClick={this.handleReload}
                className="px-4 py-2 bg-cyan-950 hover:bg-cyan-900 border border-cyan-800 rounded text-cyan-300 text-xs font-bold flex items-center gap-2 transition-colors cursor-pointer"
              >
                <RefreshCw className="w-3.5 h-3.5 text-cyan-400" />
                <span>Reload Console</span>
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
