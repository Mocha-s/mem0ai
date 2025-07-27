// MemoryCard Component - 记忆展示卡片
import React from 'react';
import { Card, CardContent, CardFooter, CardHeader } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import { Edit, Trash2, MoreVertical, Clock, User, Tag, ExternalLink } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { UnifiedMemory } from '@/lib/types/unified';

export interface MemoryCardProps {
  memory: UnifiedMemory;
  onEdit?: (id: string) => void;
  onDelete?: (id: string) => void;
  onView?: (id: string) => void;
  className?: string;
  compact?: boolean;
  showActions?: boolean;
  showMetadata?: boolean;
}

export const MemoryCard: React.FC<MemoryCardProps> = ({
  memory,
  onEdit,
  onDelete,
  onView,
  className,
  compact = false,
  showActions = true,
  showMetadata = true,
}) => {
  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const getSourceIcon = (source?: string) => {
    switch (source) {
      case 'mem0':
        return '🧠';
      case 'openmemory':
        return '💾';
      default:
        return '📝';
    }
  };

  const getClientIcon = (client?: string) => {
    switch (client) {
      case 'chrome':
        return '🌐';
      case 'chatgpt':
        return '🤖';
      case 'cursor':
        return '⚡';
      case 'terminal':
        return '💻';
      case 'api':
        return '🔌';
      default:
        return '📱';
    }
  };

  const truncateContent = (content: string, maxLength: number = 150) => {
    if (content.length <= maxLength) return content;
    return content.slice(0, maxLength) + '...';
  };

  return (
    <Card className={cn(
      'transition-all duration-200 hover:shadow-md',
      compact ? 'p-3' : 'p-4',
      className
    )}>
      <CardHeader className={cn('pb-3', compact && 'pb-2')}>
        <div className="flex items-start justify-between">
          <div className="flex items-center space-x-2">
            <Avatar className="h-8 w-8">
              <AvatarFallback className="text-xs">
                {getSourceIcon()}
              </AvatarFallback>
            </Avatar>
            <div className="flex-1 min-w-0">
              <div className="flex items-center space-x-2">
                <span className="text-xs text-muted-foreground">
                  {getClientIcon(memory.client)} {memory.client || 'unknown'}
                </span>
                {memory.app_name && (
                  <Badge variant="outline" className="text-xs">
                    {memory.app_name}
                  </Badge>
                )}
              </div>
            </div>
          </div>
          
          {showActions && (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                  <MoreVertical className="h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                {onView && (
                  <DropdownMenuItem onClick={() => onView(memory.id)}>
                    <ExternalLink className="mr-2 h-4 w-4" />
                    View Details
                  </DropdownMenuItem>
                )}
                {onEdit && (
                  <DropdownMenuItem onClick={() => onEdit(memory.id)}>
                    <Edit className="mr-2 h-4 w-4" />
                    Edit
                  </DropdownMenuItem>
                )}
                {onDelete && (
                  <DropdownMenuItem 
                    onClick={() => onDelete(memory.id)}
                    className="text-destructive"
                  >
                    <Trash2 className="mr-2 h-4 w-4" />
                    Delete
                  </DropdownMenuItem>
                )}
              </DropdownMenuContent>
            </DropdownMenu>
          )}
        </div>
      </CardHeader>

      <CardContent className={cn('pb-3', compact && 'pb-2')}>
        <div className="space-y-3">
          {/* Memory Content */}
          <div className="text-sm leading-relaxed">
            {compact ? truncateContent(memory.content, 100) : memory.content}
          </div>

          {/* Categories */}
          {memory.categories && memory.categories.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {memory.categories.slice(0, compact ? 2 : 5).map((category, index) => (
                <Badge key={index} variant="secondary" className="text-xs">
                  <Tag className="mr-1 h-3 w-3" />
                  {category}
                </Badge>
              ))}
              {memory.categories.length > (compact ? 2 : 5) && (
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger>
                      <Badge variant="outline" className="text-xs">
                        +{memory.categories.length - (compact ? 2 : 5)}
                      </Badge>
                    </TooltipTrigger>
                    <TooltipContent>
                      <div className="space-y-1">
                        {memory.categories.slice(compact ? 2 : 5).map((category, index) => (
                          <div key={index} className="text-xs">{category}</div>
                        ))}
                      </div>
                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>
              )}
            </div>
          )}

          {/* Metadata */}
          {showMetadata && !compact && (
            <div className="grid grid-cols-2 gap-2 text-xs text-muted-foreground">
              {memory.user_id && (
                <div className="flex items-center space-x-1">
                  <User className="h-3 w-3" />
                  <span>User: {memory.user_id}</span>
                </div>
              )}
              {memory.score && (
                <div className="flex items-center space-x-1">
                  <span>Score: {(memory.score * 100).toFixed(1)}%</span>
                </div>
              )}
              {memory.agent_id && (
                <div className="flex items-center space-x-1">
                  <span>Agent: {memory.agent_id}</span>
                </div>
              )}
              {memory.memory_type && (
                <div className="flex items-center space-x-1">
                  <span>Type: {memory.memory_type}</span>
                </div>
              )}
            </div>
          )}
        </div>
      </CardContent>

      <CardFooter className={cn('pt-3 border-t', compact && 'pt-2')}>
        <div className="flex items-center justify-between w-full text-xs text-muted-foreground">
          <div className="flex items-center space-x-1">
            <Clock className="h-3 w-3" />
            <span>{formatDate(memory.created_at)}</span>
          </div>
          
          {memory.state && (
            <Badge 
              variant={memory.state === 'active' ? 'default' : 'secondary'}
              className="text-xs"
            >
              {memory.state}
            </Badge>
          )}
        </div>
      </CardFooter>
    </Card>
  );
};

export default MemoryCard;
