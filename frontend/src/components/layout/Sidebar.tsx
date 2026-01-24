/**
 * Collapsible Sidebar Component
 *
 * A responsive, collapsible navigation sidebar with animations.
 */

import * as React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Link, useLocation } from '@tanstack/react-router';
import {
  ChevronLeft,
  ChevronRight,
  Home,
  Database,
  Layers,
  TrendingUp,
  Calculator,
  FileText,
  Settings,
  HelpCircle,
  PanelLeftClose,
  PanelLeft,
  BarChart3,
  GitBranch,
  Beaker,
  Target,
  Sparkles,
  Activity,
  Workflow,
  Package,
  Clock,
  History,
  Shield,
  FileSearch,
} from 'lucide-react';
import { cn } from '@/lib/cn';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';

interface NavItem {
  id: string;
  label: string;
  icon: React.ReactNode;
  href: string;
  badge?: string | number;
  children?: NavItem[];
}

interface SidebarProps {
  className?: string;
  defaultCollapsed?: boolean;
  onCollapsedChange?: (collapsed: boolean) => void;
}

const navigationItems: NavItem[] = [
  {
    id: 'dashboard',
    label: 'Dashboard',
    icon: <Home className="h-5 w-5" />,
    href: '/',
  },
  {
    id: 'data',
    label: 'Data Management',
    icon: <Database className="h-5 w-5" />,
    href: '/data',
    children: [
      {
        id: 'data-profiling',
        label: 'Data Profiling',
        icon: <FileSearch className="h-4 w-4" />,
        href: '/data/profiling',
      },
      {
        id: 'data-versions',
        label: 'Data Versions',
        icon: <History className="h-4 w-4" />,
        href: '/data/versions',
      },
    ],
  },
  {
    id: 'models',
    label: 'Models',
    icon: <Layers className="h-5 w-5" />,
    href: '/models',
    children: [
      {
        id: 'mmm',
        label: 'Marketing Mix',
        icon: <BarChart3 className="h-4 w-4" />,
        href: '/models/mmm',
      },
      {
        id: 'attribution',
        label: 'Attribution',
        icon: <GitBranch className="h-4 w-4" />,
        href: '/models/attribution',
      },
      {
        id: 'causal',
        label: 'Causal Inference',
        icon: <Target className="h-4 w-4" />,
        href: '/models/causal',
      },
    ],
  },
  {
    id: 'registry',
    label: 'Model Registry',
    icon: <Package className="h-5 w-5" />,
    href: '/registry',
    badge: 'New',
  },
  {
    id: 'experiments',
    label: 'Experiments',
    icon: <Beaker className="h-5 w-5" />,
    href: '/experiments',
  },
  {
    id: 'forecasting',
    label: 'Forecasting',
    icon: <TrendingUp className="h-5 w-5" />,
    href: '/forecasting',
  },
  {
    id: 'optimization',
    label: 'Optimization',
    icon: <Calculator className="h-5 w-5" />,
    href: '/optimization',
  },
  {
    id: 'insights',
    label: 'AI Insights',
    icon: <Sparkles className="h-5 w-5" />,
    href: '/insights',
    badge: 'Beta',
  },
  {
    id: 'etl',
    label: 'ETL Pipelines',
    icon: <Workflow className="h-5 w-5" />,
    href: '/etl',
  },
  {
    id: 'scheduler',
    label: 'Job Scheduler',
    icon: <Clock className="h-5 w-5" />,
    href: '/scheduler',
  },
  {
    id: 'monitoring',
    label: 'Monitoring',
    icon: <Activity className="h-5 w-5" />,
    href: '/monitoring',
  },
  {
    id: 'reports',
    label: 'Reports',
    icon: <FileText className="h-5 w-5" />,
    href: '/reports',
  },
];

const bottomItems: NavItem[] = [
  {
    id: 'privacy',
    label: 'Privacy & Consent',
    icon: <Shield className="h-5 w-5" />,
    href: '/privacy',
  },
  {
    id: 'settings',
    label: 'Settings',
    icon: <Settings className="h-5 w-5" />,
    href: '/settings',
  },
  {
    id: 'help',
    label: 'Help & Support',
    icon: <HelpCircle className="h-5 w-5" />,
    href: '/help',
  },
];

