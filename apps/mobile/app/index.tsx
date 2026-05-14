import { Redirect, router } from "expo-router";
import { Search } from "lucide-react-native";
import { useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  ImageBackground,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";

import { listDestinations, listSavedPlans } from "../src/api/client";
import type { Destination, SavedPlanSummary } from "../src/api/types";
import { getDestinationCityName, getDestinationImageSource } from "../src/assets/destinationImages";
import { useAuth } from "../src/auth/AuthContext";
import { AppTabBar, APP_TAB_BAR_OVERLAY_HEIGHT } from "../src/components/AppTabBar";
import { DestinationCard } from "../src/components/DestinationCard";
import { Screen } from "../src/components/Screen";
import { colors, radius, spacing, typography } from "../src/theme/tokens";

const CATEGORY_FILTERS = [
  { label: "All", value: "all" },
  { label: "Quiet", value: "quiet" },
  { label: "Cafes", value: "cafes" },
  { label: "Food", value: "vegetarian" },
  { label: "Culture", value: "culture" },
  { label: "Walkable", value: "walkable" },
];
const SEARCH_BORDER_COLOR = "rgba(216, 195, 165, 0.72)";
const PAST_JOURNEY_LIMIT = 3;

export default function DashboardScreen() {
  const { isAuthenticated } = useAuth();
  const [destinations, setDestinations] = useState<Destination[]>([]);
  const [pastPlans, setPastPlans] = useState<SavedPlanSummary[]>([]);
  const [searchText, setSearchText] = useState("");
  const [query, setQuery] = useState("");
  const [activeCategory, setActiveCategory] = useState("all");
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;

    async function loadDestinations() {
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

    async function loadPastPlans() {
      try {
        const data = await listSavedPlans();
        if (isMounted) {
          setPastPlans(
            [...data]
              .sort((left, right) => (
                new Date(right.created_at).getTime() - new Date(left.created_at).getTime()
              ))
              .slice(0, PAST_JOURNEY_LIMIT),
          );
        }
      } catch {
        if (isMounted) {
          setPastPlans([]);
        }
      }
    }

    if (isAuthenticated) {
      loadDestinations();
      loadPastPlans();
    }

    return () => {
      isMounted = false;
    };
  }, [isAuthenticated]);

  const filteredDestinations = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();

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

      const matchesQuery = normalizedQuery
        ? normalizedQuery.split(/\s+/).every((term) => haystack.includes(term))
        : true;
      const matchesCategory = activeCategory === "all" || haystack.includes(activeCategory);

      return matchesQuery && matchesCategory;
    });
  }, [activeCategory, destinations, query]);

  function submitSearch() {
    setQuery(searchText.trim());
  }

  function formatJourneyDate(createdAt: string) {
    const date = new Date(createdAt);

    if (Number.isNaN(date.getTime())) {
      return "Recent trip";
    }

    return new Intl.DateTimeFormat("en-US", {
      month: "short",
      year: "numeric",
    }).format(date);
  }

  if (!isAuthenticated) {
    return <Redirect href="/onboarding" />;
  }

  return (
    <Screen padded={false} scroll={false}>
      <View style={styles.container}>
        <ScrollView
          contentContainerStyle={styles.content}
          style={styles.pageScroll}
          showsVerticalScrollIndicator={false}
        >
          <View style={styles.header}>
            <View>
              <Text style={styles.title}>Where should Nori take you?</Text>
              <Text style={styles.subtitle}>Tell me the vibe, and I’ll find somewhere that fits.</Text>
            </View>
            <Pressable
              accessibilityRole="button"
              onPress={() => router.push("/profile")}
              style={styles.avatar}
            >
              <Text style={styles.avatarText}>J</Text>
            </Pressable>
          </View>

          <View style={styles.searchCard}>
            <Search
              color={colors.muted}
              pointerEvents="none"
              size={20}
              strokeWidth={2.2}
              style={styles.searchIcon}
            />
            <TextInput
              autoCapitalize="none"
              onChangeText={setSearchText}
              onSubmitEditing={submitSearch}
              placeholder="Search destinations or vibes"
              placeholderTextColor={colors.muted}
              returnKeyType="search"
              style={styles.searchInput}
              value={searchText}
            />
          </View>

          <ScrollView
            contentContainerStyle={styles.categoryList}
            horizontal
            style={styles.categoryScroll}
            showsHorizontalScrollIndicator={false}
          >
            {CATEGORY_FILTERS.map((category) => (
              <Pressable
                accessibilityRole="button"
                key={category.value}
                onPress={() => setActiveCategory(category.value)}
                style={[
                  styles.categoryChip,
                  activeCategory === category.value && styles.activeCategoryChip,
                ]}
              >
                <Text
                  style={[
                    styles.categoryText,
                    activeCategory === category.value && styles.activeCategoryText,
                  ]}
                >
                  {category.label}
                </Text>
              </Pressable>
            ))}
          </ScrollView>

          <View style={styles.sectionHeader}>
            <View style={styles.sectionHeaderCopy}>
              <Text style={styles.sectionTitle}>Curated for you</Text>
              <Text style={styles.sectionSubtitle}>
                I know these places well enough to start sketching the good stuff.
              </Text>
            </View>
          </View>

          <ScrollView
            contentContainerStyle={styles.destinationScrollContent}
            horizontal
            style={styles.destinationScroll}
            showsHorizontalScrollIndicator={false}
          >
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
                <View key={destination.id} style={styles.destinationCardFrame}>
                  <DestinationCard
                    destination={destination}
                    onPress={() => router.push({
                      pathname: "/destinations/[id]",
                      params: { id: destination.id },
                    })}
                  />
                </View>
              ))}
            </View>
          </ScrollView>

          <View style={[styles.sectionHeader, styles.pastJourneysHeader]}>
            <View style={styles.sectionHeaderCopy}>
              <Text style={styles.sectionTitle}>My Past Journeys</Text>
              <Text style={styles.sectionSubtitle}>
                Trips we already mapped, ready for a second look.
              </Text>
            </View>
            <Pressable
              accessibilityRole="button"
              onPress={() => router.replace("/itineraries")}
              style={styles.viewAllButton}
            >
              <Text style={styles.viewAllText}>View all</Text>
            </Pressable>
          </View>

          <ScrollView
            contentContainerStyle={styles.pastJourneyScrollContent}
            horizontal
            style={styles.pastJourneyScroll}
            showsHorizontalScrollIndicator={false}
          >
            {pastPlans.length > 0 ? (
              pastPlans.map((plan) => {
                const imageSource = getDestinationImageSource(plan.destination);

                return (
                  <Pressable
                    accessibilityRole="button"
                    key={plan.plan_id}
                    onPress={() => router.push({
                      pathname: "/plans/[id]",
                      params: { id: plan.plan_id },
                    })}
                    style={styles.pastJourneyCard}
                  >
                    {imageSource ? (
                      <ImageBackground
                        imageStyle={styles.pastJourneyHeroImage}
                        source={imageSource}
                        style={styles.pastJourneyImage}
                      >
                        <View style={styles.pastJourneyImageOverlay}>
                          <Text style={styles.pastJourneyImageText}>
                            {getDestinationCityName(plan.destination)}
                          </Text>
                        </View>
                      </ImageBackground>
                    ) : (
                      <View style={styles.pastJourneyImage}>
                        <Text style={styles.pastJourneyImageText}>
                          {getDestinationCityName(plan.destination)}
                        </Text>
                      </View>
                    )}
                    <View style={styles.pastJourneyCopy}>
                      <Text numberOfLines={1} style={styles.pastJourneyTitle}>
                        {plan.destination}
                      </Text>
                      <Text style={styles.pastJourneyDate}>
                        {formatJourneyDate(plan.created_at)}
                      </Text>
                    </View>
                  </Pressable>
                );
              })
            ) : (
              <View style={styles.emptyPastJourneyCard}>
                <Text style={styles.pastJourneyTitle}>No journeys yet</Text>
                <Text style={styles.pastJourneyDate}>Your saved trips will appear here.</Text>
              </View>
            )}
          </ScrollView>
        </ScrollView>

        <AppTabBar active="explore" />
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
    paddingBottom: APP_TAB_BAR_OVERLAY_HEIGHT + spacing.xl,
    paddingHorizontal: spacing.xl,
    paddingTop: spacing.xl,
  },
  pageScroll: {
    flex: 1,
  },
  header: {
    alignItems: "flex-start",
    flexDirection: "row",
    justifyContent: "space-between",
  },
  title: {
    ...typography.heading,
    maxWidth: 250,
  },
  subtitle: {
    color: colors.muted,
    fontSize: 15,
    fontWeight: "400",
    lineHeight: 21,
    marginTop: spacing.xs,
  },
  avatar: {
    alignItems: "center",
    backgroundColor: colors.moss,
    borderRadius: radius.pill,
    height: 46,
    justifyContent: "center",
    width: 46,
  },
  avatarText: {
    color: colors.surface,
    fontSize: 18,
    fontWeight: "900",
  },
  searchCard: {
    alignItems: "center",
    backgroundColor: "#FFF7EA",
    borderColor: SEARCH_BORDER_COLOR,
    borderRadius: radius.md,
    borderWidth: StyleSheet.hairlineWidth,
    flexDirection: "row",
    gap: spacing.sm,
    height: 52,
    justifyContent: "center",
    paddingHorizontal: spacing.md,
    width: "100%",
  },
  searchIcon: {
    marginTop: 1,
  },
  searchInput: {
    color: colors.ink,
    flex: 1,
    fontSize: 16,
    fontWeight: "400",
    height: "100%",
    includeFontPadding: false,
    lineHeight: 20,
    paddingBottom: 0,
    paddingTop: 0,
    textAlignVertical: "center",
  },
  categoryList: {
    gap: spacing.sm,
    paddingRight: spacing.xl,
  },
  categoryScroll: {
    flexGrow: 0,
    maxHeight: 38,
  },
  categoryChip: {
    backgroundColor: colors.surface,
    borderColor: colors.clay,
    borderRadius: radius.pill,
    borderWidth: 1,
    height: 36,
    justifyContent: "center",
    paddingHorizontal: spacing.md,
    paddingVertical: 0,
  },
  activeCategoryChip: {
    backgroundColor: colors.sage,
    borderColor: colors.sage,
  },
  categoryText: {
    ...typography.caption,
    color: colors.muted,
  },
  activeCategoryText: {
    color: colors.surface,
  },
  sectionHeader: {
    alignItems: "flex-start",
    flexDirection: "row",
    justifyContent: "space-between",
  },
  sectionHeaderCopy: {
    flex: 1,
    paddingRight: spacing.md,
  },
  sectionTitle: {
    ...typography.heading,
  },
  sectionSubtitle: {
    ...typography.caption,
    color: colors.muted,
    marginTop: spacing.xs,
  },
  pastJourneysHeader: {
    marginTop: spacing.md,
  },
  viewAllButton: {
    paddingLeft: spacing.md,
    paddingVertical: spacing.xs,
  },
  viewAllText: {
    ...typography.caption,
    color: colors.primaryPressed,
    fontWeight: "800",
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
  destinationScroll: {
    flexGrow: 0,
    marginRight: -spacing.xl,
  },
  destinationScrollContent: {
    gap: spacing.lg,
    paddingRight: spacing.xl,
  },
  destinationList: {
    flexDirection: "row",
    gap: spacing.lg,
  },
  destinationCardFrame: {
    height: 418,
    width: 302,
  },
  pastJourneyScroll: {
    flexGrow: 0,
    marginRight: -spacing.xl,
  },
  pastJourneyScrollContent: {
    gap: spacing.md,
    paddingRight: spacing.xl,
  },
  pastJourneyCard: {
    backgroundColor: colors.surface,
    borderColor: colors.clay,
    borderRadius: radius.lg,
    borderWidth: StyleSheet.hairlineWidth,
    gap: spacing.sm,
    height: 170,
    overflow: "hidden",
    width: 180,
  },
  pastJourneyImage: {
    alignItems: "center",
    backgroundColor: colors.moss,
    height: 98,
    justifyContent: "center",
    overflow: "hidden",
    width: "100%",
  },
  pastJourneyHeroImage: {
    borderTopLeftRadius: radius.lg,
    borderTopRightRadius: radius.lg,
  },
  pastJourneyImageOverlay: {
    alignItems: "center",
    backgroundColor: "rgba(39, 34, 29, 0.22)",
    flex: 1,
    justifyContent: "center",
    width: "100%",
  },
  pastJourneyImageText: {
    color: colors.background,
    fontSize: 26,
    fontWeight: "900",
    letterSpacing: 1,
  },
  pastJourneyCopy: {
    gap: spacing.xs,
    paddingHorizontal: spacing.md,
    paddingBottom: spacing.md,
  },
  pastJourneyTitle: {
    ...typography.caption,
    color: colors.ink,
    fontWeight: "800",
  },
  pastJourneyDate: {
    ...typography.caption,
    color: colors.muted,
    fontWeight: "400",
  },
  emptyPastJourneyCard: {
    backgroundColor: colors.surface,
    borderColor: colors.clay,
    borderRadius: radius.lg,
    borderWidth: StyleSheet.hairlineWidth,
    gap: spacing.xs,
    justifyContent: "center",
    minHeight: 196,
    padding: spacing.lg,
    width: 156,
  },
});
