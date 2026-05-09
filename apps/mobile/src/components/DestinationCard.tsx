import { Pressable, StyleSheet, Text, View } from "react-native";

import type { Destination } from "../api/types";
import { colors, radius, shadows, spacing, typography } from "../theme/tokens";
import { Pill } from "./Pill";

type DestinationCardProps = {
  destination: Destination;
  onPress: () => void;
};

export function DestinationCard({ destination, onPress }: DestinationCardProps) {
  return (
    <Pressable accessibilityRole="button" onPress={onPress} style={styles.card}>
      <View style={styles.imagePlaceholder}>
        <Text style={styles.imageText}>{destination.city.slice(0, 2).toUpperCase()}</Text>
      </View>
      <View style={styles.body}>
        <Text style={styles.title}>{destination.city}, {destination.country}</Text>
        <Text style={styles.summary}>{destination.summary}</Text>
        <View style={styles.pills}>
          {destination.vibes.slice(0, 3).map((vibe) => (
            <Pill key={vibe} label={vibe} tone="sage" />
          ))}
        </View>
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.surface,
    borderColor: colors.clay,
    borderRadius: radius.lg,
    borderWidth: 1,
    overflow: "hidden",
    ...shadows.card,
  },
  imagePlaceholder: {
    alignItems: "center",
    backgroundColor: colors.moss,
    height: 156,
    justifyContent: "center",
  },
  imageText: {
    color: colors.background,
    fontSize: 48,
    fontWeight: "900",
    letterSpacing: 2,
  },
  body: {
    gap: spacing.sm,
    padding: spacing.lg,
  },
  title: {
    ...typography.subheading,
  },
  summary: {
    ...typography.body,
    color: colors.muted,
  },
  pills: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.sm,
    paddingTop: spacing.xs,
  },
});
