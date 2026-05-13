import { Redirect, router } from "expo-router";
import { useEffect, useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";

import { listSavedPlans } from "../src/api/client";
import type { SavedPlanSummary } from "../src/api/types";
import { useAuth } from "../src/auth/AuthContext";
import { AppTabBar } from "../src/components/AppTabBar";
import { PrimaryButton } from "../src/components/PrimaryButton";
import { Screen } from "../src/components/Screen";
import { colors, radius, shadows, spacing, typography } from "../src/theme/tokens";

export default function ItinerariesScreen() {
  const { isAuthenticated } = useAuth();
  const [plans, setPlans] = useState<SavedPlanSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;

    async function loadPlans() {
      try {
        const data = await listSavedPlans();
        if (isMounted) {
          setPlans(data);
          setErrorMessage(null);
        }
      } catch (error) {
        if (isMounted) {
          setErrorMessage(error instanceof Error ? error.message : "Could not load saved itineraries.");
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    if (isAuthenticated) {
      loadPlans();
    }

    return () => {
      isMounted = false;
    };
  }, [isAuthenticated]);

  if (!isAuthenticated) {
    return <Redirect href="/onboarding" />;
  }

  return (
    <Screen scroll={false}>
      <View style={styles.container}>
        <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
          <View>
            <Text style={styles.kicker}>Previous itineraries</Text>
            <Text style={styles.title}>Pick up where Nori left off.</Text>
          </View>

          {isLoading ? (
            <View style={styles.stateCard}>
              <ActivityIndicator color={colors.primary} />
              <Text style={styles.stateText}>Loading saved trips...</Text>
            </View>
          ) : null}

          {errorMessage ? (
            <View style={styles.stateCard}>
              <Text style={styles.stateTitle}>Could not load trips</Text>
              <Text style={styles.stateText}>{errorMessage}</Text>
            </View>
          ) : null}

          {!isLoading && !errorMessage && plans.length === 0 ? (
            <View style={styles.emptyCard}>
              <Text style={styles.stateTitle}>No saved plans yet</Text>
              <Text style={styles.stateText}>
                Choose a destination and start an itinerary. Saved plans will show up here.
              </Text>
              <PrimaryButton label="Explore destinations" onPress={() => router.replace("/")} />
            </View>
          ) : null}

          <View style={styles.planList}>
            {plans.map((plan) => (
              <Pressable
                accessibilityRole="button"
                key={plan.plan_id}
                onPress={() => router.push({
                  pathname: "/plans/[id]",
                  params: { id: plan.plan_id },
                })}
                style={styles.planCard}
              >
                <Text style={styles.planDestination}>{plan.destination}</Text>
                <Text style={styles.planTitle}>{plan.title}</Text>
                <Text style={styles.planPrompt}>{plan.original_prompt}</Text>
              </Pressable>
            ))}
          </View>
        </ScrollView>

        <AppTabBar active="trips" />
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    gap: spacing.md,
  },
  content: {
    gap: spacing.lg,
    paddingBottom: spacing.md,
  },
  kicker: {
    ...typography.caption,
    color: colors.primaryPressed,
    textTransform: "uppercase",
  },
  title: {
    ...typography.title,
    marginTop: spacing.xs,
  },
  stateCard: {
    alignItems: "center",
    backgroundColor: colors.surface,
    borderColor: colors.clay,
    borderRadius: radius.lg,
    borderWidth: 1,
    gap: spacing.sm,
    padding: spacing.xl,
  },
  emptyCard: {
    backgroundColor: colors.surface,
    borderColor: colors.clay,
    borderRadius: radius.lg,
    borderWidth: 1,
    gap: spacing.md,
    padding: spacing.xl,
    ...shadows.card,
  },
  stateTitle: {
    ...typography.heading,
  },
  stateText: {
    ...typography.body,
    color: colors.muted,
  },
  planList: {
    gap: spacing.md,
  },
  planCard: {
    backgroundColor: colors.surface,
    borderColor: colors.clay,
    borderRadius: radius.lg,
    borderWidth: 1,
    gap: spacing.sm,
    padding: spacing.lg,
    ...shadows.card,
  },
  planDestination: {
    ...typography.caption,
    color: colors.moss,
    textTransform: "uppercase",
  },
  planTitle: {
    ...typography.subheading,
  },
  planPrompt: {
    ...typography.body,
    color: colors.muted,
  },
});
