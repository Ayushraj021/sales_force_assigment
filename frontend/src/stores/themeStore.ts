/**
 * Theme Store
 *
 * Manages dark/light mode theming with system preference detection
 * and persistent storage.
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export type Theme = 'light' | 'dark' | 'system';
export type ResolvedTheme = 'light' | 'dark';

interface ThemeState {
  theme: Theme;
  resolvedTheme: ResolvedTheme;
  setTheme: (theme: Theme) => void;
  toggleTheme: () => void;
}

// Get the resolved theme based on system preference
const getSystemTheme = (): ResolvedTheme => {
  if (typeof window === 'undefined') return 'light';
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
};

// Get resolved theme from theme setting
const resolveTheme = (theme: Theme): ResolvedTheme => {
  if (theme === 'system') {
    return getSystemTheme();
  }
  return theme;
};

// Apply theme to document
const applyTheme = (theme: ResolvedTheme) => {
  if (typeof document === 'undefined') return;

  const root = document.documentElement;

  // Remove existing theme classes
  root.classList.remove('light', 'dark');

  // Add new theme class
  root.classList.add(theme);

  // Update color-scheme for native elements
  root.style.colorScheme = theme;

  // Update meta theme-color for mobile browsers
  const metaThemeColor = document.querySelector('meta[name="theme-color"]');
  if (metaThemeColor) {
    metaThemeColor.setAttribute(
      'content',
      theme === 'dark' ? 'hsl(222, 47%, 11%)' : 'hsl(210, 40%, 98%)'
    );
  }
};

export const useThemeStore = create<ThemeState>()(
  persist(
    (set, get) => ({
      theme: 'system',
      resolvedTheme: getSystemTheme(),

      setTheme: (theme: Theme) => {
        const resolvedTheme = resolveTheme(theme);
        applyTheme(resolvedTheme);
        set({ theme, resolvedTheme });
      },

      toggleTheme: () => {
        const { resolvedTheme } = get();
        const newTheme: Theme = resolvedTheme === 'light' ? 'dark' : 'light';
        const newResolvedTheme = resolveTheme(newTheme);
        applyTheme(newResolvedTheme);
        set({ theme: newTheme, resolvedTheme: newResolvedTheme });
      },
    }),
    {
      name: 'theme-storage',
      onRehydrateStorage: () => (state) => {
        // Apply theme on rehydration
        if (state) {
          const resolvedTheme = resolveTheme(state.theme);
          applyTheme(resolvedTheme);
          // Update resolved theme in case system preference changed
          if (state.theme === 'system') {
            state.resolvedTheme = resolvedTheme;
          }
        }
      },
    }
  )
);

// Listen for system theme changes
if (typeof window !== 'undefined') {
  const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');

  mediaQuery.addEventListener('change', (e) => {
    const state = useThemeStore.getState();
    if (state.theme === 'system') {
      const newResolvedTheme: ResolvedTheme = e.matches ? 'dark' : 'light';
      applyTheme(newResolvedTheme);
      useThemeStore.setState({ resolvedTheme: newResolvedTheme });
    }
  });
}

// Helper hook for theme-aware styles
export const useTheme = () => {
  const { theme, resolvedTheme, setTheme, toggleTheme } = useThemeStore();

  return {
    theme,
    resolvedTheme,
    setTheme,
    toggleTheme,
    isDark: resolvedTheme === 'dark',
    isLight: resolvedTheme === 'light',
    isSystem: theme === 'system',
  };
};

// Export convenience selectors
export const selectTheme = (state: ThemeState) => state.theme;
export const selectResolvedTheme = (state: ThemeState) => state.resolvedTheme;
export const selectIsDark = (state: ThemeState) => state.resolvedTheme === 'dark';
