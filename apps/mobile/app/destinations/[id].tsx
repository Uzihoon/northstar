import { router, useLocalSearchParams } from "expo-router";
import { useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";

import { getDestination, getPlanRun, startPlanRun } from "../../src/api/client";
import type { Destination, ItineraryPlanRunResponse } from "../../src/api/types";
import { Pill } from "../../src/components/Pill";
import { PrimaryButton } from "../../src/components/PrimaryButton";
import { Screen } from "../../src/components/Screen";
import { colors, radius, shadows, spacing, typography } from "../../src/theme/tokens";

const BUDGET_OPTIONS = [
  { label: "Budget", value: "budget" },
  { label: "Mid-range", value: "midrange" },
  { label: "Luxury", value: "luxury" },
];

const PACE_OPTIONS = [
  { label: "Relaxed", value: "relaxed" },
  { label: "Balanced", value: "balanced" },
  { label: "Fast", value: "fast" },
];

const INTEREST_OPTIONS = [
  "quiet neighborhoods",
  "cafes",
  "bookstores",
  "temples",
  "markets",
  "walkable",
];

const FOOD_OPTIONS = [
  "vegetarian",
  "coffee",
  "vegan",
  "local cuisine",
];

function firstParam(value: string | string[] | undefined): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}

function toggleValue(values: string[], value: string): string[] {
  return values.includes(value)
    ? values.filter((item) => item !== value)
    : [...values, value];
}

