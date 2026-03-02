/**
 * Design System Color Tokens
 *
 * A comprehensive color palette supporting both light and dark themes.
 * Based on a semantic naming convention for maintainability.
 */

// Base color scales (HSL values for easy manipulation)
export const baseColors = {
  // Neutrals - Slate palette
  slate: {
    50: 'hsl(210, 40%, 98%)',
    100: 'hsl(210, 40%, 96%)',
    200: 'hsl(214, 32%, 91%)',
    300: 'hsl(213, 27%, 84%)',
    400: 'hsl(215, 20%, 65%)',
    500: 'hsl(215, 16%, 47%)',
    600: 'hsl(215, 19%, 35%)',
    700: 'hsl(215, 25%, 27%)',
    800: 'hsl(217, 33%, 17%)',
    900: 'hsl(222, 47%, 11%)',
    950: 'hsl(229, 84%, 5%)',
  },

  // Primary - Indigo/Blue
  primary: {
    50: 'hsl(226, 100%, 97%)',
    100: 'hsl(226, 100%, 94%)',
    200: 'hsl(228, 96%, 89%)',
    300: 'hsl(230, 94%, 82%)',
    400: 'hsl(234, 89%, 74%)',
    500: 'hsl(239, 84%, 67%)',
    600: 'hsl(243, 75%, 59%)',
    700: 'hsl(245, 58%, 51%)',
    800: 'hsl(244, 55%, 41%)',
    900: 'hsl(242, 47%, 34%)',
    950: 'hsl(244, 47%, 20%)',
  },

  // Secondary - Violet
  secondary: {
    50: 'hsl(270, 100%, 98%)',
    100: 'hsl(269, 100%, 95%)',
    200: 'hsl(269, 100%, 92%)',
    300: 'hsl(269, 97%, 85%)',
    400: 'hsl(270, 95%, 75%)',
    500: 'hsl(271, 91%, 65%)',
    600: 'hsl(271, 81%, 56%)',
    700: 'hsl(272, 72%, 47%)',
    800: 'hsl(273, 67%, 39%)',
    900: 'hsl(274, 66%, 32%)',
    950: 'hsl(274, 87%, 21%)',
  },

  // Success - Emerald
  success: {
    50: 'hsl(152, 81%, 96%)',
    100: 'hsl(149, 80%, 90%)',
    200: 'hsl(152, 76%, 80%)',
    300: 'hsl(156, 72%, 67%)',
    400: 'hsl(158, 64%, 52%)',
    500: 'hsl(160, 84%, 39%)',
    600: 'hsl(161, 94%, 30%)',
    700: 'hsl(163, 94%, 24%)',
    800: 'hsl(163, 88%, 20%)',
    900: 'hsl(164, 86%, 16%)',
    950: 'hsl(166, 91%, 9%)',
  },

  // Warning - Amber
  warning: {
    50: 'hsl(48, 100%, 96%)',
    100: 'hsl(48, 96%, 89%)',
    200: 'hsl(48, 97%, 77%)',
    300: 'hsl(46, 97%, 65%)',
    400: 'hsl(43, 96%, 56%)',
    500: 'hsl(38, 92%, 50%)',
    600: 'hsl(32, 95%, 44%)',
    700: 'hsl(26, 90%, 37%)',
    800: 'hsl(23, 83%, 31%)',
    900: 'hsl(22, 78%, 26%)',
    950: 'hsl(21, 92%, 14%)',
  },

  // Error - Rose
  error: {
    50: 'hsl(355, 100%, 97%)',
    100: 'hsl(355, 100%, 94%)',
    200: 'hsl(353, 96%, 90%)',
    300: 'hsl(353, 96%, 82%)',
    400: 'hsl(351, 95%, 71%)',
    500: 'hsl(349, 89%, 60%)',
    600: 'hsl(346, 77%, 49%)',
    700: 'hsl(345, 83%, 41%)',
    800: 'hsl(343, 80%, 35%)',
    900: 'hsl(342, 75%, 30%)',
    950: 'hsl(343, 88%, 16%)',
  },

  // Info - Sky
  info: {
    50: 'hsl(204, 100%, 97%)',
    100: 'hsl(204, 94%, 94%)',
    200: 'hsl(201, 94%, 86%)',
    300: 'hsl(199, 95%, 74%)',
    400: 'hsl(198, 93%, 60%)',
    500: 'hsl(199, 89%, 48%)',
    600: 'hsl(200, 98%, 39%)',
    700: 'hsl(201, 96%, 32%)',
    800: 'hsl(201, 90%, 27%)',
    900: 'hsl(202, 80%, 24%)',
    950: 'hsl(204, 80%, 16%)',
  },
} as const;

