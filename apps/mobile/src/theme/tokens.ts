export const colors = {
  background: "#F8F1E7",
  surface: "#FFF9F0",
  surfaceStrong: "#F3E3CF",
  primary: "#E86F2C",
  primaryPressed: "#C95722",
  sage: "#6F8F72",
  moss: "#355E3B",
  clay: "#D8C3A5",
  ink: "#27221D",
  muted: "#74685C",
  white: "#FFFFFF",
  error: "#A7432D",
} as const;

export const spacing = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 24,
  xxl: 32,
} as const;

export const radius = {
  sm: 12,
  md: 18,
  lg: 26,
  pill: 999,
} as const;

export const typography = {
  title: {
    fontSize: 34,
    lineHeight: 40,
    fontWeight: "800" as const,
    color: colors.ink,
  },
  heading: {
    fontSize: 24,
    lineHeight: 30,
    fontWeight: "800" as const,
    color: colors.ink,
  },
  subheading: {
    fontSize: 18,
    lineHeight: 24,
    fontWeight: "700" as const,
    color: colors.ink,
  },
  body: {
    fontSize: 16,
    lineHeight: 24,
    fontWeight: "400" as const,
    color: colors.ink,
  },
  caption: {
    fontSize: 13,
    lineHeight: 18,
    fontWeight: "600" as const,
    color: colors.muted,
  },
} as const;

export const shadows = {
  card: {
    shadowColor: "#6A4B2B",
    shadowOffset: { width: 0, height: 12 },
    shadowOpacity: 0.08,
    shadowRadius: 24,
    elevation: 4,
  },
} as const;
