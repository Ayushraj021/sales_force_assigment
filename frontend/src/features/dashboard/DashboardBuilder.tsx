/**
 * Dashboard Builder Component
 *
 * Drag-and-drop dashboard builder with grid layout.
 */

import * as React from 'react';
import GridLayout, { Layout, WidthProvider } from 'react-grid-layout';
import {
  DndContext,
  DragEndEvent,
  DragOverlay,
  DragStartEvent,
  useSensor,
  useSensors,
  PointerSensor,
} from '@dnd-kit/core';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Plus,
  Trash2,
  Settings,
  Maximize2,
  Minimize2,
  BarChart2,
  LineChart,
  PieChart,
  Table2,
  FileText,
  Activity,
  TrendingUp,
  DollarSign,
  Users,
  Percent,
  GripVertical,
  X,
  Save,
  RotateCcw,
} from 'lucide-react';
import { cn } from '@/lib/cn';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

const ResponsiveGridLayout = WidthProvider(GridLayout);

// Widget types
type WidgetType =
  | 'kpi'
  | 'lineChart'
  | 'barChart'
  | 'pieChart'
  | 'table'
  | 'text'
  | 'forecast'
  | 'contribution'
  | 'roi';

interface WidgetConfig {
  id: string;
  type: WidgetType;
  title: string;
  config?: Record<string, unknown>;
}

interface DashboardLayout extends Layout {
  i: string;
}

interface DashboardBuilderProps {
  className?: string;
  initialLayout?: DashboardLayout[];
  initialWidgets?: WidgetConfig[];
  editable?: boolean;
  onLayoutChange?: (layout: DashboardLayout[]) => void;
  onWidgetsChange?: (widgets: WidgetConfig[]) => void;
  onSave?: (layout: DashboardLayout[], widgets: WidgetConfig[]) => void;
}

const widgetTypes: Array<{
  type: WidgetType;
  label: string;
  icon: React.ReactNode;
  defaultSize: { w: number; h: number };
}> = [
  {
    type: 'kpi',
    label: 'KPI Metric',
    icon: <Activity className="h-5 w-5" />,
    defaultSize: { w: 3, h: 2 },
  },
  {
    type: 'lineChart',
    label: 'Line Chart',
    icon: <LineChart className="h-5 w-5" />,
    defaultSize: { w: 6, h: 4 },
  },
  {
    type: 'barChart',
    label: 'Bar Chart',
    icon: <BarChart2 className="h-5 w-5" />,
    defaultSize: { w: 6, h: 4 },
  },
  {
    type: 'pieChart',
    label: 'Pie Chart',
    icon: <PieChart className="h-5 w-5" />,
    defaultSize: { w: 4, h: 4 },
  },
  {
    type: 'table',
    label: 'Data Table',
    icon: <Table2 className="h-5 w-5" />,
    defaultSize: { w: 6, h: 4 },
  },
  {
    type: 'text',
    label: 'Text/Notes',
    icon: <FileText className="h-5 w-5" />,
    defaultSize: { w: 4, h: 2 },
  },
  {
    type: 'forecast',
    label: 'Forecast',
    icon: <TrendingUp className="h-5 w-5" />,
    defaultSize: { w: 6, h: 4 },
  },
  {
    type: 'contribution',
    label: 'Channel Contribution',
    icon: <Percent className="h-5 w-5" />,
    defaultSize: { w: 6, h: 4 },
  },
  {
    type: 'roi',
    label: 'ROI Analysis',
    icon: <DollarSign className="h-5 w-5" />,
    defaultSize: { w: 4, h: 3 },
  },
];

const defaultLayout: DashboardLayout[] = [
  { i: 'kpi-1', x: 0, y: 0, w: 3, h: 2 },
  { i: 'kpi-2', x: 3, y: 0, w: 3, h: 2 },
  { i: 'kpi-3', x: 6, y: 0, w: 3, h: 2 },
  { i: 'kpi-4', x: 9, y: 0, w: 3, h: 2 },
  { i: 'chart-1', x: 0, y: 2, w: 8, h: 4 },
  { i: 'chart-2', x: 8, y: 2, w: 4, h: 4 },
];

