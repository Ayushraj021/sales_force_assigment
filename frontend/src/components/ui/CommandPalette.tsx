/**
 * Command Palette Component
 *
 * A powerful command palette (Cmd+K) for quick navigation and actions.
 */

import * as React from 'react';
import { Command } from 'cmdk';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Search,
  FileText,
  BarChart2,
  Settings,
  User,
  Database,
  TrendingUp,
  Calculator,
  Layers,
  ArrowRight,
  Moon,
  Sun,
  LogOut,
} from 'lucide-react';
import { cn } from '@/lib/cn';
import { useTheme } from '@/stores/themeStore';

interface CommandItem {
  id: string;
  title: string;
  description?: string;
  icon?: React.ReactNode;
  shortcut?: string[];
  action?: () => void;
  href?: string;
  group?: string;
}

interface CommandPaletteProps {
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
}

const defaultCommands: CommandItem[] = [
  {
    id: 'dashboard',
    title: 'Go to Dashboard',
    description: 'View executive dashboard',
    icon: <BarChart2 className="h-4 w-4" />,
    shortcut: ['G', 'D'],
    href: '/',
    group: 'Navigation',
  },
  {
    id: 'data',
    title: 'Data Management',
    description: 'Manage datasets and sources',
    icon: <Database className="h-4 w-4" />,
    shortcut: ['G', 'M'],
    href: '/data',
    group: 'Navigation',
  },
  {
    id: 'models',
    title: 'Models',
    description: 'View and manage models',
    icon: <Layers className="h-4 w-4" />,
    shortcut: ['G', 'O'],
    href: '/models',
    group: 'Navigation',
  },
  {
    id: 'forecasting',
    title: 'Forecasting',
    description: 'Sales forecasting and predictions',
    icon: <TrendingUp className="h-4 w-4" />,
    shortcut: ['G', 'F'],
    href: '/forecasting',
    group: 'Navigation',
  },
  {
    id: 'optimization',
    title: 'Budget Optimization',
    description: 'Optimize marketing budget allocation',
    icon: <Calculator className="h-4 w-4" />,
    shortcut: ['G', 'B'],
    href: '/optimization',
    group: 'Navigation',
  },
  {
    id: 'reports',
    title: 'Reports',
    description: 'View and generate reports',
    icon: <FileText className="h-4 w-4" />,
    shortcut: ['G', 'R'],
    href: '/reports',
    group: 'Navigation',
  },
  {
    id: 'settings',
    title: 'Settings',
    description: 'Application settings',
    icon: <Settings className="h-4 w-4" />,
    shortcut: ['G', 'S'],
    href: '/settings',
    group: 'Navigation',
  },
  {
    id: 'profile',
    title: 'Profile',
    description: 'View and edit your profile',
    icon: <User className="h-4 w-4" />,
    group: 'Account',
  },
  {
    id: 'logout',
    title: 'Sign Out',
    description: 'Sign out of your account',
    icon: <LogOut className="h-4 w-4" />,
    group: 'Account',
  },
];

