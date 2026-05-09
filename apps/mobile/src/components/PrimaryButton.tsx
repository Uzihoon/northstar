import { Pressable, StyleSheet, Text } from "react-native";

import { colors, radius, spacing, typography } from "../theme/tokens";

type PrimaryButtonProps = {
  label: string;
  onPress: () => void;
  disabled?: boolean;
  tone?: "primary" | "secondary";
};

export function PrimaryButton({
  label,
  onPress,
  disabled = false,
  tone = "primary",
}: PrimaryButtonProps) {
  return (
    <Pressable
      accessibilityRole="button"
      disabled={disabled}
      onPress={onPress}
      style={({ pressed }) => [
        styles.button,
        tone === "secondary" && styles.secondary,
        pressed && !disabled && (tone === "secondary" ? styles.secondaryPressed : styles.pressed),
        disabled && styles.disabled,
      ]}
    >
      <Text style={[styles.label, tone === "secondary" && styles.secondaryLabel]}>{label}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  button: {
    alignItems: "center",
    backgroundColor: colors.primary,
    borderRadius: radius.pill,
    minHeight: 52,
    justifyContent: "center",
    paddingHorizontal: spacing.xl,
    paddingVertical: spacing.md,
  },
  secondary: {
    backgroundColor: colors.surface,
    borderColor: colors.clay,
    borderWidth: 1,
  },
  pressed: {
    backgroundColor: colors.primaryPressed,
  },
  secondaryPressed: {
    backgroundColor: colors.surfaceStrong,
  },
  disabled: {
    opacity: 0.55,
  },
  label: {
    ...typography.body,
    color: colors.white,
    fontWeight: "800",
  },
  secondaryLabel: {
    color: colors.moss,
  },
});