const defaultWidgets: WidgetConfig[] = [
  { id: 'kpi-1', type: 'kpi', title: 'Total Revenue', config: { value: '$1.2M' } },
  { id: 'kpi-2', type: 'kpi', title: 'Conversions', config: { value: '12.5K' } },
  { id: 'kpi-3', type: 'kpi', title: 'ROAS', config: { value: '3.2x' } },
  { id: 'kpi-4', type: 'kpi', title: 'CAC', config: { value: '$45' } },
  { id: 'chart-1', type: 'lineChart', title: 'Revenue Trend' },
  { id: 'chart-2', type: 'pieChart', title: 'Channel Mix' },
];

export function DashboardBuilder({
  className,
  initialLayout = defaultLayout,
  initialWidgets = defaultWidgets,
  editable = true,
  onLayoutChange,
  onWidgetsChange,
  onSave,
}: DashboardBuilderProps) {
  const [layout, setLayout] = React.useState<DashboardLayout[]>(initialLayout);
  const [widgets, setWidgets] = React.useState<WidgetConfig[]>(initialWidgets);
  const [isEditing, setIsEditing] = React.useState(false);
  const [addWidgetOpen, setAddWidgetOpen] = React.useState(false);

  const handleLayoutChange = (newLayout: Layout[]) => {
    const typedLayout = newLayout as DashboardLayout[];
    setLayout(typedLayout);
    onLayoutChange?.(typedLayout);
  };

  const addWidget = (type: WidgetType) => {
    const widgetDef = widgetTypes.find((w) => w.type === type);
    if (!widgetDef) return;

    const id = `${type}-${Date.now()}`;
    const newWidget: WidgetConfig = {
      id,
      type,
      title: widgetDef.label,
    };

    const newLayoutItem: DashboardLayout = {
      i: id,
      x: 0,
      y: Infinity, // Put at the bottom
      w: widgetDef.defaultSize.w,
      h: widgetDef.defaultSize.h,
    };

    setWidgets([...widgets, newWidget]);
    setLayout([...layout, newLayoutItem]);
    setAddWidgetOpen(false);
  };

  const removeWidget = (id: string) => {
    setWidgets(widgets.filter((w) => w.id !== id));
    setLayout(layout.filter((l) => l.i !== id));
  };

  const handleSave = () => {
    onSave?.(layout, widgets);
    setIsEditing(false);
  };

  const handleReset = () => {
    setLayout(initialLayout);
    setWidgets(initialWidgets);
  };

  const getWidgetIcon = (type: WidgetType) => {
    const widgetDef = widgetTypes.find((w) => w.type === type);
    return widgetDef?.icon ?? <Activity className="h-5 w-5" />;
  };

  return (
    <div className={cn('space-y-4', className)}>
      {/* Toolbar */}
      {editable && (
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Button
              variant={isEditing ? 'default' : 'outline'}
              size="sm"
              onClick={() => setIsEditing(!isEditing)}
            >
              <Settings className="mr-2 h-4 w-4" />
              {isEditing ? 'Exit Edit Mode' : 'Edit Dashboard'}
            </Button>

            {isEditing && (
              <>
                <Dialog open={addWidgetOpen} onOpenChange={setAddWidgetOpen}>
                  <DialogTrigger asChild>
                    <Button variant="outline" size="sm">
                      <Plus className="mr-2 h-4 w-4" />
                      Add Widget
                    </Button>
                  </DialogTrigger>
                  <DialogContent>
                    <DialogHeader>
                      <DialogTitle>Add Widget</DialogTitle>
                      <DialogDescription>
                        Select a widget type to add to your dashboard
                      </DialogDescription>
                    </DialogHeader>
                    <div className="grid grid-cols-3 gap-4 py-4">
                      {widgetTypes.map((widget) => (
                        <button
                          key={widget.type}
                          onClick={() => addWidget(widget.type)}
                          className="flex flex-col items-center gap-2 p-4 rounded-lg border hover:bg-accent hover:text-accent-foreground transition-colors"
                        >
                          {widget.icon}
                          <span className="text-sm font-medium">{widget.label}</span>
                        </button>
                      ))}
                    </div>
                  </DialogContent>
                </Dialog>

                <Button variant="outline" size="sm" onClick={handleReset}>
                  <RotateCcw className="mr-2 h-4 w-4" />
                  Reset
                </Button>
              </>
            )}
          </div>

          {isEditing && (
            <Button size="sm" onClick={handleSave}>
              <Save className="mr-2 h-4 w-4" />
              Save Layout
            </Button>
          )}
        </div>
      )}

      {/* Grid Layout */}
      <ResponsiveGridLayout
        className="layout"
        layout={layout}
        cols={12}
        rowHeight={80}
        onLayoutChange={handleLayoutChange}
        isDraggable={isEditing}
        isResizable={isEditing}
        draggableHandle=".drag-handle"
        margin={[16, 16]}
      >
        {widgets.map((widget) => (
          <div key={widget.id} className="h-full">
            <WidgetWrapper
              widget={widget}
              isEditing={isEditing}
              onRemove={() => removeWidget(widget.id)}
              icon={getWidgetIcon(widget.type)}
            />
          </div>
        ))}
      </ResponsiveGridLayout>
    </div>
  );
}