// Semantic tokens for light theme
export const lightTheme = {
  // Background colors
  background: {
    default: baseColors.slate[50],
    paper: 'hsl(0, 0%, 100%)',
    subtle: baseColors.slate[100],
    muted: baseColors.slate[200],
    elevated: 'hsl(0, 0%, 100%)',
  },

  // Foreground (text) colors
  foreground: {
    default: baseColors.slate[900],
    muted: baseColors.slate[500],
    subtle: baseColors.slate[400],
    inverted: 'hsl(0, 0%, 100%)',
  },

  // Border colors
  border: {
    default: baseColors.slate[200],
    muted: baseColors.slate[100],
    strong: baseColors.slate[300],
  },

  // Component colors
  card: {
    background: 'hsl(0, 0%, 100%)',
    foreground: baseColors.slate[900],
    border: baseColors.slate[200],
  },

  // Interactive states
  interactive: {
    hover: baseColors.slate[100],
    active: baseColors.slate[200],
    focus: baseColors.primary[500],
    disabled: baseColors.slate[300],
  },

  // Primary action colors
  primary: {
    default: baseColors.primary[600],
    hover: baseColors.primary[700],
    active: baseColors.primary[800],
    foreground: 'hsl(0, 0%, 100%)',
  },

  // Secondary action colors
  secondary: {
    default: baseColors.secondary[600],
    hover: baseColors.secondary[700],
    active: baseColors.secondary[800],
    foreground: 'hsl(0, 0%, 100%)',
  },

  // Status colors
  success: {
    default: baseColors.success[600],
    light: baseColors.success[50],
    foreground: 'hsl(0, 0%, 100%)',
  },
  warning: {
    default: baseColors.warning[500],
    light: baseColors.warning[50],
    foreground: baseColors.warning[950],
  },
  error: {
    default: baseColors.error[600],
    light: baseColors.error[50],
    foreground: 'hsl(0, 0%, 100%)',
  },
  info: {
    default: baseColors.info[600],
    light: baseColors.info[50],
    foreground: 'hsl(0, 0%, 100%)',
  },

  // Chart colors
  chart: {
    primary: baseColors.primary[500],
    secondary: baseColors.secondary[500],
    tertiary: baseColors.info[500],
    quaternary: baseColors.success[500],
    quinary: baseColors.warning[500],
    senary: baseColors.error[500],
    series: [
      baseColors.primary[500],
      baseColors.secondary[500],
      baseColors.info[500],
      baseColors.success[500],
      baseColors.warning[500],
      baseColors.error[500],
      baseColors.primary[300],
      baseColors.secondary[300],
      baseColors.info[300],
      baseColors.success[300],
    ],
  },
} as const;

// Semantic tokens for dark theme
export const darkTheme = {
  // Background colors
  background: {
    default: baseColors.slate[950],
    paper: baseColors.slate[900],
    subtle: baseColors.slate[800],
    muted: baseColors.slate[700],
    elevated: baseColors.slate[800],
  },

  // Foreground (text) colors
  foreground: {
    default: baseColors.slate[50],
    muted: baseColors.slate[400],
    subtle: baseColors.slate[500],
    inverted: baseColors.slate[900],
  },

  // Border colors
  border: {
    default: baseColors.slate[700],
    muted: baseColors.slate[800],
    strong: baseColors.slate[600],
  },

  // Component colors
  card: {
    background: baseColors.slate[900],
    foreground: baseColors.slate[50],
    border: baseColors.slate[700],
  },

  // Interactive states
  interactive: {
    hover: baseColors.slate[800],
    active: baseColors.slate[700],
    focus: baseColors.primary[400],
    disabled: baseColors.slate[700],
  },

  // Primary action colors
  primary: {
    default: baseColors.primary[500],
    hover: baseColors.primary[400],
    active: baseColors.primary[300],
    foreground: 'hsl(0, 0%, 100%)',
  },

  // Secondary action colors
  secondary: {
    default: baseColors.secondary[500],
    hover: baseColors.secondary[400],
    active: baseColors.secondary[300],
    foreground: 'hsl(0, 0%, 100%)',
  },

  // Status colors
  success: {
    default: baseColors.success[500],
    light: baseColors.success[900],
    foreground: 'hsl(0, 0%, 100%)',
  },
  warning: {
    default: baseColors.warning[500],
    light: baseColors.warning[900],
    foreground: baseColors.warning[950],
  },
  error: {
    default: baseColors.error[500],
    light: baseColors.error[900],
    foreground: 'hsl(0, 0%, 100%)',
  },
  info: {
    default: baseColors.info[500],
    light: baseColors.info[900],
    foreground: 'hsl(0, 0%, 100%)',
  },

  // Chart colors (brighter for dark mode)
  chart: {
    primary: baseColors.primary[400],
    secondary: baseColors.secondary[400],
    tertiary: baseColors.info[400],
    quaternary: baseColors.success[400],
    quinary: baseColors.warning[400],
    senary: baseColors.error[400],
    series: [
      baseColors.primary[400],
      baseColors.secondary[400],
      baseColors.info[400],
      baseColors.success[400],
      baseColors.warning[400],
      baseColors.error[400],
      baseColors.primary[300],
      baseColors.secondary[300],
      baseColors.info[300],
      baseColors.success[300],
    ],
  },
} as const;

// CSS variable names for theme switching
export const cssVariables = {
  // Backgrounds
  '--background': 'background-default',
  '--background-paper': 'background-paper',
  '--background-subtle': 'background-subtle',
  '--background-muted': 'background-muted',
  '--background-elevated': 'background-elevated',

  // Foreground
  '--foreground': 'foreground-default',
  '--foreground-muted': 'foreground-muted',
  '--foreground-subtle': 'foreground-subtle',

  // Border
  '--border': 'border-default',
  '--border-muted': 'border-muted',
  '--border-strong': 'border-strong',

  // Primary
  '--primary': 'primary-default',
  '--primary-hover': 'primary-hover',
  '--primary-foreground': 'primary-foreground',

  // Secondary
  '--secondary': 'secondary-default',
  '--secondary-hover': 'secondary-hover',
  '--secondary-foreground': 'secondary-foreground',

  // Status
  '--success': 'success-default',
  '--success-light': 'success-light',
  '--warning': 'warning-default',
  '--warning-light': 'warning-light',
  '--error': 'error-default',
  '--error-light': 'error-light',
  '--info': 'info-default',
  '--info-light': 'info-light',
} as const;

export type ThemeColors = typeof lightTheme;
export type ColorScale = typeof baseColors.primary;
