// EmptyState Component - 空状态组件
import React from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { 
  Brain, 
  Database, 
  Search, 
  Plus, 
  RefreshCw, 
  FileText, 
  Inbox,
  AlertCircle,
  Zap
} from 'lucide-react';
import { cn } from '@/lib/utils';

export interface EmptyStateProps {
  variant?: 'memories' | 'search' | 'error' | 'loading' | 'custom';
  title?: string;
  description?: string;
  icon?: React.ReactNode;
  actions?: Array<{
    label: string;
    onClick: () => void;
    variant?: 'default' | 'outline' | 'secondary';
    icon?: React.ReactNode;
  }>;
  className?: string;
  size?: 'sm' | 'md' | 'lg';
}

const variantConfig = {
  memories: {
    icon: <Brain className="h-12 w-12 text-muted-foreground" />,
    title: 'No memories found',
    description: 'Start creating memories to see them here. Your memories will help you remember important information.',
    defaultActions: [
      {
        label: 'Create Memory',
        variant: 'default' as const,
        icon: <Plus className="h-4 w-4" />,
      },
      {
        label: 'Refresh',
        variant: 'outline' as const,
        icon: <RefreshCw className="h-4 w-4" />,
      },
    ],
  },
  search: {
    icon: <Search className="h-12 w-12 text-muted-foreground" />,
    title: 'No results found',
    description: 'Try adjusting your search terms or filters to find what you\'re looking for.',
    defaultActions: [
      {
        label: 'Clear Filters',
        variant: 'outline' as const,
        icon: <RefreshCw className="h-4 w-4" />,
      },
    ],
  },
  error: {
    icon: <AlertCircle className="h-12 w-12 text-destructive" />,
    title: 'Something went wrong',
    description: 'We encountered an error while loading your data. Please try again.',
    defaultActions: [
      {
        label: 'Try Again',
        variant: 'default' as const,
        icon: <RefreshCw className="h-4 w-4" />,
      },
    ],
  },
  loading: {
    icon: <Zap className="h-12 w-12 text-muted-foreground animate-pulse" />,
    title: 'Loading...',
    description: 'Please wait while we fetch your data.',
    defaultActions: [],
  },
  custom: {
    icon: <Inbox className="h-12 w-12 text-muted-foreground" />,
    title: 'Empty',
    description: 'No content available.',
    defaultActions: [],
  },
};

const sizeConfig = {
  sm: {
    container: 'py-8',
    icon: 'h-8 w-8',
    title: 'text-lg',
    description: 'text-sm',
    spacing: 'space-y-2',
  },
  md: {
    container: 'py-12',
    icon: 'h-12 w-12',
    title: 'text-xl',
    description: 'text-base',
    spacing: 'space-y-4',
  },
  lg: {
    container: 'py-16',
    icon: 'h-16 w-16',
    title: 'text-2xl',
    description: 'text-lg',
    spacing: 'space-y-6',
  },
};

export const EmptyState: React.FC<EmptyStateProps> = ({
  variant = 'custom',
  title,
  description,
  icon,
  actions,
  className,
  size = 'md',
}) => {
  const config = variantConfig[variant];
  const sizeStyles = sizeConfig[size];

  const displayTitle = title || config.title;
  const displayDescription = description || config.description;
  const displayIcon = icon || config.icon;
  const displayActions = actions || config.defaultActions;

  // Clone icon with size class
  const iconWithSize = React.isValidElement(displayIcon)
    ? React.cloneElement(displayIcon, {
        className: cn(sizeStyles.icon, displayIcon.props.className),
      })
    : displayIcon;

  return (
    <div className={cn(
      'flex items-center justify-center w-full',
      sizeStyles.container,
      className
    )}>
      <div className={cn(
        'text-center max-w-md mx-auto',
        sizeStyles.spacing
      )}>
        {/* Icon */}
        <div className="flex justify-center mb-4">
          {iconWithSize}
        </div>

        {/* Title */}
        <h3 className={cn(
          'font-semibold text-foreground',
          sizeStyles.title
        )}>
          {displayTitle}
        </h3>

        {/* Description */}
        {displayDescription && (
          <p className={cn(
            'text-muted-foreground',
            sizeStyles.description
          )}>
            {displayDescription}
          </p>
        )}

        {/* Actions */}
        {displayActions.length > 0 && (
          <div className="flex flex-col sm:flex-row gap-2 justify-center mt-6">
            {displayActions.map((action, index) => (
              <Button
                key={index}
                variant={action.variant || 'default'}
                onClick={action.onClick}
                className="flex items-center"
              >
                {action.icon && (
                  <span className="mr-2">
                    {action.icon}
                  </span>
                )}
                {action.label}
              </Button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

// Specialized empty state components
export const MemoriesEmptyState: React.FC<Omit<EmptyStateProps, 'variant'> & {
  onCreateMemory?: () => void;
  onRefresh?: () => void;
}> = ({ onCreateMemory, onRefresh, ...props }) => {
  const actions = [];
  
  if (onCreateMemory) {
    actions.push({
      label: 'Create Memory',
      onClick: onCreateMemory,
      variant: 'default' as const,
      icon: <Plus className="h-4 w-4" />,
    });
  }
  
  if (onRefresh) {
    actions.push({
      label: 'Refresh',
      onClick: onRefresh,
      variant: 'outline' as const,
      icon: <RefreshCw className="h-4 w-4" />,
    });
  }

  return (
    <EmptyState
      {...props}
      variant="memories"
      actions={actions}
    />
  );
};

export const SearchEmptyState: React.FC<Omit<EmptyStateProps, 'variant'> & {
  onClearFilters?: () => void;
  searchQuery?: string;
}> = ({ onClearFilters, searchQuery, ...props }) => {
  const actions = [];
  
  if (onClearFilters) {
    actions.push({
      label: 'Clear Filters',
      onClick: onClearFilters,
      variant: 'outline' as const,
      icon: <RefreshCw className="h-4 w-4" />,
    });
  }

  const description = searchQuery 
    ? `No results found for "${searchQuery}". Try adjusting your search terms or filters.`
    : 'Try adjusting your search terms or filters to find what you\'re looking for.';

  return (
    <EmptyState
      {...props}
      variant="search"
      description={description}
      actions={actions}
    />
  );
};

export const ErrorEmptyState: React.FC<Omit<EmptyStateProps, 'variant'> & {
  onRetry?: () => void;
  error?: string;
}> = ({ onRetry, error, ...props }) => {
  const actions = [];
  
  if (onRetry) {
    actions.push({
      label: 'Try Again',
      onClick: onRetry,
      variant: 'default' as const,
      icon: <RefreshCw className="h-4 w-4" />,
    });
  }

  const description = error || 'We encountered an error while loading your data. Please try again.';

  return (
    <EmptyState
      {...props}
      variant="error"
      description={description}
      actions={actions}
    />
  );
};

export const LoadingEmptyState: React.FC<Omit<EmptyStateProps, 'variant'> & {
  loadingText?: string;
}> = ({ loadingText, ...props }) => {
  return (
    <EmptyState
      {...props}
      variant="loading"
      title={loadingText || 'Loading...'}
    />
  );
};

export default EmptyState;
