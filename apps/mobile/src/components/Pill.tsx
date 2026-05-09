import { StyleSheet, Text, View } from "react-native";

import { colors, radius, spacing, typography } from "../theme/tokens";

type PillProps = {
  label: string;
  tone?: "sage" | "orange" | "neutral";
};

export function Pill({ label, tone = "neutral" }: PillProps) {
  return (
    <View style={[styles.pill, styles[tone]]}>
      <Text style={[styles.label, tone === "orange" && styles.orangeLabel]}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  pill: {
    alignSelf: "flex-start",
    borderRadius: radius.pill,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
  },
  neutral: {
    backgroundColor: colors.surfaceStrong,
  },
  sage: {
    backgroundColor: "#E1E9DA",
  },
  orange: {
    backgroundColor: "#F7D4BD",
  },
  label: {
    ...typography.caption,
    color: colors.moss,
  },
  orangeLabel: {
    color: colors.primaryPressed,
  },
});
