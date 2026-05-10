import { Redirect, router } from "expo-router";
import { ScrollView, StyleSheet, Text, View } from "react-native";

import { useAuth } from "../src/auth/AuthContext";
import { AppTabBar } from "../src/components/AppTabBar";
import { Pill } from "../src/components/Pill";
import { PrimaryButton } from "../src/components/PrimaryButton";
import { Screen } from "../src/components/Screen";
import { colors, radius, shadows, spacing, typography } from "../src/theme/tokens";

export default function SavedScreen() {
  const { isAuthenticated } = useAuth();

  if (!isAuthenticated) {
    return <Redirect href="/onboarding" />;
  }

  return (
    <Screen scroll={false}>
      <View style={styles.container}>
        <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
          <View>
            <Text style={styles.kicker}>Saved</Text>
            <Text style={styles.title}>Keep places for later.</Text>
          </View>

          <View style={styles.placeholderCard}>
            <View style={styles.cardArt}>
              <View style={styles.sunBlob} />
              <View style={styles.leafBlob} />
              <Text style={styles.cardArtText}>Soon</Text>
            </View>
            <Text style={styles.cardTitle}>Saved destinations and options will live here.</Text>
            <Text style={styles.cardBody}>
              Later this can hold destinations, restaurants, cafes, stays, or itinerary options you want to compare before planning.
            </Text>
            <View style={styles.pills}>
              <Pill label="destinations" tone="sage" />
              <Pill label="cafes" tone="orange" />
              <Pill label="stays" tone="sage" />
            </View>
            <PrimaryButton label="Explore destinations" onPress={() => router.replace("/")} />
          </View>
        </ScrollView>

        <AppTabBar active="saved" />
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
  placeholderCard: {
    backgroundColor: colors.surface,
    borderColor: colors.clay,
    borderRadius: radius.lg,
    borderWidth: 1,
    gap: spacing.md,
    overflow: "hidden",
    padding: spacing.lg,
    ...shadows.card,
  },
  cardArt: {
    backgroundColor: colors.moss,
    borderRadius: radius.lg,
    height: 180,
    justifyContent: "flex-end",
    overflow: "hidden",
    padding: spacing.lg,
  },
  sunBlob: {
    backgroundColor: colors.primary,
    borderRadius: 80,
    height: 130,
    position: "absolute",
    right: -18,
    top: -22,
    width: 130,
  },
  leafBlob: {
    backgroundColor: colors.sage,
    borderRadius: 110,
    bottom: -58,
    height: 150,
    left: -18,
    position: "absolute",
    width: 230,
  },
  cardArtText: {
    color: colors.surface,
    fontSize: 42,
    fontWeight: "900",
    letterSpacing: 1,
  },
  cardTitle: {
    ...typography.heading,
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
