/**
 * Design System Spacing Tokens
 *
 * A consistent spacing scale based on 4px increments.
 * Follows a t-shirt sizing naming convention for ease of use.
 */

// Base spacing unit (4px)
const BASE_UNIT = 4;

// Spacing scale in pixels
export const spacing = {
  px: '1px',
  0: '0',
  0.5: `${BASE_UNIT * 0.5}px`,   // 2px
  1: `${BASE_UNIT * 1}px`,       // 4px
  1.5: `${BASE_UNIT * 1.5}px`,   // 6px
  2: `${BASE_UNIT * 2}px`,       // 8px
  2.5: `${BASE_UNIT * 2.5}px`,   // 10px
  3: `${BASE_UNIT * 3}px`,       // 12px
  3.5: `${BASE_UNIT * 3.5}px`,   // 14px
  4: `${BASE_UNIT * 4}px`,       // 16px
  5: `${BASE_UNIT * 5}px`,       // 20px
  6: `${BASE_UNIT * 6}px`,       // 24px
  7: `${BASE_UNIT * 7}px`,       // 28px
  8: `${BASE_UNIT * 8}px`,       // 32px
  9: `${BASE_UNIT * 9}px`,       // 36px
  10: `${BASE_UNIT * 10}px`,     // 40px
  11: `${BASE_UNIT * 11}px`,     // 44px
  12: `${BASE_UNIT * 12}px`,     // 48px
  14: `${BASE_UNIT * 14}px`,     // 56px
  16: `${BASE_UNIT * 16}px`,     // 64px
  20: `${BASE_UNIT * 20}px`,     // 80px
  24: `${BASE_UNIT * 24}px`,     // 96px
  28: `${BASE_UNIT * 28}px`,     // 112px
  32: `${BASE_UNIT * 32}px`,     // 128px
  36: `${BASE_UNIT * 36}px`,     // 144px
  40: `${BASE_UNIT * 40}px`,     // 160px
  44: `${BASE_UNIT * 44}px`,     // 176px
  48: `${BASE_UNIT * 48}px`,     // 192px
  52: `${BASE_UNIT * 52}px`,     // 208px
  56: `${BASE_UNIT * 56}px`,     // 224px
  60: `${BASE_UNIT * 60}px`,     // 240px
  64: `${BASE_UNIT * 64}px`,     // 256px
  72: `${BASE_UNIT * 72}px`,     // 288px
  80: `${BASE_UNIT * 80}px`,     // 320px
  96: `${BASE_UNIT * 96}px`,     // 384px
} as const;

// Semantic spacing for common use cases
export const semanticSpacing = {
  // Component internal padding
  component: {
    xs: spacing[1],    // 4px - tight elements
    sm: spacing[2],    // 8px - small buttons, badges
    md: spacing[3],    // 12px - default button padding
    lg: spacing[4],    // 16px - cards, containers
    xl: spacing[6],    // 24px - large containers
  },

  // Gaps between elements
  gap: {
    xs: spacing[1],    // 4px - icon spacing
    sm: spacing[2],    // 8px - inline elements
    md: spacing[4],    // 16px - standard gap
    lg: spacing[6],    // 24px - section gap
    xl: spacing[8],    // 32px - large section gap
    '2xl': spacing[12], // 48px - page sections
  },

  // Layout margins
  layout: {
    page: spacing[6],      // 24px - page margins on mobile
    pageDesktop: spacing[8], // 32px - page margins on desktop
    section: spacing[8],   // 32px - between sections
    container: spacing[4], // 16px - container padding
  },

  // Input/form spacing
  form: {
    fieldGap: spacing[4],      // 16px - between form fields
    labelGap: spacing[1.5],    // 6px - between label and input
    helpTextGap: spacing[1],   // 4px - between input and help text
    groupGap: spacing[6],      // 24px - between field groups
  },

  // Card/panel spacing
  card: {
    padding: spacing[4],       // 16px - card content padding
    paddingLg: spacing[6],     // 24px - large card padding
    gap: spacing[3],           // 12px - between card sections
    headerPadding: spacing[4], // 16px - card header padding
  },

  // Modal/dialog spacing
  modal: {
    padding: spacing[6],       // 24px - modal content padding
    headerGap: spacing[4],     // 16px - after header
    footerGap: spacing[4],     // 16px - before footer
    actionGap: spacing[3],     // 12px - between action buttons
  },

  // Table spacing
  table: {
    cellPadding: spacing[3],   // 12px - table cell padding
    cellPaddingCompact: spacing[2], // 8px - compact table
    headerPadding: spacing[3], // 12px - header cell padding
    rowGap: spacing[2],        // 8px - between rows (if any)
  },

  // Sidebar/navigation
  navigation: {
    itemPadding: spacing[3],   // 12px - nav item padding
    groupGap: spacing[4],      // 16px - between nav groups
    iconGap: spacing[3],       // 12px - between icon and text
  },
} as const;

// Border radius scale
export const radius = {
  none: '0',
  sm: '4px',
  md: '6px',
  lg: '8px',
  xl: '12px',
  '2xl': '16px',
  '3xl': '24px',
  full: '9999px',
} as const;

// Semantic border radius
export const semanticRadius = {
  button: radius.md,
  input: radius.md,
  card: radius.lg,
  modal: radius.xl,
  badge: radius.full,
  avatar: radius.full,
  tooltip: radius.md,
  dropdown: radius.lg,
  chip: radius.full,
} as const;

// Z-index scale
export const zIndex = {
  behind: -1,
  base: 0,
  dropdown: 50,
  sticky: 100,
  fixed: 150,
  overlay: 200,
  modal: 300,
  popover: 400,
  tooltip: 500,
  toast: 600,
  maximum: 9999,
} as const;

// Breakpoints for responsive design
export const breakpoints = {
  xs: '480px',
  sm: '640px',
  md: '768px',
  lg: '1024px',
  xl: '1280px',
  '2xl': '1536px',
} as const;

// Container max-widths
export const containers = {
  xs: '480px',
  sm: '640px',
  md: '768px',
  lg: '1024px',
  xl: '1280px',
  '2xl': '1536px',
  full: '100%',
} as const;

// Sidebar widths
export const sidebarWidths = {
  collapsed: '64px',
  default: '256px',
  expanded: '320px',
} as const;

export type Spacing = typeof spacing;
export type Radius = typeof radius;
export type ZIndex = typeof zIndex;
