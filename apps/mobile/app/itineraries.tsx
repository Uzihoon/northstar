import { Redirect, router } from "expo-router";
import { CalendarDays, ChevronRight, MapPin } from "lucide-react-native";
import { useEffect, useState } from "react";
import {
  ActivityIndicator,
  ImageBackground,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";

import { listSavedPlans } from "../src/api/client";
import type { SavedPlanSummary } from "../src/api/types";
import { getDestinationImageSource } from "../src/assets/destinationImages";
import { useAuth } from "../src/auth/AuthContext";
import { AppTabBar, APP_TAB_BAR_OVERLAY_HEIGHT } from "../src/components/AppTabBar";
import { PrimaryButton } from "../src/components/PrimaryButton";
import { Screen } from "../src/components/Screen";
import { colors, radius, shadows, spacing, typography } from "../src/theme/tokens";

type PlanMonthGroup = {
  month: string;
  plans: SavedPlanSummary[];
};

export default function ItinerariesScreen() {
  const { isAuthenticated } = useAuth();
  const [plans, setPlans] = useState<SavedPlanSummary[]>([]);
  const [activeFilter, setActiveFilter] = useState("all");
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

  const sortedPlans = sortPlansByNewest(plans);
  const filterOptions = buildFilterOptions(sortedPlans);
  const visiblePlans = filterPlans(sortedPlans, activeFilter);
  const latestPlan = visiblePlans[0];
  const groupedPlans = groupPlansByMonth(visiblePlans.slice(1));

  if (!isAuthenticated) {
    return <Redirect href="/onboarding" />;
  }

  return (
    <Screen padded={false} scroll={false}>
      <View style={styles.container}>
        <ScrollView
          contentContainerStyle={styles.content}
          style={styles.scroll}
          showsVerticalScrollIndicator={false}
        >
          <View>
            <Text style={styles.title}>My Journeys</Text>
            <Text style={styles.subtitle}>I saved the trips we shaped together, in case one calls again.</Text>
          </View>

          {isLoading ? (
            <View style={styles.stateCard}>
              <ActivityIndicator color={colors.primary} />
              <Text style={styles.stateText}>Loading saved journeys...</Text>
            </View>
          ) : null}

          {errorMessage ? (
            <View style={styles.stateCard}>
              <Text style={styles.stateTitle}>Could not load journeys</Text>
              <Text style={styles.stateText}>{errorMessage}</Text>
            </View>
          ) : null}

          {!isLoading && !errorMessage && sortedPlans.length === 0 ? (
            <View style={styles.emptyCard}>
              <Text style={styles.stateTitle}>No saved plans yet</Text>
              <Text style={styles.stateText}>
                Choose a destination and start an itinerary. Saved plans will show up here.
              </Text>
              <PrimaryButton label="Explore destinations" onPress={() => router.replace("/")} />
            </View>
          ) : null}

          {!isLoading && !errorMessage && sortedPlans.length > 0 ? (
            <>
              {latestPlan ? (
                <Pressable
                  accessibilityRole="button"
                  onPress={() => router.push({
                    pathname: "/plans/[id]",
                    params: { id: latestPlan.plan_id },
                  })}
                  style={styles.latestCard}
                >
                  <LatestJourneyArtwork plan={latestPlan} />

                  <View style={styles.latestCopy}>
                    <View style={styles.latestMetaRow}>
                      <Text style={styles.latestLabel}>Latest journey</Text>
                      <View style={styles.savedChip}>
                        <Text style={styles.savedChipText}>Saved</Text>
                      </View>
                    </View>
                    <Text numberOfLines={1} style={styles.latestDestination}>
                      {latestPlan.destination}
                    </Text>
                    <Text numberOfLines={2} style={styles.latestTitle}>
                      {latestPlan.title}
                    </Text>
                    <View style={styles.latestFooter}>
                      <View style={styles.metaPill}>
                        <CalendarDays color={colors.moss} size={15} strokeWidth={2.2} />
                        <Text style={styles.metaPillText}>{formatSavedMonth(latestPlan.created_at)}</Text>
                      </View>
                      <View style={styles.openPlanButton}>
                        <Text style={styles.openPlanText}>Open</Text>
                        <ChevronRight color={colors.surface} size={16} strokeWidth={2.4} />
                      </View>
                    </View>
                  </View>
                </Pressable>
              ) : null}

              <ScrollView
                contentContainerStyle={styles.filterList}
                horizontal
                showsHorizontalScrollIndicator={false}
                style={styles.filterScroll}
              >
                {filterOptions.map((filter) => (
                  <Pressable
                    accessibilityRole="button"
                    accessibilityState={{ selected: activeFilter === filter.value }}
                    key={filter.value}
                    onPress={() => setActiveFilter(filter.value)}
                    style={[
                      styles.filterChip,
                      activeFilter === filter.value && styles.activeFilterChip,
                    ]}
                  >
                    <Text
                      style={[
                        styles.filterText,
                        activeFilter === filter.value && styles.activeFilterText,
                      ]}
                    >
                      {filter.label}
                    </Text>
                  </Pressable>
                ))}
              </ScrollView>

              {groupedPlans.length > 0 ? (
                <View style={styles.timeline}>
                  {groupedPlans.map((group) => (
                    <View key={group.month} style={styles.monthGroup}>
                      <Text style={styles.monthLabel}>{group.month}</Text>
                      {group.plans.map((plan) => (
                        <JourneyCard key={plan.plan_id} plan={plan} />
                      ))}
                    </View>
                  ))}
                </View>
              ) : (
                <View style={styles.stateCard}>
                  <Text style={styles.stateTitle}>No older journeys here yet</Text>
                  <Text style={styles.stateText}>
                    The latest saved plan is ready above. More plans will build out this archive.
                  </Text>
                </View>
              )}
            </>
          ) : null}
        </ScrollView>

        <AppTabBar active="trips" />
      </View>
    </Screen>
  );
}

function LatestJourneyArtwork({ plan }: { plan: SavedPlanSummary }) {
  const imageSource = getDestinationImageSource(plan.destination);

  return (
    <View style={styles.latestArtwork}>
      {imageSource ? (
        <ImageBackground
          imageStyle={styles.latestImage}
          source={imageSource}
          style={styles.latestImageBackground}
        >
          <View style={styles.latestImageOverlay} />
        </ImageBackground>
      ) : (
        <>
          <View style={styles.latestBlobOrange} />
          <View style={styles.latestBlobSage} />
        </>
      )}
      <View style={styles.latestOrb}>
        <Text style={styles.latestOrbText}>{getDestinationInitials(plan)}</Text>
      </View>
    </View>
  );
}

function JourneyCard({ plan }: { plan: SavedPlanSummary }) {
  return (
    <Pressable
      accessibilityRole="button"
      onPress={() => router.push({
        pathname: "/plans/[id]",
        params: { id: plan.plan_id },
      })}
      style={styles.planCard}
    >
      <JourneyArtwork plan={plan} />
      <View style={styles.planCopy}>
        <View style={styles.planMetaRow}>
          <MapPin color={colors.sage} size={14} strokeWidth={2.2} />
          <Text numberOfLines={1} style={styles.planDestination}>{plan.destination}</Text>
        </View>
        <Text numberOfLines={2} style={styles.planTitle}>{plan.title}</Text>
        <Text numberOfLines={1} style={styles.planPrompt}>
          {formatPlanDetail(plan)}
        </Text>
      </View>
      <ChevronRight color={colors.muted} size={20} strokeWidth={2.2} />
    </Pressable>
  );
}

function JourneyArtwork({ plan }: { plan: SavedPlanSummary }) {
  const imageSource = getDestinationImageSource(plan.destination);

  return (
    <View style={styles.planArtwork}>
      {imageSource ? (
        <ImageBackground
          imageStyle={styles.planImage}
          source={imageSource}
          style={styles.planImageBackground}
        >
          <View style={styles.planImageOverlay} />
        </ImageBackground>
      ) : null}
      <Text style={styles.planArtworkText}>{getDestinationInitials(plan)}</Text>
    </View>
  );
}

function sortPlansByNewest(plans: SavedPlanSummary[]) {
  return [...plans].sort((left, right) => (
    getTimestamp(right.created_at) - getTimestamp(left.created_at)
  ));
}

function buildFilterOptions(plans: SavedPlanSummary[]) {
  const destinationFilters: { label: string; value: string }[] = [];
  const seen = new Set<string>();

  for (const plan of plans) {
    const city = getDestinationCity(plan.destination);
    const value = city.toLowerCase();

    if (!seen.has(value)) {
      seen.add(value);
      destinationFilters.push({ label: city, value });
    }
  }

  return [
    { label: "All", value: "all" },
    ...destinationFilters.slice(0, 4),
  ];
}

function filterPlans(plans: SavedPlanSummary[], activeFilter: string) {
  if (activeFilter === "all") {
    return plans;
  }

  return plans.filter((plan) => getDestinationCity(plan.destination).toLowerCase() === activeFilter);
}

function groupPlansByMonth(plans: SavedPlanSummary[]): PlanMonthGroup[] {
  const groups: PlanMonthGroup[] = [];

  for (const plan of plans) {
    const month = formatSavedMonth(plan.created_at);
    const existingGroup = groups.find((group) => group.month === month);

    if (existingGroup) {
      existingGroup.plans.push(plan);
    } else {
      groups.push({ month, plans: [plan] });
    }
  }

  return groups;
}

function getTimestamp(value: string) {
  const date = new Date(value);

  return Number.isNaN(date.getTime()) ? 0 : date.getTime();
}

function getDestinationCity(destination: string) {
  return destination.split(",")[0]?.trim() || destination;
}

function getDestinationInitials(plan: SavedPlanSummary) {
  const parts = plan.destination
    .split(",")
    .map((part) => part.trim())
    .filter(Boolean);

  if (parts.length >= 2) {
    return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
  }

  return plan.destination.slice(0, 2).toUpperCase();
}

function formatSavedMonth(value: string) {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "Recent";
  }

  return new Intl.DateTimeFormat("en-US", {
    month: "long",
    year: "numeric",
  }).format(date);
}

