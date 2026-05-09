import { router, useLocalSearchParams } from "expo-router";
import { useEffect, useState } from "react";
import { ActivityIndicator, StyleSheet, Text, View } from "react-native";

import { getPlanSummary } from "../../src/api/client";
import type { MobilePlanSummary } from "../../src/api/types";
import { ItineraryCard } from "../../src/components/ItineraryCard";
import { Pill } from "../../src/components/Pill";
import { PrimaryButton } from "../../src/components/PrimaryButton";
import { Screen } from "../../src/components/Screen";
import { colors, radius, shadows, spacing, typography } from "../../src/theme/tokens";

function firstParam(value: string | string[] | undefined): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}

export default function PlanSummaryScreen() {
  const params = useLocalSearchParams();
  const planId = firstParam(params.id);

  const [plan, setPlan] = useState<MobilePlanSummary | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;

    async function loadPlan() {
      if (!planId) {
        setErrorMessage("Plan id is missing.");
        setIsLoading(false);
        return;
      }

      try {
        const data = await getPlanSummary(planId);
        if (isMounted) {
          setPlan(data);
          setErrorMessage(null);
        }
      } catch (error) {
        if (isMounted) {
          setErrorMessage(error instanceof Error ? error.message : "Could not load itinerary.");
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    loadPlan();

    return () => {
      isMounted = false;
    };
  }, [planId]);

  if (isLoading) {
    return (
      <Screen>
        <View style={styles.stateCard}>
          <ActivityIndicator color={colors.primary} />
          <Text style={styles.stateText}>Opening itinerary...</Text>
        </View>
      </Screen>
    );
  }

  if (!plan) {
    return (
      <Screen>
        <View style={styles.stateCard}>
          <Text style={styles.stateTitle}>Plan unavailable</Text>
          <Text style={styles.stateText}>{errorMessage}</Text>
          <PrimaryButton label="Back to explore" onPress={() => router.replace("/")} />
        </View>
      </Screen>
    );
  }

  return (
    <Screen>
      <View style={styles.hero}>
        <View style={styles.statusRow}>
          <Pill
            label={plan.status === "ready_with_warnings" ? "Ready with notes" : "Ready"}
            tone={plan.status === "ready_with_warnings" ? "orange" : "sage"}
          />
          <Text style={styles.duration}>{plan.duration_days} days</Text>
        </View>
        <Text style={styles.title}>{plan.title}</Text>
        <Text style={styles.destination}>{plan.destination}</Text>
        <View style={styles.highlights}>
          {plan.highlights.slice(0, 8).map((highlight) => (
            <Pill key={highlight} label={highlight} tone="sage" />
          ))}
        </View>
      </View>

      {plan.quality.issue_count > 0 ? (
        <View style={styles.qualityCard}>
          <Text style={styles.qualityTitle}>Internal quality notes hidden from traveler view</Text>
          <Text style={styles.qualityText}>
            {plan.quality.issue_count} soft validation issue{plan.quality.issue_count === 1 ? "" : "s"} logged for later model improvement.
          </Text>
        </View>
      ) : null}

      {plan.days.map((day) => (
        <View key={day.day_number} style={styles.daySection}>
          <View style={styles.dayHeader}>
            <Text style={styles.dayKicker}>Day {day.day_number}</Text>
            <Text style={styles.dayTitle}>{day.theme}</Text>
          </View>
          <View style={styles.cards}>
            {day.cards.map((card, index) => (
              <ItineraryCard key={`${card.time}-${card.title}-${index}`} card={card} />
            ))}
          </View>
        </View>
      ))}

      <PrimaryButton label="Back to explore" onPress={() => router.replace("/")} tone="secondary" />
    </Screen>
  );
}

const styles = StyleSheet.create({
  hero: {
    backgroundColor: "#FCE3C8",
    borderColor: colors.clay,
    borderRadius: radius.lg,
    borderWidth: 1,
    gap: spacing.md,
    padding: spacing.xl,
    ...shadows.card,
  },
  statusRow: {
    alignItems: "center",
    flexDirection: "row",
    justifyContent: "space-between",
  },
  duration: {
    ...typography.caption,
    color: colors.primaryPressed,
  },
  title: {
    ...typography.title,
  },
  destination: {
    ...typography.subheading,
    color: colors.moss,
  },
  highlights: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.sm,
  },
  qualityCard: {
    backgroundColor: colors.surface,
    borderColor: colors.clay,
    borderRadius: radius.lg,
    borderWidth: 1,
    gap: spacing.sm,
    padding: spacing.lg,
  },
  qualityTitle: {
    ...typography.subheading,
  },
  qualityText: {
    ...typography.body,
    color: colors.muted,
  },
  daySection: {
    gap: spacing.md,
  },
  dayHeader: {
    gap: spacing.xs,
  },
  dayKicker: {
    ...typography.caption,
    color: colors.primaryPressed,
    textTransform: "uppercase",
  },
  dayTitle: {
    ...typography.heading,
  },
  cards: {
    gap: spacing.md,
  },
  stateCard: {
    alignItems: "center",
    backgroundColor: colors.surface,
    borderColor: colors.clay,
    borderRadius: radius.lg,
    borderWidth: 1,
    gap: spacing.md,
    padding: spacing.xl,
  },
  stateTitle: {
    ...typography.heading,
  },
  stateText: {
    ...typography.body,
    color: colors.muted,
    textAlign: "center",
  },
});
