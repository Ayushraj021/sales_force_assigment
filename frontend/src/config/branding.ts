/**
 * White-Label Branding Configuration
 *
 * Centralized configuration for customizing the platform's appearance and branding.
 */

export interface BrandColors {
  primary: string;
  primaryForeground: string;
  secondary: string;
  secondaryForeground: string;
  accent: string;
  accentForeground: string;
  background: string;
  foreground: string;
  muted: string;
  mutedForeground: string;
  card: string;
  cardForeground: string;
  border: string;
  destructive: string;
  destructiveForeground: string;
  success: string;
  successForeground: string;
  warning: string;
  warningForeground: string;
}

export interface BrandColorScheme {
  light: BrandColors;
  dark: BrandColors;
}

export interface BrandLogo {
  src: string;
  alt: string;
  width?: number;
  height?: number;
}

export interface BrandTypography {
  fontFamily: string;
  headingFontFamily?: string;
  monoFontFamily?: string;
  baseFontSize: string;
  fontWeightNormal: number;
  fontWeightMedium: number;
  fontWeightSemibold: number;
  fontWeightBold: number;
}

export interface BrandNavigation {
  showLogo: boolean;
  showOrgName: boolean;
  collapsible: boolean;
  defaultCollapsed: boolean;
}

export interface BrandFooter {
  show: boolean;
  text?: string;
  links?: Array<{
    label: string;
    href: string;
    external?: boolean;
  }>;
  showPoweredBy: boolean;
}

export interface BrandFeatureFlags {
  showDarkModeToggle: boolean;
  showLanguageSelector: boolean;
  showUserAvatar: boolean;
  showNotifications: boolean;
  showSearchBar: boolean;
  enableKeyboardShortcuts: boolean;
  enableCommandPalette: boolean;
  enableExports: boolean;
  enableSharing: boolean;
}

export interface BrandingConfig {
  // Basic info
  name: string;
  tagline?: string;
  description?: string;
  version?: string;

  // Domain and URLs
  domain?: string;
  supportUrl?: string;
  documentationUrl?: string;
  privacyPolicyUrl?: string;
  termsOfServiceUrl?: string;

  // Visual identity
  logo: BrandLogo;
  logoCompact?: BrandLogo;
  favicon?: string;
  appleTouchIcon?: string;

  // Colors
  colors: BrandColorScheme;

  // Typography
  typography: BrandTypography;

  // Navigation
  navigation: BrandNavigation;

  // Footer
  footer: BrandFooter;

  // Features
  features: BrandFeatureFlags;

  // Custom CSS classes
  customClasses?: Record<string, string>;

  // Custom meta tags
  metaTags?: Array<{
    name: string;
    content: string;
  }>;

  // Analytics
  analytics?: {
    googleAnalyticsId?: string;
    mixpanelToken?: string;
    segmentWriteKey?: string;
  };
}

/**
 * Default branding configuration
 */
