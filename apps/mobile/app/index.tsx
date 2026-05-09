import { router } from "expo-router";
import { useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";

import { listDestinations } from "../src/api/client";
import type { Destination } from "../src/api/types";
import { DestinationCard } from "../src/components/DestinationCard";
import { Pill } from "../src/components/Pill";
import { PrimaryButton } from "../src/components/PrimaryButton";
import { Screen } from "../src/components/Screen";
import { colors, radius, shadows, spacing, typography } from "../src/theme/tokens";

export default function ExploreScreen() {
  const [destinations, setDestinations] = useState<Destination[]>([]);
  const [query, setQuery] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;

    async function load() {
      try {
        const data = await listDestinations();
        if (isMounted) {
          setDestinations(data);
          setErrorMessage(null);
        }
      } catch (error) {
        if (isMounted) {
          setErrorMessage(error instanceof Error ? error.message : "Could not load destinations.");
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    load();

    return () => {
      isMounted = false;
    };
  }, []);

  const filteredDestinations = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();

    if (!normalizedQuery) {
      return destinations;
    }

    return destinations.filter((destination) => {
      const haystack = [
        destination.city,
        destination.country,
        destination.summary,
        destination.description,
        ...destination.vibes,
        ...destination.best_for,
        ...destination.tags,
      ].join(" ").toLowerCase();

      return normalizedQuery.split(/\s+/).every((term) => haystack.includes(term));
    });
  }, [destinations, query]);

  return (
    <Screen>
      <View style={styles.hero}>
        <View style={styles.heroGlow} />
        <Pill label="Northstar beta" tone="orange" />
        <Text style={styles.heroTitle}>Trips that know your rhythm.</Text>
        <Text style={styles.heroBody}>
          Nori learns your travel style, then turns supported destinations into personal, source-aware itineraries.
        </Text>
        <View style={styles.heroActions}>
          <PrimaryButton label="Meet Nori" onPress={() => router.push("/onboarding")} />
          <PrimaryButton
            label="Skip for now"
            onPress={() => setQuery("kyoto")}
            tone="secondary"
          />
        </View>
      </View>

      <View style={styles.searchCard}>
        <Text style={styles.sectionKicker}>Where to?</Text>
        <TextInput
          autoCapitalize="none"
          onChangeText={setQuery}
          placeholder="Search Kyoto, cafes, temples..."
          placeholderTextColor={colors.muted}
          style={styles.searchInput}
          value={query}
        />
      </View>

      <View style={styles.sectionHeader}>
        <View>
          <Text style={styles.sectionTitle}>Supported destinations</Text>
          <Text style={styles.sectionSubtitle}>Start narrow. Make it delightful. Add more cities later.</Text>
        </View>
      </View>

      {isLoading ? (
        <View style={styles.stateCard}>
          <ActivityIndicator color={colors.primary} />
          <Text style={styles.stateText}>Loading travel shelves...</Text>
        </View>
      ) : null}

      {errorMessage ? (
        <View style={styles.stateCard}>
          <Text style={styles.errorTitle}>Could not reach Northstar API</Text>
          <Text style={styles.stateText}>{errorMessage}</Text>
        </View>
      ) : null}

      {!isLoading && !errorMessage && filteredDestinations.length === 0 ? (
        <View style={styles.stateCard}>
          <Text style={styles.errorTitle}>No matching destinations yet</Text>
          <Text style={styles.stateText}>Try Kyoto, cafe, temple, walkable, or slow travel.</Text>
        </View>
      ) : null}

      <View style={styles.destinationList}>
        {filteredDestinations.map((destination) => (
          <DestinationCard
            key={destination.id}
            destination={destination}
            onPress={() => router.push({
              pathname: "/destinations/[id]",
              params: { id: destination.id },
            })}
          />
        ))}
      </View>

      <Pressable style={styles.previousCard}>
        <Text style={styles.sectionKicker}>Previous plans</Text>
        <Text style={styles.previousTitle}>Your saved itineraries will live here.</Text>
        <Text style={styles.previousBody}>
          Once the mobile flow creates plans, we can show recent trips, warnings, and "continue planning" actions here.
        </Text>
      </Pressable>
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
    overflow: "hidden",
    padding: spacing.xl,
    ...shadows.card,
  },
  heroGlow: {
    backgroundColor: "#B8D39B",
    borderRadius: 120,
    height: 180,
    opacity: 0.55,
    position: "absolute",
    right: -72,
    top: -56,
    width: 180,
  },
  heroTitle: {
    ...typography.title,
    maxWidth: 280,
  },
  heroBody: {
    ...typography.body,
    color: colors.muted,
  },
  heroActions: {
    gap: spacing.sm,
    paddingTop: spacing.sm,
  },
  searchCard: {
    backgroundColor: colors.surface,
    borderColor: colors.clay,
    borderRadius: radius.lg,
    borderWidth: 1,
    gap: spacing.sm,
    padding: spacing.lg,
  },
  sectionKicker: {
    ...typography.caption,
    color: colors.primaryPressed,
    textTransform: "uppercase",
  },
  searchInput: {
    ...typography.body,
    backgroundColor: colors.background,
    borderColor: colors.clay,
    borderRadius: radius.md,
    borderWidth: 1,
    minHeight: 52,
    paddingHorizontal: spacing.lg,
  },
  sectionHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
  },
  sectionTitle: {
    ...typography.heading,
  },
  sectionSubtitle: {
    ...typography.caption,
    color: colors.muted,
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
  errorTitle: {
    ...typography.subheading,
    textAlign: "center",
  },
  stateText: {
    ...typography.body,
    color: colors.muted,
    textAlign: "center",
  },
  destinationList: {
    gap: spacing.lg,
  },
  previousCard: {
    backgroundColor: colors.moss,
    borderRadius: radius.lg,
    gap: spacing.sm,
    padding: spacing.xl,
  },
  previousTitle: {
    ...typography.subheading,
    color: colors.surface,
  },
  previousBody: {
    ...typography.body,
    color: "#E9F0E2",
  },
});
