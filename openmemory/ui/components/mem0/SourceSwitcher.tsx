// SourceSwitcher Component - API源切换组件
import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Separator } from '@/components/ui/separator';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { 
  Settings, 
  Database, 
  Brain, 
  Zap, 
  Shield, 
  AlertTriangle, 
  CheckCircle,
  Info,
  RefreshCw
} from 'lucide-react';
import { cn } from '@/lib/utils';
import type { FeatureFlags } from '@/lib/api-adapter';

export interface SourceSwitcherProps {
  currentSource: 'openmemory' | 'mem0';
  featureFlags: FeatureFlags;
  onUpdateFlags: (flags: Partial<FeatureFlags>) => void;
  onSwitchSource: (source: 'openmemory' | 'mem0') => void;
  isSourceAvailable: (source: 'openmemory' | 'mem0') => boolean;
  className?: string;
  showAdvancedSettings?: boolean;
}

export const SourceSwitcher: React.FC<SourceSwitcherProps> = ({
  currentSource,
  featureFlags,
  onUpdateFlags,
  onSwitchSource,
  isSourceAvailable,
  className,
  showAdvancedSettings = true,
}) => {
  const [isOpen, setIsOpen] = useState(false);

  const openMemoryAvailable = isSourceAvailable('openmemory');
  const mem0Available = isSourceAvailable('mem0');

  const handleSourceSwitch = (source: 'openmemory' | 'mem0') => {
    if (isSourceAvailable(source)) {
      onSwitchSource(source);
      onUpdateFlags({ defaultSource: source });
    }
  };

  const getSourceInfo = (source: 'openmemory' | 'mem0') => {
    if (source === 'openmemory') {
      return {
        name: 'OpenMemory',
        icon: <Database className="h-4 w-4" />,
        description: 'Local memory storage with full control',
        features: ['Local Storage', 'Full Control', 'Privacy First', 'Fast Access'],
        color: 'blue',
      };
    } else {
      return {
        name: 'Mem0',
        icon: <Brain className="h-4 w-4" />,
        description: 'AI-powered memory with advanced features',
        features: ['AI Processing', 'Smart Search', 'Auto Categorization', 'Cloud Sync'],
        color: 'purple',
      };
    }
  };

  const openMemoryInfo = getSourceInfo('openmemory');
  const mem0Info = getSourceInfo('mem0');

  return (
    <div className={cn("flex items-center space-x-2", className)}>
      {/* Quick Source Toggle */}
      <div className="flex items-center space-x-1 border rounded-md p-1">
        <Button
          variant={currentSource === 'openmemory' ? 'default' : 'ghost'}
          size="sm"
          onClick={() => handleSourceSwitch('openmemory')}
          disabled={!openMemoryAvailable}
          className="h-8 px-3"
        >
          <Database className="h-3 w-3 mr-1" />
          OpenMemory
        </Button>
        <Button
          variant={currentSource === 'mem0' ? 'default' : 'ghost'}
          size="sm"
          onClick={() => handleSourceSwitch('mem0')}
          disabled={!mem0Available}
          className="h-8 px-3"
        >
          <Brain className="h-3 w-3 mr-1" />
          Mem0
        </Button>
      </div>

      {/* Status Indicator */}
      <div className="flex items-center space-x-1">
        <div className={cn(
          "h-2 w-2 rounded-full",
          currentSource === 'openmemory' ? "bg-blue-500" : "bg-purple-500"
        )} />
        <span className="text-xs text-muted-foreground">
          {currentSource === 'openmemory' ? 'OpenMemory' : 'Mem0'}
        </span>
      </div>

      {/* Advanced Settings */}
      {showAdvancedSettings && (
        <Popover open={isOpen} onOpenChange={setIsOpen}>
          <PopoverTrigger asChild>
            <Button variant="outline" size="sm" className="h-8 w-8 p-0">
              <Settings className="h-3 w-3" />
            </Button>
          </PopoverTrigger>
          <PopoverContent className="w-96" align="end">
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h4 className="font-medium">API Source Settings</h4>
                <Badge variant="outline" className="text-xs">
                  {currentSource === 'openmemory' ? '💾' : '🧠'} {currentSource}
                </Badge>
              </div>

              <Separator />

              {/* Source Selection */}
              <div className="space-y-3">
                <Label className="text-sm font-medium">Available Sources</Label>
                
                {/* OpenMemory Card */}
                <Card className={cn(
                  "cursor-pointer transition-all",
                  currentSource === 'openmemory' && "ring-2 ring-blue-500",
                  !openMemoryAvailable && "opacity-50"
                )}>
                  <CardHeader 
                    className="pb-2"
                    onClick={() => openMemoryAvailable && handleSourceSwitch('openmemory')}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-2">
                        {openMemoryInfo.icon}
                        <CardTitle className="text-sm">{openMemoryInfo.name}</CardTitle>
                      </div>
                      <div className="flex items-center space-x-2">
                        {openMemoryAvailable ? (
                          <CheckCircle className="h-4 w-4 text-green-500" />
                        ) : (
                          <AlertTriangle className="h-4 w-4 text-red-500" />
                        )}
                        {currentSource === 'openmemory' && (
                          <Badge variant="default" className="text-xs">Active</Badge>
                        )}
                      </div>
                    </div>
                    <CardDescription className="text-xs">
                      {openMemoryInfo.description}
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="pt-0">
                    <div className="flex flex-wrap gap-1">
                      {openMemoryInfo.features.map((feature, index) => (
                        <Badge key={index} variant="secondary" className="text-xs">
                          {feature}
                        </Badge>
                      ))}
                    </div>
                  </CardContent>
                </Card>

                {/* Mem0 Card */}
                <Card className={cn(
                  "cursor-pointer transition-all",
                  currentSource === 'mem0' && "ring-2 ring-purple-500",
                  !mem0Available && "opacity-50"
                )}>
                  <CardHeader 
                    className="pb-2"
                    onClick={() => mem0Available && handleSourceSwitch('mem0')}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-2">
                        {mem0Info.icon}
                        <CardTitle className="text-sm">{mem0Info.name}</CardTitle>
                      </div>
                      <div className="flex items-center space-x-2">
                        {mem0Available ? (
                          <CheckCircle className="h-4 w-4 text-green-500" />
                        ) : (
                          <AlertTriangle className="h-4 w-4 text-red-500" />
                        )}
                        {currentSource === 'mem0' && (
                          <Badge variant="default" className="text-xs">Active</Badge>
                        )}
                      </div>
                    </div>
                    <CardDescription className="text-xs">
                      {mem0Info.description}
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="pt-0">
                    <div className="flex flex-wrap gap-1">
                      {mem0Info.features.map((feature, index) => (
                        <Badge key={index} variant="secondary" className="text-xs">
                          {feature}
                        </Badge>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              </div>

              <Separator />

              {/* Feature Flags */}
              <div className="space-y-3">
                <Label className="text-sm font-medium">Advanced Options</Label>
                
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <Shield className="h-4 w-4" />
                      <Label htmlFor="auto-fallback" className="text-sm">
                        Auto Fallback
                      </Label>
                    </div>
                    <Switch
                      id="auto-fallback"
                      checked={featureFlags.enableAutoFallback}
                      onCheckedChange={(checked) => 
                        onUpdateFlags({ enableAutoFallback: checked })
                      }
                    />
                  </div>
                  <p className="text-xs text-muted-foreground ml-6">
                    Automatically switch to backup source if primary fails
                  </p>
                </div>

                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <Zap className="h-4 w-4" />
                      <Label htmlFor="caching" className="text-sm">
                        Enable Caching
                      </Label>
                    </div>
                    <Switch
                      id="caching"
                      checked={featureFlags.enableCaching}
                      onCheckedChange={(checked) => 
                        onUpdateFlags({ enableCaching: checked })
                      }
                    />
                  </div>
                  <p className="text-xs text-muted-foreground ml-6">
                    Cache API responses for better performance
                  </p>
                </div>

                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <Info className="h-4 w-4" />
                      <Label htmlFor="telemetry" className="text-sm">
                        Telemetry
                      </Label>
                    </div>
                    <Switch
                      id="telemetry"
                      checked={featureFlags.enableTelemetry}
                      onCheckedChange={(checked) => 
                        onUpdateFlags({ enableTelemetry: checked })
                      }
                    />
                  </div>
                  <p className="text-xs text-muted-foreground ml-6">
                    Send usage analytics to improve the service
                  </p>
                </div>
              </div>

              {/* Status Alerts */}
              {!openMemoryAvailable && !mem0Available && (
                <Alert variant="destructive">
                  <AlertTriangle className="h-4 w-4" />
                  <AlertDescription className="text-xs">
                    No API sources are available. Please check your configuration.
                  </AlertDescription>
                </Alert>
              )}

              {featureFlags.enableAutoFallback && (
                <Alert>
                  <Shield className="h-4 w-4" />
                  <AlertDescription className="text-xs">
                    Auto fallback is enabled. Requests will automatically switch to backup source if primary fails.
                  </AlertDescription>
                </Alert>
              )}

              <Separator />

              <div className="flex justify-end space-x-2">
                <Button variant="outline" size="sm" onClick={() => setIsOpen(false)}>
                  Close
                </Button>
                <Button size="sm" onClick={() => {
                  // Trigger a refresh or validation
                  setIsOpen(false);
                }}>
                  <RefreshCw className="h-3 w-3 mr-1" />
                  Apply
                </Button>
              </div>
            </div>
          </PopoverContent>
        </Popover>
      )}
    </div>
  );
};

export default SourceSwitcher;
