// LoadingSpinner Component - 通用加载组件
import React from 'react';
import { Loader2, Brain, Database, Zap, RefreshCw } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg' | 'xl';
  variant?: 'default' | 'brain' | 'database' | 'zap' | 'refresh';
  className?: string;
  text?: string;
  fullScreen?: boolean;
}

const sizeClasses = {
  sm: 'h-4 w-4',
  md: 'h-6 w-6',
  lg: 'h-8 w-8',
  xl: 'h-12 w-12',
};

const textSizeClasses = {
  sm: 'text-sm',
  md: 'text-base',
  lg: 'text-lg',
  xl: 'text-xl',
};

export const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({
  size = 'md',
  variant = 'default',
  className,
  text,
  fullScreen = false,
}) => {
  const getIcon = () => {
    const iconClass = cn('animate-spin', sizeClasses[size]);
    
    switch (variant) {
      case 'brain':
        return <Brain className={iconClass} />;
      case 'database':
        return <Database className={iconClass} />;
      case 'zap':
        return <Zap className={iconClass} />;
      case 'refresh':
        return <RefreshCw className={iconClass} />;
      default:
        return <Loader2 className={iconClass} />;
    }
  };

  const content = (
    <div className={cn(
      'flex flex-col items-center justify-center space-y-2',
      className
    )}>
      {getIcon()}
      {text && (
        <p className={cn(
          'text-muted-foreground animate-pulse',
          textSizeClasses[size]
        )}>
          {text}
        </p>
      )}
    </div>
  );

  if (fullScreen) {
    return (
      <div className="fixed inset-0 bg-background/80 backdrop-blur-sm z-50 flex items-center justify-center">
        {content}
      </div>
    );
  }

  return content;
};

// Specialized loading components
export const MemoryLoadingSpinner: React.FC<Omit<LoadingSpinnerProps, 'variant'>> = (props) => (
  <LoadingSpinner {...props} variant="brain" text="Loading memories..." />
);

export const DatabaseLoadingSpinner: React.FC<Omit<LoadingSpinnerProps, 'variant'>> = (props) => (
  <LoadingSpinner {...props} variant="database" text="Connecting to database..." />
);

export const SearchLoadingSpinner: React.FC<Omit<LoadingSpinnerProps, 'variant'>> = (props) => (
  <LoadingSpinner {...props} variant="zap" text="Searching..." />
);

export const RefreshLoadingSpinner: React.FC<Omit<LoadingSpinnerProps, 'variant'>> = (props) => (
  <LoadingSpinner {...props} variant="refresh" text="Refreshing..." />
);

export default LoadingSpinner;
