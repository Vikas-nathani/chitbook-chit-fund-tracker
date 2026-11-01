/** Design tokens. Use these instead of raw colours/sizes in components. */
export const colors = {
  bg: '#f5f6fb',
  surface: '#ffffff',
  surfaceMuted: '#f1f2f8',
  border: '#e3e5ef',
  text: '#16182b',
  textMuted: '#6b7085',
  primary: '#4f46e5',
  primarySoft: '#eef0ff',
  onPrimary: '#ffffff',
  profit: '#059669',
  profitSoft: '#e7f8f1',
  loss: '#e11d48',
  lossSoft: '#fdecef',
  warning: '#d97706',
  warningSoft: '#fff5e6',
  overdue: '#dc2626',
  paid: '#059669',
  pending: '#9ca3af',
  overlay: 'rgba(15, 17, 35, 0.45)',
  tiles: {
    indigo: '#eef0ff',
    violet: '#f3efff',
    amber: '#fff5e6',
    emerald: '#e7f8f1',
    rose: '#fdecef',
  },
  accents: ['#6366f1', '#ec4899', '#10b981', '#f59e0b', '#06b6d4', '#8b5cf6'],
} as const;

export const space = { xs: 4, sm: 8, md: 12, lg: 16, xl: 24, xxl: 32 } as const;
export const radius = { sm: 8, md: 12, lg: 16, pill: 999 } as const;
export const font = {
  xs: 12,
  sm: 13,
  md: 15,
  lg: 17,
  xl: 22,
  xxl: 28,
  regular: '400',
  medium: '500',
  semibold: '600',
  bold: '700',
} as const;

/** Minimum touch target (Apple HIG 44pt, Material 48dp). */
export const TOUCH = 48;

export const shadow = {
  shadowColor: '#1a1d3a',
  shadowOpacity: 0.06,
  shadowRadius: 12,
  shadowOffset: { width: 0, height: 4 },
  elevation: 2,
} as const;
