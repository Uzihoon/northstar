import { Redirect, router } from "expo-router";
import { Search } from "lucide-react-native";
import { useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";

import { listDestinations } from "../src/api/client";
import type { Destination } from "../src/api/types";
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

export default function DashboardScreen() {
  const { isAuthenticated } = useAuth();
  const [destinations, setDestinations] = useState<Destination[]>([]);
  const [searchText, setSearchText] = useState("");
  const [query, setQuery] = useState("");
  const [activeCategory, setActiveCategory] = useState("all");
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

    if (isAuthenticated) {
      load();
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
          <View style={styles.header}>
            <View>
              <Text style={styles.title}>Where should Nori take you?</Text>
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
            <View>
              <Text style={styles.sectionTitle}>Destinations</Text>
              <Text style={styles.sectionSubtitle}>
                Large cards now, real photography later.
              </Text>
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
                destination={destination}
                key={destination.id}
                onPress={() => router.push({
                  pathname: "/destinations/[id]",
                  params: { id: destination.id },
                })}
              />
            ))}
          </View>
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
    paddingHorizontal: spacing.xl,
    paddingBottom: APP_TAB_BAR_OVERLAY_HEIGHT,
    paddingTop: spacing.xl,
  },
  scroll: {
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
  categoryChip: {
    backgroundColor: colors.surface,
    borderColor: colors.clay,
    borderRadius: radius.pill,
    borderWidth: 1,
    minHeight: 36,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
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
});