function formatPlanDetail(plan: SavedPlanSummary) {
  const duration = extractDuration(plan);
  const month = formatSavedMonth(plan.created_at);

  return duration ? `${duration} - ${month}` : month;
}

function extractDuration(plan: SavedPlanSummary) {
  const text = `${plan.title} ${plan.original_prompt}`;
  const match = text.match(/\b(\d+)\s*[- ]?\s*days?\b/i);

  if (!match) {
    return null;
  }

  return `${match[1]} ${match[1] === "1" ? "day" : "days"}`;
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    gap: spacing.md,
  },
  content: {
    gap: spacing.lg,
    paddingHorizontal: spacing.xl,
    paddingBottom: APP_TAB_BAR_OVERLAY_HEIGHT + spacing.xl,
    paddingTop: spacing.xl,
  },
  scroll: {
    flex: 1,
  },
  title: {
    ...typography.heading,
  },
  subtitle: {
    color: colors.muted,
    fontSize: 15,
    fontWeight: "400",
    lineHeight: 21,
    marginTop: spacing.xs,
  },
  stateCard: {
    alignItems: "center",
    backgroundColor: colors.surface,
    borderColor: colors.clay,
    borderRadius: radius.lg,
    borderWidth: StyleSheet.hairlineWidth,
    gap: spacing.sm,
    padding: spacing.xl,
  },
  emptyCard: {
    backgroundColor: colors.surface,
    borderColor: colors.clay,
    borderRadius: radius.lg,
    borderWidth: StyleSheet.hairlineWidth,
    gap: spacing.md,
    padding: spacing.xl,
    ...shadows.card,
  },
  stateTitle: {
    ...typography.subheading,
    textAlign: "center",
  },
  stateText: {
    ...typography.body,
    color: colors.muted,
    textAlign: "center",
  },
  latestCard: {
    backgroundColor: colors.surface,
    borderColor: "rgba(216, 195, 165, 0.76)",
    borderRadius: radius.lg,
    borderWidth: StyleSheet.hairlineWidth,
    overflow: "hidden",
    ...shadows.card,
  },
  latestArtwork: {
    backgroundColor: "#E9D8BF",
    height: 148,
    overflow: "hidden",
    position: "relative",
  },
  latestImageBackground: {
    ...StyleSheet.absoluteFillObject,
  },
  latestImage: {
    borderTopLeftRadius: radius.lg,
    borderTopRightRadius: radius.lg,
  },
  latestImageOverlay: {
    backgroundColor: "rgba(39, 34, 29, 0.22)",
    flex: 1,
  },
  latestBlobOrange: {
    backgroundColor: "#F09A57",
    borderRadius: 100,
    height: 156,
    left: -34,
    opacity: 0.7,
    position: "absolute",
    top: -48,
    width: 156,
  },
  latestBlobSage: {
    backgroundColor: "#789B6F",
    borderRadius: 120,
    bottom: -78,
    height: 190,
    opacity: 0.78,
    position: "absolute",
    right: -46,
    width: 190,
  },
  latestOrb: {
    alignItems: "center",
    backgroundColor: "rgba(255, 249, 240, 0.76)",
    borderColor: "rgba(255, 255, 255, 0.82)",
    borderRadius: radius.pill,
    borderWidth: 1,
    height: 76,
    justifyContent: "center",
    left: spacing.xl,
    position: "absolute",
    top: spacing.xl,
    width: 76,
  },
  latestOrbText: {
    color: colors.moss,
    fontSize: 26,
    fontWeight: "900",
    letterSpacing: 1,
  },
  latestCopy: {
    gap: spacing.sm,
    padding: spacing.lg,
  },
  latestMetaRow: {
    alignItems: "center",
    flexDirection: "row",
    justifyContent: "space-between",
  },
  latestLabel: {
    ...typography.caption,
    color: colors.primaryPressed,
    textTransform: "uppercase",
  },
  savedChip: {
    backgroundColor: "rgba(111, 143, 114, 0.16)",
    borderRadius: radius.pill,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.xs,
  },
  savedChipText: {
    ...typography.caption,
    color: colors.moss,
    fontWeight: "800",
  },
  latestDestination: {
    ...typography.heading,
  },
  latestTitle: {
    ...typography.body,
    color: colors.muted,
  },
  latestFooter: {
    alignItems: "center",
    flexDirection: "row",
    justifyContent: "space-between",
    marginTop: spacing.xs,
  },
  metaPill: {
    alignItems: "center",
    backgroundColor: colors.background,
    borderRadius: radius.pill,
    flexDirection: "row",
    gap: spacing.xs,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
  },
  metaPillText: {
    ...typography.caption,
    color: colors.moss,
  },
  openPlanButton: {
    alignItems: "center",
    backgroundColor: colors.primary,
    borderRadius: radius.pill,
    flexDirection: "row",
    gap: spacing.xs,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
  },
  openPlanText: {
    ...typography.caption,
    color: colors.surface,
    fontWeight: "900",
  },
  filterScroll: {
    flexGrow: 0,
    marginRight: -spacing.xl,
  },
  filterList: {
    gap: spacing.sm,
    paddingRight: spacing.xl,
  },
  filterChip: {
    backgroundColor: colors.surface,
    borderColor: colors.clay,
    borderRadius: radius.pill,
    borderWidth: StyleSheet.hairlineWidth,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
  },
  activeFilterChip: {
    backgroundColor: colors.sage,
    borderColor: colors.sage,
  },
  filterText: {
    ...typography.caption,
    color: colors.muted,
  },
  activeFilterText: {
    color: colors.surface,
  },
  timeline: {
    gap: spacing.lg,
  },
  monthGroup: {
    gap: spacing.md,
  },
  monthLabel: {
    ...typography.caption,
    color: colors.primaryPressed,
    textTransform: "uppercase",
  },
  planCard: {
    alignItems: "center",
    backgroundColor: colors.surface,
    borderColor: colors.clay,
    borderRadius: radius.lg,
    borderWidth: StyleSheet.hairlineWidth,
    flexDirection: "row",
    gap: spacing.md,
    padding: spacing.md,
  },
  planArtwork: {
    alignItems: "center",
    backgroundColor: colors.moss,
    borderRadius: radius.md,
    height: 68,
    justifyContent: "center",
    overflow: "hidden",
    width: 68,
  },
  planImageBackground: {
    ...StyleSheet.absoluteFillObject,
  },
  planImage: {
    borderRadius: radius.md,
  },
  planImageOverlay: {
    backgroundColor: "rgba(39, 34, 29, 0.28)",
    flex: 1,
  },
  planArtworkText: {
    color: colors.background,
    fontSize: 20,
    fontWeight: "900",
    letterSpacing: 1,
    zIndex: 1,
  },
  planCopy: {
    flex: 1,
    gap: spacing.xs,
  },
  planMetaRow: {
    alignItems: "center",
    flexDirection: "row",
    gap: spacing.xs,
  },
  planDestination: {
    ...typography.caption,
    color: colors.sage,
    flexShrink: 1,
    fontWeight: "800",
  },
  planTitle: {
    ...typography.subheading,
  },
  planPrompt: {
    ...typography.caption,
    color: colors.muted,
    fontWeight: "400",
  },
});