export function CommandPalette({ open, onOpenChange }: CommandPaletteProps) {
  const [isOpen, setIsOpen] = React.useState(open ?? false);
  const [search, setSearch] = React.useState('');
  const { toggleTheme, isDark } = useTheme();

  const handleOpenChange = (newOpen: boolean) => {
    setIsOpen(newOpen);
    onOpenChange?.(newOpen);
  };

  // Handle keyboard shortcut
  React.useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === 'k' && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        handleOpenChange(!isOpen);
      }
    };

    document.addEventListener('keydown', down);
    return () => document.removeEventListener('keydown', down);
  }, [isOpen]);

  // Sync with prop
  React.useEffect(() => {
    if (open !== undefined) {
      setIsOpen(open);
    }
  }, [open]);

  const themeCommand: CommandItem = {
    id: 'theme',
    title: isDark ? 'Switch to Light Mode' : 'Switch to Dark Mode',
    description: 'Toggle application theme',
    icon: isDark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />,
    shortcut: ['T'],
    action: () => {
      toggleTheme();
      handleOpenChange(false);
    },
    group: 'Preferences',
  };

  const allCommands = [...defaultCommands, themeCommand];
  const groups = [...new Set(allCommands.map((c) => c.group))];

  const handleSelect = (item: CommandItem) => {
    if (item.action) {
      item.action();
    } else if (item.href) {
      window.location.href = item.href;
    }
    handleOpenChange(false);
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 bg-black/50"
            onClick={() => handleOpenChange(false)}
          />

          {/* Command Dialog */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: -20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: -20 }}
            transition={{ type: 'spring', duration: 0.3 }}
            className="fixed left-1/2 top-[20%] z-50 w-full max-w-lg -translate-x-1/2"
          >
            <Command
              className="rounded-lg border bg-popover shadow-2xl overflow-hidden"
              loop
            >
              <div className="flex items-center border-b px-3">
                <Search className="mr-2 h-4 w-4 shrink-0 opacity-50" />
                <Command.Input
                  value={search}
                  onValueChange={setSearch}
                  placeholder="Type a command or search..."
                  className="flex h-12 w-full bg-transparent py-3 text-sm outline-none placeholder:text-muted-foreground disabled:cursor-not-allowed disabled:opacity-50"
                />
                <kbd className="pointer-events-none hidden h-5 select-none items-center gap-1 rounded border bg-muted px-1.5 font-mono text-[10px] font-medium opacity-100 sm:flex">
                  <span className="text-xs">esc</span>
                </kbd>
              </div>

              <Command.List className="max-h-[300px] overflow-y-auto overflow-x-hidden p-2">
                <Command.Empty className="py-6 text-center text-sm text-muted-foreground">
                  No results found.
                </Command.Empty>

                {groups.map((group) => (
                  <Command.Group key={group} heading={group} className="px-2 py-1.5">
                    <p className="text-xs font-medium text-muted-foreground px-2 py-1.5">
                      {group}
                    </p>
                    {allCommands
                      .filter((cmd) => cmd.group === group)
                      .map((item) => (
                        <Command.Item
                          key={item.id}
                          value={`${item.title} ${item.description || ''}`}
                          onSelect={() => handleSelect(item)}
                          className="relative flex cursor-pointer select-none items-center rounded-md px-2 py-2 text-sm outline-none aria-selected:bg-accent aria-selected:text-accent-foreground data-[disabled]:pointer-events-none data-[disabled]:opacity-50"
                        >
                          <div className="mr-3 flex h-8 w-8 items-center justify-center rounded-md border bg-background">
                            {item.icon}
                          </div>
                          <div className="flex-1">
                            <p className="font-medium">{item.title}</p>
                            {item.description && (
                              <p className="text-xs text-muted-foreground">
                                {item.description}
                              </p>
                            )}
                          </div>
                          {item.shortcut && (
                            <div className="flex items-center gap-1">
                              {item.shortcut.map((key) => (
                                <kbd
                                  key={key}
                                  className="pointer-events-none inline-flex h-5 select-none items-center gap-1 rounded border bg-muted px-1.5 font-mono text-[10px] font-medium text-muted-foreground"
                                >
                                  {key}
                                </kbd>
                              ))}
                            </div>
                          )}
                          <ArrowRight className="ml-2 h-4 w-4 opacity-0 group-aria-selected:opacity-100" />
                        </Command.Item>
                      ))}
                  </Command.Group>
                ))}
              </Command.List>

              <div className="flex items-center justify-between border-t px-3 py-2 text-xs text-muted-foreground">
                <div className="flex items-center gap-2">
                  <span>Navigate</span>
                  <kbd className="rounded border bg-muted px-1">↑↓</kbd>
                </div>
                <div className="flex items-center gap-2">
                  <span>Select</span>
                  <kbd className="rounded border bg-muted px-1">↵</kbd>
                </div>
                <div className="flex items-center gap-2">
                  <span>Close</span>
                  <kbd className="rounded border bg-muted px-1">esc</kbd>
                </div>
              </div>
            </Command>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

// Hook for triggering command palette
export function useCommandPalette() {
  const [open, setOpen] = React.useState(false);

  return {
    open,
    setOpen,
    toggle: () => setOpen((prev) => !prev),
  };
}