export default function DestinationDetailScreen() {
  const params = useLocalSearchParams();
  const destinationId = firstParam(params.id);

  const [destination, setDestination] = useState<Destination | null>(null);
  const [durationDays, setDurationDays] = useState("2");
  const [budgetLevel, setBudgetLevel] = useState("midrange");
  const [pace, setPace] = useState("relaxed");
  const [interests, setInterests] = useState<string[]>(["cafes", "quiet neighborhoods"]);
  const [foodPreferences, setFoodPreferences] = useState<string[]>(["vegetarian", "coffee"]);
  const [note, setNote] = useState("");
  const [run, setRun] = useState<ItineraryPlanRunResponse | null>(null);
  const [runId, setRunId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isStarting, setIsStarting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;

    async function loadDestination() {
      if (!destinationId) {
        setErrorMessage("Destination id is missing.");
        setIsLoading(false);
        return;
      }

      try {
        const data = await getDestination(destinationId);
        if (isMounted) {
          setDestination(data);
          setDurationDays(String(data.suggested_duration_days[0] ?? 2));
          setInterests(data.vibes.slice(0, 2));
          setErrorMessage(null);
        }
      } catch (error) {
        if (isMounted) {
          setErrorMessage(error instanceof Error ? error.message : "Could not load destination.");
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    loadDestination();

    return () => {
      isMounted = false;
    };
  }, [destinationId]);

  useEffect(() => {
    if (!runId) {
      return undefined;
    }

    let isMounted = true;

    const interval = setInterval(async () => {
      try {
        const nextRun = await getPlanRun(runId);

        if (!isMounted) {
          return;
        }

        setRun(nextRun);

        if (nextRun.status === "completed" && nextRun.plan_id) {
          setRunId(null);
          router.replace({
            pathname: "/plans/[id]",
            params: { id: nextRun.plan_id },
          });
        }

        if (nextRun.status === "failed") {
          setRunId(null);
          setErrorMessage(nextRun.error_message ?? "Planning failed.");
        }
      } catch (error) {
        if (isMounted) {
          setRunId(null);
          setErrorMessage(error instanceof Error ? error.message : "Could not poll planning run.");
        }
      }
    }, 2000);

    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [runId]);

  const additionalInfo = useMemo(() => {
    const parts = [`Duration: ${durationDays || "2"} days.`];

    if (note.trim()) {
      parts.push(note.trim());
    }

    return parts.join("\n");
  }, [durationDays, note]);

  async function startPlanning() {
    if (!destinationId || isStarting || runId) {
      return;
    }

    setIsStarting(true);
    setErrorMessage(null);

    try {
      const createdRun = await startPlanRun({
        destinationId,
        additionalInfo,
        budgetLevel,
        pace,
        interests,
        foodPreferences,
      });

      setRun({
        run_id: createdRun.run_id,
        original_prompt: "",
        model_name: "",
        save: true,
        status: "queued",
        progress_events: createdRun.progress_events,
        error_message: null,
        plan_id: null,
        trip_request_id: null,
        created_at: createdRun.created_at,
        updated_at: createdRun.updated_at,
      });
      setRunId(createdRun.run_id);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Could not start planning.");
    } finally {
      setIsStarting(false);
    }
  }

  if (isLoading) {
    return (
      <Screen>
        <View style={styles.stateCard}>
          <ActivityIndicator color={colors.primary} />
          <Text style={styles.stateText}>Loading destination...</Text>
        </View>
      </Screen>
    );
  }

  if (!destination) {
    return (
      <Screen>
        <View style={styles.stateCard}>
          <Text style={styles.stateTitle}>Destination unavailable</Text>
          <Text style={styles.stateText}>{errorMessage}</Text>
        </View>
      </Screen>
    );
  }

  return (
    <Screen>
      <View style={styles.hero}>
        <Text style={styles.destinationCode}>{destination.city.slice(0, 2).toUpperCase()}</Text>
        <View style={styles.heroCopy}>
          <Text style={styles.title}>{destination.title}</Text>
          <Text style={styles.description}>{destination.description}</Text>
        </View>
      </View>

      <View style={styles.pillGrid}>
        {destination.vibes.map((vibe) => (
          <Pill key={vibe} label={vibe} tone="sage" />
        ))}
      </View>

      <View style={styles.formCard}>
        <Text style={styles.sectionTitle}>Trip basics</Text>

        <View style={styles.field}>
          <Text style={styles.label}>How many days?</Text>
          <TextInput
            keyboardType="number-pad"
            onChangeText={setDurationDays}
            style={styles.input}
            value={durationDays}
          />
        </View>

        <View style={styles.field}>
          <Text style={styles.label}>Budget</Text>
          <View style={styles.optionRow}>
            {BUDGET_OPTIONS.map((option) => (
              <SelectableChip
                isSelected={budgetLevel === option.value}
                key={option.value}
                label={option.label}
                onPress={() => setBudgetLevel(option.value)}
              />
            ))}
          </View>
        </View>

        <View style={styles.field}>
          <Text style={styles.label}>Pace</Text>
          <View style={styles.optionRow}>
            {PACE_OPTIONS.map((option) => (
              <SelectableChip
                isSelected={pace === option.value}
                key={option.value}
                label={option.label}
                onPress={() => setPace(option.value)}
              />
            ))}
          </View>
        </View>

        <View style={styles.field}>
          <Text style={styles.label}>Themes</Text>
          <View style={styles.optionRow}>
            {INTEREST_OPTIONS.map((interest) => (
              <SelectableChip
                isSelected={interests.includes(interest)}
                key={interest}
                label={interest}
                onPress={() => setInterests((current) => toggleValue(current, interest))}
              />
            ))}
          </View>
        </View>

        <View style={styles.field}>
          <Text style={styles.label}>Food notes</Text>
          <View style={styles.optionRow}>
            {FOOD_OPTIONS.map((food) => (
              <SelectableChip
                isSelected={foodPreferences.includes(food)}
                key={food}
                label={food}
                onPress={() => setFoodPreferences((current) => toggleValue(current, food))}
              />
            ))}
          </View>
        </View>

        <View style={styles.field}>
          <Text style={styles.label}>Anything else?</Text>
          <TextInput
            multiline
            onChangeText={setNote}
            placeholder="Example: keep mornings gentle, avoid crowded dinner spots..."
            placeholderTextColor={colors.muted}
            style={[styles.input, styles.noteInput]}
            value={note}
          />
        </View>

        {errorMessage ? (
          <View style={styles.errorCard}>
            <Text style={styles.errorText}>{errorMessage}</Text>
          </View>
        ) : null}

        <PrimaryButton
          disabled={isStarting || Boolean(runId)}
          label={runId ? "Planning..." : "Start itinerary"}
          onPress={startPlanning}
        />
      </View>

      {run ? (
        <View style={styles.runCard}>
          <Text style={styles.sectionTitle}>Nori is planning</Text>
          {run.progress_events.map((event, index) => (
            <View key={`${event.status}-${index}`} style={styles.runEvent}>
              <View style={styles.runDot} />
              <Text style={styles.runText}>{event.message}</Text>
            </View>
          ))}
          {runId ? <ActivityIndicator color={colors.primary} /> : null}
        </View>
      ) : null}
    </Screen>
  );
}

type SelectableChipProps = {
  isSelected: boolean;
  label: string;
  onPress: () => void;
};

function SelectableChip({ isSelected, label, onPress }: SelectableChipProps) {
  return (
    <Pressable
      accessibilityRole="button"
      onPress={onPress}
      style={[styles.selectableChip, isSelected && styles.selectedChip]}
    >
      <Text style={[styles.selectableChipText, isSelected && styles.selectedChipText]}>
        {label}
      </Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  hero: {
    backgroundColor: colors.moss,
    borderRadius: radius.lg,
    gap: spacing.lg,
    overflow: "hidden",
    padding: spacing.xl,
    ...shadows.card,
  },
  destinationCode: {
    color: "#DDEBCF",
    fontSize: 72,
    fontWeight: "900",
    letterSpacing: 3,
    opacity: 0.9,
  },
  heroCopy: {
    gap: spacing.sm,
  },
  title: {
    ...typography.title,
    color: colors.surface,
  },
  description: {
    color: "#E9F0E2",
    fontSize: 15,
    fontWeight: "400",
    lineHeight: 21,
  },
  pillGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.sm,
  },
  formCard: {
    backgroundColor: colors.surface,
    borderColor: colors.clay,
    borderRadius: radius.lg,
    borderWidth: 1,
    gap: spacing.lg,
    padding: spacing.lg,
    ...shadows.card,
  },
  sectionTitle: {
    ...typography.heading,
  },
  field: {
    gap: spacing.sm,
  },
  label: {
    ...typography.caption,
    color: colors.moss,
    textTransform: "uppercase",
  },
  input: {
    ...typography.body,
    backgroundColor: colors.background,
    borderColor: colors.clay,
    borderRadius: radius.md,
    borderWidth: 1,
    minHeight: 52,
    paddingHorizontal: spacing.lg,
  },
  noteInput: {
    minHeight: 112,
    paddingTop: spacing.md,
    textAlignVertical: "top",
  },
  optionRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.sm,
  },
  selectableChip: {
    backgroundColor: colors.background,
    borderColor: colors.clay,
    borderRadius: radius.pill,
    borderWidth: 1,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
  },
  selectedChip: {
    backgroundColor: "#F7D4BD",
    borderColor: colors.primary,
  },
  selectableChipText: {
    ...typography.caption,
    color: colors.muted,
  },
  selectedChipText: {
    color: colors.primaryPressed,
  },
  errorCard: {
    backgroundColor: "#F7D4BD",
    borderRadius: radius.md,
    padding: spacing.md,
  },
  errorText: {
    ...typography.caption,
    color: colors.error,
  },
  runCard: {
    backgroundColor: colors.surface,
    borderColor: colors.clay,
    borderRadius: radius.lg,
    borderWidth: 1,
    gap: spacing.md,
    padding: spacing.lg,
  },
  runEvent: {
    alignItems: "center",
    flexDirection: "row",
    gap: spacing.sm,
  },
  runDot: {
    backgroundColor: colors.primary,
    borderRadius: radius.pill,
    height: 10,
    width: 10,
  },
  runText: {
    ...typography.body,
    color: colors.muted,
    flex: 1,
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
