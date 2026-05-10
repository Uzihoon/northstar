import { Redirect, router } from "expo-router";
import { ScrollView, StyleSheet, Text, View } from "react-native";

import { useAuth } from "../src/auth/AuthContext";
import { AppTabBar } from "../src/components/AppTabBar";
import { Pill } from "../src/components/Pill";
import { PrimaryButton } from "../src/components/PrimaryButton";
import { Screen } from "../src/components/Screen";
import { colors, radius, shadows, spacing, typography } from "../src/theme/tokens";

export default function ProfileScreen() {
  const { isAuthenticated, resetLocalAuth } = useAuth();

  if (!isAuthenticated) {
    return <Redirect href="/onboarding" />;
  }

  function resetAndReturn() {
    resetLocalAuth();
    router.replace("/onboarding");
  }

  return (
    <Screen scroll={false}>
      <View style={styles.container}>
        <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
          <View>
            <Text style={styles.kicker}>Profile</Text>
            <Text style={styles.title}>Your travel taste, still local for now.</Text>
          </View>

          <View style={styles.profileCard}>
            <View style={styles.avatar}>
              <Text style={styles.avatarText}>J</Text>
            </View>
            <View style={styles.profileCopy}>
              <Text style={styles.name}>Local traveler</Text>
              <Text style={styles.description}>
                Social login will replace this temporary local auth state later.
              </Text>
            </View>
          </View>

          <View style={styles.preferenceCard}>
            <Text style={styles.cardTitle}>Preference profile</Text>
            <Text style={styles.cardBody}>
              Nori saves durable travel preferences through onboarding. A review/edit screen can sit here next.
            </Text>
            <View style={styles.pills}>
              <Pill label="relaxed pace" tone="sage" />
              <Pill label="quiet cafes" tone="sage" />
              <Pill label="vegetarian" tone="orange" />
            </View>
          </View>

          <View style={styles.preferenceCard}>
            <Text style={styles.cardTitle}>Developer helper</Text>
            <Text style={styles.cardBody}>
              Reset local auth to test the first-run chat flow again.
            </Text>
            <PrimaryButton label="Reset local auth" onPress={resetAndReturn} tone="secondary" />
          </View>
        </ScrollView>

        <AppTabBar active="profile" />
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
  profileCard: {
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
  profileCopy: {
    flex: 1,
    gap: spacing.xs,
  },
  name: {
    ...typography.subheading,
    color: colors.surface,
  },
  description: {
    ...typography.body,
    color: "#E9F0E2",
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
  cardTitle: {
    ...typography.subheading,
  },
  cardBody: {
    ...typography.body,
    color: colors.muted,
  },
  pills: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.sm,
  },
});