export function Sidebar({
  className,
  defaultCollapsed = false,
  onCollapsedChange,
}: SidebarProps) {
  const [collapsed, setCollapsed] = React.useState(defaultCollapsed);
  const [expandedItems, setExpandedItems] = React.useState<string[]>([]);
  const location = useLocation();

  const toggleCollapsed = () => {
    const newCollapsed = !collapsed;
    setCollapsed(newCollapsed);
    onCollapsedChange?.(newCollapsed);
  };

  const toggleExpanded = (id: string) => {
    setExpandedItems((prev) =>
      prev.includes(id) ? prev.filter((i) => i !== id) : [...prev, id]
    );
  };

  const isActive = (href: string) => location.pathname === href;
  const isChildActive = (item: NavItem) =>
    item.children?.some((child) => isActive(child.href));

  const sidebarVariants = {
    expanded: { width: 256 },
    collapsed: { width: 64 },
  };

  return (
    <TooltipProvider delayDuration={0}>
      <motion.aside
        initial={collapsed ? 'collapsed' : 'expanded'}
        animate={collapsed ? 'collapsed' : 'expanded'}
        variants={sidebarVariants}
        transition={{ type: 'spring', stiffness: 300, damping: 30 }}
        className={cn(
          'fixed left-0 top-0 z-40 h-screen border-r bg-sidebar-background flex flex-col',
          className
        )}
      >
        {/* Header */}
        <div className="flex h-16 items-center justify-between border-b px-4">
          <AnimatePresence mode="wait">
            {!collapsed && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="flex items-center gap-2"
              >
                <div className="h-8 w-8 rounded-lg bg-primary flex items-center justify-center">
                  <BarChart3 className="h-5 w-5 text-primary-foreground" />
                </div>
                <span className="font-semibold text-lg">Analytics</span>
              </motion.div>
            )}
          </AnimatePresence>

          <button
            onClick={toggleCollapsed}
            className="p-2 rounded-md hover:bg-sidebar-accent transition-colors"
          >
            {collapsed ? (
              <PanelLeft className="h-5 w-5" />
            ) : (
              <PanelLeftClose className="h-5 w-5" />
            )}
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 overflow-y-auto py-4">
          <ul className="space-y-1 px-2">
            {navigationItems.map((item) => (
              <li key={item.id}>
                <NavItemComponent
                  item={item}
                  collapsed={collapsed}
                  isActive={isActive(item.href)}
                  isChildActive={isChildActive(item)}
                  isExpanded={expandedItems.includes(item.id)}
                  onToggleExpand={() => toggleExpanded(item.id)}
                />
              </li>
            ))}
          </ul>
        </nav>

        {/* Bottom Navigation */}
        <div className="border-t py-4">
          <ul className="space-y-1 px-2">
            {bottomItems.map((item) => (
              <li key={item.id}>
                <NavItemComponent
                  item={item}
                  collapsed={collapsed}
                  isActive={isActive(item.href)}
                />
              </li>
            ))}
          </ul>
        </div>
      </motion.aside>
    </TooltipProvider>
  );
}

interface NavItemComponentProps {
  item: NavItem;
  collapsed: boolean;
  isActive: boolean;
  isChildActive?: boolean;
  isExpanded?: boolean;
  onToggleExpand?: () => void;
  isChild?: boolean;
}

function NavItemComponent({
  item,
  collapsed,
  isActive,
  isChildActive,
  isExpanded,
  onToggleExpand,
  isChild = false,
}: NavItemComponentProps) {
  const hasChildren = item.children && item.children.length > 0;
  const active = isActive || isChildActive;

  const content = (
    <div
      className={cn(
        'flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors',
        active
          ? 'bg-sidebar-accent text-sidebar-accent-foreground'
          : 'text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground',
        isChild && 'pl-10',
        collapsed && !isChild && 'justify-center px-2'
      )}
    >
      {item.icon}
      <AnimatePresence mode="wait">
        {!collapsed && (
          <motion.span
            initial={{ opacity: 0, width: 0 }}
            animate={{ opacity: 1, width: 'auto' }}
            exit={{ opacity: 0, width: 0 }}
            className="flex-1 truncate"
          >
            {item.label}
          </motion.span>
        )}
      </AnimatePresence>
      {!collapsed && item.badge && (
        <span
          className={cn(
            'ml-auto text-xs px-2 py-0.5 rounded-full',
            item.badge === 'New' && 'bg-primary text-primary-foreground',
            item.badge === 'Beta' && 'bg-secondary text-secondary-foreground'
          )}
        >
          {item.badge}
        </span>
      )}
      {!collapsed && hasChildren && (
        <ChevronRight
          className={cn(
            'h-4 w-4 transition-transform',
            isExpanded && 'rotate-90'
          )}
        />
      )}
    </div>
  );

  if (collapsed && !isChild) {
    return (
      <Tooltip>
        <TooltipTrigger asChild>
          <Link to={item.href}>{content}</Link>
        </TooltipTrigger>
        <TooltipContent side="right" sideOffset={10}>
          <p>{item.label}</p>
          {item.badge && (
            <span className="ml-2 text-xs opacity-75">({item.badge})</span>
          )}
        </TooltipContent>
      </Tooltip>
    );
  }

  if (hasChildren) {
    return (
      <>
        <button onClick={onToggleExpand} className="w-full">
          {content}
        </button>
        <AnimatePresence>
          {isExpanded && !collapsed && (
            <motion.ul
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="overflow-hidden"
            >
              {item.children?.map((child) => (
                <li key={child.id}>
                  <Link to={child.href}>
                    <div
                      className={cn(
                        'flex items-center gap-3 rounded-md px-3 py-2 pl-10 text-sm transition-colors',
                        'text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground'
                      )}
                    >
                      {child.icon}
                      <span className="truncate">{child.label}</span>
                    </div>
                  </Link>
                </li>
              ))}
            </motion.ul>
          )}
        </AnimatePresence>
      </>
    );
  }

  return <Link to={item.href}>{content}</Link>;
}

// Hook for sidebar state
export function useSidebar() {
  const [collapsed, setCollapsed] = React.useState(false);

  React.useEffect(() => {
    const stored = localStorage.getItem('sidebar-collapsed');
    if (stored !== null) {
      setCollapsed(JSON.parse(stored));
    }
  }, []);

  const toggle = () => {
    const newValue = !collapsed;
    setCollapsed(newValue);
    localStorage.setItem('sidebar-collapsed', JSON.stringify(newValue));
  };

  return { collapsed, setCollapsed, toggle };
}
