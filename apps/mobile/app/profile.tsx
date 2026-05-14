import { useEffect, useState } from "react";
import { Redirect, router } from "expo-router";
import { ActivityIndicator, ScrollView, StyleSheet, Text, View } from "react-native";

import { getPreferenceProfile } from "../src/api/client";
import type { UserPreferenceProfile } from "../src/api/types";
import { useAuth } from "../src/auth/AuthContext";
import { AppTabBar, APP_TAB_BAR_OVERLAY_HEIGHT } from "../src/components/AppTabBar";
import { Pill } from "../src/components/Pill";
import { PrimaryButton } from "../src/components/PrimaryButton";
import { Screen } from "../src/components/Screen";
import { colors, radius, shadows, spacing, typography } from "../src/theme/tokens";

const EMPTY_PROFILE: UserPreferenceProfile = {
  pace: null,
  budget_level: null,
  interests: [],
  food_preferences: [],
  dislikes: [],
  notes: [],
};

type PreferenceSectionProps = {
  title: string;
  description: string;
  emptyLabel: string;
  values: string[];
  tone?: "sage" | "orange" | "neutral";
};

type PreferenceStatProps = {
  label: string;
  value: string;
};

export default function ProfileScreen() {
  const { isAuthenticated, resetLocalAuth } = useAuth();
  const [profile, setProfile] = useState<UserPreferenceProfile | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;

    async function loadProfile() {
      if (!isAuthenticated) {
        return;
      }

      setIsLoading(true);
      setErrorMessage(null);

      try {
        const loadedProfile = await getPreferenceProfile();
        if (isMounted) {
          setProfile(loadedProfile);
        }
      } catch {
        if (isMounted) {
          setErrorMessage("Nori could not load your preference profile yet.");
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    void loadProfile();

    return () => {
      isMounted = false;
    };
  }, [isAuthenticated]);

  if (!isAuthenticated) {
    return <Redirect href="/onboarding" />;
  }

  const safeProfile = profile ?? EMPTY_PROFILE;
  const signalCount = countPreferenceSignals(safeProfile);
  const summary = buildProfileSummary(safeProfile);

  function resetAndReturn() {
    resetLocalAuth();
    router.replace("/onboarding");
  }

  return (
    <Screen padded={false} scroll={false}>
      <View style={styles.container}>
        <ScrollView
          contentContainerStyle={styles.content}
          style={styles.scroll}
          showsVerticalScrollIndicator={false}
        >
          <View style={styles.header}>
            <Text style={styles.kicker}>Profile</Text>
            <Text style={styles.title}>Your travel taste</Text>
            <Text style={styles.subtitle}>
              These are the preferences Nori uses by default when planning for you.
            </Text>
          </View>

          <View style={styles.heroCard}>
            <View style={styles.avatar}>
              <Text style={styles.avatarText}>J</Text>
            </View>
            <View style={styles.heroCopy}>
              <View style={styles.heroTopRow}>
                <Text style={styles.name}>Local traveler</Text>
                <View style={styles.memoryBadge}>
                  <Text style={styles.memoryBadgeText}>
                    {signalCount > 0 ? `${signalCount} signals` : "learning"}
                  </Text>
                </View>
              </View>
              {isLoading ? (
                <View style={styles.loadingRow}>
                  <ActivityIndicator color={colors.surface} />
                  <Text style={styles.loadingText}>Loading Nori memory...</Text>
                </View>
              ) : (
                <Text style={styles.heroSummary}>{summary}</Text>
              )}
            </View>
          </View>

          {errorMessage ? (
            <View style={styles.stateCard}>
              <Text style={styles.cardTitle}>Profile temporarily unavailable</Text>
              <Text style={styles.cardBody}>
                {errorMessage} Check that the backend and database tunnel are running.
              </Text>
            </View>
          ) : null}

          {!isLoading ? (
            <>
              <View style={styles.statGrid}>
                <PreferenceStat label="Pace" value={formatPreferenceValue(safeProfile.pace)} />
                <PreferenceStat label="Budget" value={formatPreferenceValue(safeProfile.budget_level)} />
              </View>

              <View style={styles.noteCard}>
                <Text style={styles.cardTitle}>How Nori uses this</Text>
                <Text style={styles.cardBody}>
                  Your profile sets the default vibe. Trip-specific requests still win when you ask
                  for a different pace, budget, food style, or mood.
                </Text>
              </View>

              <PreferenceSection
                title="Things you like"
                description="Activities, places, and travel moods Nori should bias toward."
                emptyLabel="No favorite travel signals yet."
                values={safeProfile.interests}
                tone="sage"
              />

              <PreferenceSection
                title="Food preferences"
                description="Diet and dining notes that should appear in future plans."
                emptyLabel="No food preferences learned yet."
                values={safeProfile.food_preferences}
                tone="orange"
              />

              <PreferenceSection
                title="Not my vibe"
                description="Things Nori should avoid when it can."
                emptyLabel="No dislikes saved yet."
                values={safeProfile.dislikes}
              />

              <PreferenceSection
                title="Memory notes"
                description="Extra context Nori has learned from your onboarding chat."
                emptyLabel="No extra notes saved yet."
                values={safeProfile.notes}
              />
            </>
          ) : null}

          <View style={styles.developerCard}>
            <Text style={styles.cardEyebrow}>Developer helper</Text>
            <Text style={styles.cardTitle}>Test onboarding again</Text>
            <Text style={styles.cardBody}>
              Reset local auth to return to the first-run chat flow. Profile editing can become the
              next product slice.
            </Text>
            <PrimaryButton label="Reset local auth" onPress={resetAndReturn} tone="secondary" />
          </View>
        </ScrollView>

        <AppTabBar active="profile" />
      </View>
    </Screen>
  );
}

function PreferenceStat({ label, value }: PreferenceStatProps) {
  return (
    <View style={styles.statCard}>
      <Text style={styles.statLabel}>{label}</Text>
      <Text style={styles.statValue}>{value}</Text>
    </View>
  );
}

function PreferenceSection({
  title,
  description,
  emptyLabel,
  values,
  tone = "neutral",
}: PreferenceSectionProps) {
  return (
    <View style={styles.preferenceCard}>
      <Text style={styles.cardTitle}>{title}</Text>
      <Text style={styles.cardBody}>{description}</Text>
      {values.length > 0 ? (
        <View style={styles.pills}>
          {values.map((value) => (
            <Pill key={value} label={value} tone={tone} />
          ))}
        </View>
      ) : (
        <Text style={styles.emptyText}>{emptyLabel}</Text>
      )}
    </View>
  );
}

function countPreferenceSignals(profile: UserPreferenceProfile): number {
  return [
    profile.pace,
    profile.budget_level,
    ...profile.interests,
    ...profile.food_preferences,
    ...profile.dislikes,
    ...profile.notes,
  ].filter(Boolean).length;
}

function buildProfileSummary(profile: UserPreferenceProfile): string {
  const pieces = [
    profile.pace ? `${formatPreferenceValue(profile.pace)} pace` : null,
    profile.budget_level ? `${formatPreferenceValue(profile.budget_level)} budget` : null,
    profile.interests[0] ?? null,
  ].filter(Boolean);

  if (pieces.length === 0) {
    return "Nori is still learning what makes a trip feel right for you.";
  }

  return pieces.join(" • ");
}

function formatPreferenceValue(value: string | null): string {
  if (!value) {
    return "Not set yet";
  }

  return value
    .replace(/_/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    gap: spacing.md,
  },
  content: {
    gap: spacing.lg,
    paddingBottom: APP_TAB_BAR_OVERLAY_HEIGHT,
    paddingHorizontal: spacing.xl,
    paddingTop: spacing.xl,
  },
  scroll: {
    flex: 1,
  },
  header: {
    gap: spacing.xs,
  },
  kicker: {
    ...typography.caption,
    color: colors.primaryPressed,
    textTransform: "uppercase",
  },
  title: {
    ...typography.title,
  },
  subtitle: {
    ...typography.body,
    color: colors.muted,
  },
  heroCard: {
    alignItems: "center",
    backgroundColor: colors.moss,
    borderRadius: radius.lg,
    flexDirection: "row",
    gap: spacing.lg,
    padding: spacing.xl,
    ...shadows.card,
  },
  avatar: {
    alignItems: "center",
    backgroundColor: colors.surface,
    borderRadius: radius.pill,
    height: 72,
    justifyContent: "center",
    width: 72,
  },
  avatarText: {
    color: colors.moss,
    fontSize: 28,
    fontWeight: "900",
  },
  heroCopy: {
    flex: 1,
    gap: spacing.sm,
  },
  heroTopRow: {
    alignItems: "center",
    flexDirection: "row",
    gap: spacing.sm,
    justifyContent: "space-between",
  },
  name: {
    ...typography.subheading,
    color: colors.surface,
    flex: 1,
  },
  memoryBadge: {
    backgroundColor: "rgba(255, 249, 240, 0.18)",
    borderColor: "rgba(255, 249, 240, 0.28)",
    borderRadius: radius.pill,
    borderWidth: 1,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.xs,
  },
  memoryBadgeText: {
    ...typography.caption,
    color: colors.surface,
  },
  heroSummary: {
    ...typography.body,
    color: "#E9F0E2",
  },
  loadingRow: {
    alignItems: "center",
    flexDirection: "row",
    gap: spacing.sm,
  },
  loadingText: {
    ...typography.caption,
    color: "#E9F0E2",
  },
  statGrid: {
    flexDirection: "row",
    gap: spacing.md,
  },
  statCard: {
    backgroundColor: colors.surface,
    borderColor: colors.clay,
    borderRadius: radius.lg,
    borderWidth: 1,
    flex: 1,
    gap: spacing.xs,
    padding: spacing.lg,
    ...shadows.card,
  },
  statLabel: {
    ...typography.caption,
    color: colors.muted,
    textTransform: "uppercase",
  },
  statValue: {
    ...typography.subheading,
    color: colors.ink,
  },
  noteCard: {
    backgroundColor: "#EEF3E9",
    borderColor: "#D8E2D0",
    borderRadius: radius.lg,
    borderWidth: 1,
    gap: spacing.sm,
    padding: spacing.lg,
  },
  stateCard: {
    backgroundColor: "#FCE6D9",
    borderColor: "#F3B895",
    borderRadius: radius.lg,
    borderWidth: 1,
    gap: spacing.sm,
    padding: spacing.lg,
  },
  preferenceCard: {
    backgroundColor: colors.surface,
    borderColor: colors.clay,
    borderRadius: radius.lg,
    borderWidth: 1,
    gap: spacing.md,
    padding: spacing.lg,
    ...shadows.card,
  },
  developerCard: {
    backgroundColor: "rgba(255, 249, 240, 0.72)",
    borderColor: colors.clay,
    borderRadius: radius.lg,
    borderWidth: 1,
    gap: spacing.md,
    padding: spacing.lg,
  },
  cardEyebrow: {
    ...typography.caption,
    color: colors.primaryPressed,
    textTransform: "uppercase",
  },
  cardTitle: {
    ...typography.subheading,
  },
  cardBody: {
    ...typography.body,
    color: colors.muted,
  },
  emptyText: {
    ...typography.caption,
    backgroundColor: colors.surfaceStrong,
    borderRadius: radius.md,
    color: colors.muted,
    overflow: "hidden",
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
  },
  pills: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.sm,
  },
});