export const defaultBranding: BrandingConfig = {
  name: "Marketing Analytics Platform",
  tagline: "Data-driven marketing decisions",
  description: "Comprehensive marketing analytics and forecasting platform",
  version: "1.0.0",

  logo: {
    src: "/logo.svg",
    alt: "Marketing Analytics Platform",
    width: 150,
    height: 40,
  },
  logoCompact: {
    src: "/logo-icon.svg",
    alt: "MAP",
    width: 32,
    height: 32,
  },
  favicon: "/favicon.ico",
  appleTouchIcon: "/apple-touch-icon.png",

  colors: {
    light: {
      primary: "hsl(220, 90%, 56%)",
      primaryForeground: "hsl(0, 0%, 100%)",
      secondary: "hsl(220, 14%, 96%)",
      secondaryForeground: "hsl(220, 9%, 46%)",
      accent: "hsl(262, 83%, 58%)",
      accentForeground: "hsl(0, 0%, 100%)",
      background: "hsl(0, 0%, 100%)",
      foreground: "hsl(224, 71%, 4%)",
      muted: "hsl(220, 14%, 96%)",
      mutedForeground: "hsl(220, 9%, 46%)",
      card: "hsl(0, 0%, 100%)",
      cardForeground: "hsl(224, 71%, 4%)",
      border: "hsl(220, 13%, 91%)",
      destructive: "hsl(0, 84%, 60%)",
      destructiveForeground: "hsl(0, 0%, 100%)",
      success: "hsl(142, 76%, 36%)",
      successForeground: "hsl(0, 0%, 100%)",
      warning: "hsl(38, 92%, 50%)",
      warningForeground: "hsl(0, 0%, 0%)",
    },
    dark: {
      primary: "hsl(217, 91%, 60%)",
      primaryForeground: "hsl(0, 0%, 100%)",
      secondary: "hsl(217, 33%, 17%)",
      secondaryForeground: "hsl(215, 20%, 65%)",
      accent: "hsl(262, 83%, 68%)",
      accentForeground: "hsl(0, 0%, 100%)",
      background: "hsl(224, 71%, 4%)",
      foreground: "hsl(213, 31%, 91%)",
      muted: "hsl(217, 33%, 17%)",
      mutedForeground: "hsl(215, 20%, 65%)",
      card: "hsl(224, 71%, 4%)",
      cardForeground: "hsl(213, 31%, 91%)",
      border: "hsl(216, 34%, 17%)",
      destructive: "hsl(0, 62%, 50%)",
      destructiveForeground: "hsl(0, 0%, 100%)",
      success: "hsl(142, 70%, 45%)",
      successForeground: "hsl(0, 0%, 100%)",
      warning: "hsl(38, 92%, 50%)",
      warningForeground: "hsl(0, 0%, 0%)",
    },
  },

  typography: {
    fontFamily: "Inter, system-ui, sans-serif",
    headingFontFamily: "Inter, system-ui, sans-serif",
    monoFontFamily: "JetBrains Mono, monospace",
    baseFontSize: "16px",
    fontWeightNormal: 400,
    fontWeightMedium: 500,
    fontWeightSemibold: 600,
    fontWeightBold: 700,
  },

  navigation: {
    showLogo: true,
    showOrgName: true,
    collapsible: true,
    defaultCollapsed: false,
  },

  footer: {
    show: true,
    text: "Marketing Analytics Platform",
    links: [
      { label: "Documentation", href: "/docs", external: false },
      { label: "Support", href: "/support", external: false },
      { label: "Privacy", href: "/privacy", external: false },
    ],
    showPoweredBy: true,
  },

  features: {
    showDarkModeToggle: true,
    showLanguageSelector: false,
    showUserAvatar: true,
    showNotifications: true,
    showSearchBar: true,
    enableKeyboardShortcuts: true,
    enableCommandPalette: true,
    enableExports: true,
    enableSharing: true,
  },

  metaTags: [
    { name: "theme-color", content: "#3b82f6" },
    { name: "apple-mobile-web-app-capable", content: "yes" },
  ],
};

/**
 * Sample white-label configurations for different clients
 */
export const clientBrandings: Record<string, Partial<BrandingConfig>> = {
  acme: {
    name: "ACME Analytics",
    tagline: "Powered by ACME Corp",
    logo: {
      src: "/clients/acme/logo.svg",
      alt: "ACME Analytics",
    },
    colors: {
      light: {
        ...defaultBranding.colors.light,
        primary: "hsl(340, 82%, 52%)",
        accent: "hsl(340, 82%, 42%)",
      },
      dark: {
        ...defaultBranding.colors.dark,
        primary: "hsl(340, 82%, 62%)",
        accent: "hsl(340, 82%, 52%)",
      },
    },
    footer: {
      ...defaultBranding.footer,
      text: "ACME Corporation",
      showPoweredBy: false,
    },
  },

  enterprise: {
    name: "Enterprise Analytics Suite",
    tagline: "Enterprise-grade marketing intelligence",
    logo: {
      src: "/clients/enterprise/logo.svg",
      alt: "Enterprise Analytics",
    },
    colors: {
      light: {
        ...defaultBranding.colors.light,
        primary: "hsl(210, 100%, 35%)",
        accent: "hsl(210, 100%, 45%)",
      },
      dark: {
        ...defaultBranding.colors.dark,
        primary: "hsl(210, 100%, 50%)",
        accent: "hsl(210, 100%, 60%)",
      },
    },
    features: {
      ...defaultBranding.features,
      showLanguageSelector: true,
    },
  },
};

/**
 * Branding manager class
 */
export class BrandingManager {
  private config: BrandingConfig;
  private styleElement: HTMLStyleElement | null = null;

  constructor(config: Partial<BrandingConfig> = {}) {
    this.config = this.mergeConfig(defaultBranding, config);
  }

