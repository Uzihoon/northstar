import { StyleSheet, Text, View } from "react-native";

import type { MobilePlanCard } from "../api/types";
import { colors, radius, shadows, spacing, typography } from "../theme/tokens";
import { Pill } from "./Pill";

type ItineraryCardProps = {
  card: MobilePlanCard;
};

export function ItineraryCard({ card }: ItineraryCardProps) {
  return (
    <View style={styles.card}>
      <View style={styles.header}>
        <Text style={styles.time}>{card.time}</Text>
        <Pill label={card.kind} tone={card.kind === "meal" || card.kind === "cafe" ? "orange" : "sage"} />
      </View>
      <Text style={styles.title}>{card.title}</Text>
      {card.area ? <Text style={styles.area}>{card.area}</Text> : null}
      <Text style={styles.description}>{card.description}</Text>
      <View style={styles.tags}>
        {card.tags.slice(1, 5).map((tag) => (
          <Pill key={tag} label={tag} />
        ))}
      </View>
      {card.options.length > 0 ? (
        <View style={styles.options}>
          {card.options.map((option) => (
            <View key={`${option.category}-${option.name}`} style={styles.option}>
              <Text style={styles.optionName}>{option.name}</Text>
              <Text style={styles.optionMeta}>{option.category}{option.estimated_cost ? ` - ${option.estimated_cost}` : ""}</Text>
              <Text style={styles.optionWhy}>{option.why_it_fits}</Text>
            </View>
          ))}
        </View>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.surface,
    borderColor: colors.clay,
    borderRadius: radius.lg,
    borderWidth: 1,
    gap: spacing.sm,
    padding: spacing.lg,
    ...shadows.card,
  },
  header: {
    alignItems: "center",
    flexDirection: "row",
    justifyContent: "space-between",
  },
  time: {
    ...typography.caption,
    color: colors.primaryPressed,
  },
  title: {
    ...typography.subheading,
  },
  area: {
    ...typography.caption,
    color: colors.moss,
  },
  description: {
    ...typography.body,
    color: colors.muted,
  },
  tags: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.sm,
  },
  options: {
    borderTopColor: colors.clay,
    borderTopWidth: 1,
    gap: spacing.sm,
    marginTop: spacing.sm,
    paddingTop: spacing.md,
  },
  option: {
    backgroundColor: "#F8EAD8",
    borderRadius: radius.md,
    gap: spacing.xs,
    padding: spacing.md,
  },
  optionName: {
    ...typography.body,
    fontWeight: "800",
  },
  optionMeta: {
    ...typography.caption,
    color: colors.moss,
  },
  optionWhy: {
    ...typography.caption,
    color: colors.muted,
  },
});
