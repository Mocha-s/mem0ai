// ErrorBoundary Component - 错误边界组件
import React, { Component, ErrorInfo, ReactNode } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { 
  AlertTriangle, 
  RefreshCw, 
  Bug, 
  ChevronDown, 
  ChevronUp, 
  Copy,
  ExternalLink 
} from 'lucide-react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
  showDetails?: boolean;
  showReportButton?: boolean;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
  isDetailsOpen: boolean;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
      isDetailsOpen: false,
    };
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return {
      hasError: true,
      error,
    };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    this.setState({
      error,
      errorInfo,
    });

    // Call the onError callback if provided
    this.props.onError?.(error, errorInfo);

    // Log to console in development
    if (process.env.NODE_ENV === 'development') {
      console.error('ErrorBoundary caught an error:', error, errorInfo);
    }
  }

  handleRetry = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
      isDetailsOpen: false,
    });
  };

  handleCopyError = () => {
    const { error, errorInfo } = this.state;
    const errorText = `
Error: ${error?.message}
Stack: ${error?.stack}
Component Stack: ${errorInfo?.componentStack}
    `.trim();

    navigator.clipboard.writeText(errorText).then(() => {
      // Could show a toast notification here
      console.log('Error details copied to clipboard');
    });
  };

  handleReportError = () => {
    const { error, errorInfo } = this.state;
    const errorData = {
      message: error?.message,
      stack: error?.stack,
      componentStack: errorInfo?.componentStack,
      userAgent: navigator.userAgent,
      url: window.location.href,
      timestamp: new Date().toISOString(),
    };

    // In a real app, you would send this to your error reporting service
    console.log('Error report data:', errorData);
    
    // Example: Send to error reporting service
    // fetch('/api/error-report', {
    //   method: 'POST',
    //   headers: { 'Content-Type': 'application/json' },
    //   body: JSON.stringify(errorData),
    // });
  };

  render() {
    if (this.state.hasError) {
      // Custom fallback UI
      if (this.props.fallback) {
        return this.props.fallback;
      }

      const { error, errorInfo } = this.state;
      const { showDetails = true, showReportButton = true } = this.props;

      return (
        <div className="min-h-[400px] flex items-center justify-center p-4">
          <Card className="w-full max-w-2xl">
            <CardHeader>
              <div className="flex items-center space-x-2">
                <AlertTriangle className="h-5 w-5 text-destructive" />
                <CardTitle className="text-destructive">Something went wrong</CardTitle>
              </div>
              <CardDescription>
                An unexpected error occurred while rendering this component.
              </CardDescription>
            </CardHeader>

            <CardContent className="space-y-4">
              {/* Error Summary */}
              <Alert variant="destructive">
                <Bug className="h-4 w-4" />
                <AlertDescription>
                  <div className="font-medium">{error?.name || 'Error'}</div>
                  <div className="text-sm mt-1">{error?.message || 'Unknown error occurred'}</div>
                </AlertDescription>
              </Alert>

              {/* Error Details */}
              {showDetails && (error?.stack || errorInfo?.componentStack) && (
                <Collapsible 
                  open={this.state.isDetailsOpen} 
                  onOpenChange={(open) => this.setState({ isDetailsOpen: open })}
                >
                  <CollapsibleTrigger asChild>
                    <Button variant="outline" className="w-full justify-between">
                      <span>Error Details</span>
                      {this.state.isDetailsOpen ? (
                        <ChevronUp className="h-4 w-4" />
                      ) : (
                        <ChevronDown className="h-4 w-4" />
                      )}
                    </Button>
                  </CollapsibleTrigger>
                  <CollapsibleContent className="mt-2">
                    <div className="space-y-3">
                      {/* Error Stack */}
                      {error?.stack && (
                        <div>
                          <div className="flex items-center justify-between mb-2">
                            <Badge variant="outline">Error Stack</Badge>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={this.handleCopyError}
                            >
                              <Copy className="h-3 w-3 mr-1" />
                              Copy
                            </Button>
                          </div>
                          <pre className="text-xs bg-muted p-3 rounded-md overflow-auto max-h-40">
                            {error.stack}
                          </pre>
                        </div>
                      )}

                      {/* Component Stack */}
                      {errorInfo?.componentStack && (
                        <div>
                          <Badge variant="outline" className="mb-2">Component Stack</Badge>
                          <pre className="text-xs bg-muted p-3 rounded-md overflow-auto max-h-40">
                            {errorInfo.componentStack}
                          </pre>
                        </div>
                      )}

                      {/* Environment Info */}
                      <div>
                        <Badge variant="outline" className="mb-2">Environment</Badge>
                        <div className="text-xs space-y-1 bg-muted p-3 rounded-md">
                          <div><strong>URL:</strong> {window.location.href}</div>
                          <div><strong>User Agent:</strong> {navigator.userAgent}</div>
                          <div><strong>Timestamp:</strong> {new Date().toISOString()}</div>
                        </div>
                      </div>
                    </div>
                  </CollapsibleContent>
                </Collapsible>
              )}

              {/* Suggestions */}
              <div className="text-sm text-muted-foreground space-y-2">
                <p><strong>What you can try:</strong></p>
                <ul className="list-disc list-inside space-y-1 ml-2">
                  <li>Refresh the page to retry</li>
                  <li>Check your internet connection</li>
                  <li>Clear your browser cache</li>
                  <li>Try again in a few minutes</li>
                </ul>
              </div>
            </CardContent>

            <CardFooter className="flex justify-between">
              <div className="flex space-x-2">
                <Button onClick={this.handleRetry} variant="default">
                  <RefreshCw className="h-4 w-4 mr-2" />
                  Try Again
                </Button>
                
                {showReportButton && (
                  <Button onClick={this.handleReportError} variant="outline">
                    <ExternalLink className="h-4 w-4 mr-2" />
                    Report Issue
                  </Button>
                )}
              </div>

              <Button 
                variant="ghost" 
                onClick={() => window.location.reload()}
                className="text-muted-foreground"
              >
                Reload Page
              </Button>
            </CardFooter>
          </Card>
        </div>
      );
    }

    return this.props.children;
  }
}

// HOC for wrapping components with error boundary
export function withErrorBoundary<P extends object>(
  Component: React.ComponentType<P>,
  errorBoundaryProps?: Omit<Props, 'children'>
) {
  const WrappedComponent = (props: P) => (
    <ErrorBoundary {...errorBoundaryProps}>
      <Component {...props} />
    </ErrorBoundary>
  );

  WrappedComponent.displayName = `withErrorBoundary(${Component.displayName || Component.name})`;
  
  return WrappedComponent;
}

// Hook for error boundary (for functional components)
export function useErrorHandler() {
  return (error: Error, errorInfo?: ErrorInfo) => {
    // In a real app, you might want to throw the error to be caught by an error boundary
    // or send it to an error reporting service
    console.error('Error caught by useErrorHandler:', error, errorInfo);
    
    // You could also trigger a global error state here
    // For example, using a global state management solution
  };
}

export default ErrorBoundary;