  /**
   * Merge custom config with defaults
   */
  private mergeConfig(
    defaults: BrandingConfig,
    overrides: Partial<BrandingConfig>
  ): BrandingConfig {
    return {
      ...defaults,
      ...overrides,
      colors: {
        light: {
          ...defaults.colors.light,
          ...(overrides.colors?.light || {}),
        },
        dark: {
          ...defaults.colors.dark,
          ...(overrides.colors?.dark || {}),
        },
      },
      typography: {
        ...defaults.typography,
        ...(overrides.typography || {}),
      },
      navigation: {
        ...defaults.navigation,
        ...(overrides.navigation || {}),
      },
      footer: {
        ...defaults.footer,
        ...(overrides.footer || {}),
      },
      features: {
        ...defaults.features,
        ...(overrides.features || {}),
      },
    };
  }

  /**
   * Get current branding config
   */
  getConfig(): BrandingConfig {
    return this.config;
  }

  /**
   * Update branding config
   */
  updateConfig(config: Partial<BrandingConfig>): void {
    this.config = this.mergeConfig(this.config, config);
    this.applyBranding();
  }

  /**
   * Apply branding to the document
   */
  applyBranding(): void {
    this.applyColors();
    this.applyTypography();
    this.applyFavicon();
    this.applyMetaTags();
    this.applyTitle();
  }

  /**
   * Apply color scheme
   */
  private applyColors(): void {
    const root = document.documentElement;
    const isDark = root.classList.contains("dark");
    const colors = isDark ? this.config.colors.dark : this.config.colors.light;

    Object.entries(colors).forEach(([key, value]) => {
      const cssVar = `--${key.replace(/([A-Z])/g, "-$1").toLowerCase()}`;
      root.style.setProperty(cssVar, value);
    });
  }

  /**
   * Apply typography settings
   */
  private applyTypography(): void {
    const { typography } = this.config;
    const root = document.documentElement;

    root.style.setProperty("--font-family", typography.fontFamily);
    root.style.setProperty(
      "--font-family-heading",
      typography.headingFontFamily || typography.fontFamily
    );
    root.style.setProperty(
      "--font-family-mono",
      typography.monoFontFamily || "monospace"
    );
    root.style.setProperty("--font-size-base", typography.baseFontSize);
  }

  /**
   * Apply favicon
   */
  private applyFavicon(): void {
    if (!this.config.favicon) return;

    let link = document.querySelector(
      'link[rel="icon"]'
    ) as HTMLLinkElement | null;

    if (!link) {
      link = document.createElement("link");
      link.rel = "icon";
      document.head.appendChild(link);
    }

    link.href = this.config.favicon;
  }

  /**
   * Apply meta tags
   */
  private applyMetaTags(): void {
    this.config.metaTags?.forEach(({ name, content }) => {
      let meta = document.querySelector(
        `meta[name="${name}"]`
      ) as HTMLMetaElement | null;

      if (!meta) {
        meta = document.createElement("meta");
        meta.name = name;
        document.head.appendChild(meta);
      }

      meta.content = content;
    });
  }

  /**
   * Apply document title
   */
  private applyTitle(): void {
    document.title = this.config.name;
  }

  /**
   * Generate CSS variables string
   */
  generateCSSVariables(isDark: boolean = false): string {
    const colors = isDark ? this.config.colors.dark : this.config.colors.light;
    const { typography } = this.config;

    const colorVars = Object.entries(colors)
      .map(([key, value]) => {
        const cssVar = `--${key.replace(/([A-Z])/g, "-$1").toLowerCase()}`;
        return `  ${cssVar}: ${value};`;
      })
      .join("\n");

    return `
:root {
${colorVars}
  --font-family: ${typography.fontFamily};
  --font-family-heading: ${typography.headingFontFamily || typography.fontFamily};
  --font-family-mono: ${typography.monoFontFamily || "monospace"};
  --font-size-base: ${typography.baseFontSize};
}
    `.trim();
  }
}

/**
 * Hook for using branding in React components
 */
let brandingManagerInstance: BrandingManager | null = null;

export function getBrandingManager(
  config?: Partial<BrandingConfig>
): BrandingManager {
  if (!brandingManagerInstance) {
    brandingManagerInstance = new BrandingManager(config);
  }
  return brandingManagerInstance;
}

export function resetBrandingManager(): void {
  brandingManagerInstance = null;
}

/**
 * Load branding config from API
 */
export async function loadBrandingFromAPI(
  orgId: string
): Promise<BrandingConfig> {
  try {
    const response = await fetch(`/api/organizations/${orgId}/branding`);
    if (!response.ok) {
      throw new Error("Failed to load branding");
    }
    const data = await response.json();
    return getBrandingManager().getConfig();
  } catch (error) {
    console.warn("Failed to load branding, using defaults:", error);
    return defaultBranding;
  }
}

export default BrandingManager;