interface WidgetWrapperProps {
  widget: WidgetConfig;
  isEditing: boolean;
  onRemove: () => void;
  icon: React.ReactNode;
}

function WidgetWrapper({ widget, isEditing, onRemove, icon }: WidgetWrapperProps) {
  return (
    <Card className="h-full flex flex-col">
      <CardHeader className="py-3 px-4 flex-row items-center space-y-0 gap-2">
        {isEditing && (
          <div className="drag-handle cursor-grab active:cursor-grabbing p-1 -ml-2 hover:bg-accent rounded">
            <GripVertical className="h-4 w-4 text-muted-foreground" />
          </div>
        )}
        <div className="flex items-center gap-2 flex-1">
          <div className="text-muted-foreground">{icon}</div>
          <CardTitle className="text-sm font-medium">{widget.title}</CardTitle>
        </div>
        {isEditing && (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" className="h-6 w-6">
                <Settings className="h-3 w-3" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={onRemove} className="text-destructive">
                <Trash2 className="mr-2 h-4 w-4" />
                Remove
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        )}
      </CardHeader>
      <CardContent className="flex-1 p-4 pt-0">
        <WidgetContent widget={widget} />
      </CardContent>
    </Card>
  );
}

function WidgetContent({ widget }: { widget: WidgetConfig }) {
  // Placeholder content based on widget type
  switch (widget.type) {
    case 'kpi':
      return (
        <div className="flex flex-col justify-center h-full">
          <div className="text-3xl font-bold">
            {(widget.config?.value as string) ?? '--'}
          </div>
          <div className="text-sm text-muted-foreground flex items-center gap-1">
            <TrendingUp className="h-3 w-3 text-success" />
            <span className="text-success">+12.5%</span>
            <span>vs last period</span>
          </div>
        </div>
      );

    case 'lineChart':
    case 'barChart':
    case 'pieChart':
    case 'forecast':
    case 'contribution':
    case 'roi':
      return (
        <div className="flex items-center justify-center h-full text-muted-foreground bg-muted/50 rounded-md">
          <div className="text-center">
            <BarChart2 className="h-12 w-12 mx-auto mb-2 opacity-50" />
            <p className="text-sm">Chart placeholder</p>
          </div>
        </div>
      );

    case 'table':
      return (
        <div className="flex items-center justify-center h-full text-muted-foreground bg-muted/50 rounded-md">
          <div className="text-center">
            <Table2 className="h-12 w-12 mx-auto mb-2 opacity-50" />
            <p className="text-sm">Table placeholder</p>
          </div>
        </div>
      );

    case 'text':
      return (
        <div className="h-full p-2 text-sm text-muted-foreground">
          <p>Add your notes and insights here...</p>
        </div>
      );

    default:
      return null;
  }
}

export type { WidgetConfig, WidgetType, DashboardLayout };
