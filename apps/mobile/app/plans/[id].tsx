import { router, useLocalSearchParams } from "expo-router";
import {
  BedDouble,
  Bus,
  CalendarDays,
  Clock3,
  Coffee,
  Landmark,
  MapPin,
  Navigation,
  Utensils,
  type LucideIcon,
} from "lucide-react-native";
import { useEffect, useRef, useState } from "react";
import {
  ActivityIndicator,
  Animated,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
  useWindowDimensions,
} from "react-native";

import { getPlanSummary } from "../../src/api/client";
import type { MobilePlanCard, MobilePlanDay, MobilePlanSummary } from "../../src/api/types";
import { Pill } from "../../src/components/Pill";
import { PrimaryButton } from "../../src/components/PrimaryButton";
import { Screen } from "../../src/components/Screen";
import { colors, radius, shadows, spacing, typography } from "../../src/theme/tokens";

type TimelineTone = "orange" | "sage" | "moss";

type DayTabProps = {
  day: MobilePlanDay;
  isActive: boolean;
  onPress: () => void;
};

const DAY_TAB_INACTIVE_WIDTH = 82;
const DAY_TAB_ACTIVE_WIDTH = 116;
const DAY_TAB_GAP = spacing.xs;

function firstParam(value: string | string[] | undefined): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}

export default function PlanSummaryScreen() {
  const params = useLocalSearchParams();
  const planId = firstParam(params.id);
  const { width: windowWidth } = useWindowDimensions();

  const [plan, setPlan] = useState<MobilePlanSummary | null>(null);
  const [activeDayIndex, setActiveDayIndex] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [dayTabViewportWidth, setDayTabViewportWidth] = useState(0);
  const dayTabScrollRef = useRef<ScrollView | null>(null);
  const scrollRef = useRef<ScrollView | null>(null);

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
          setActiveDayIndex(0);
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

  useEffect(() => {
    const viewportWidth = dayTabViewportWidth || Math.max(0, windowWidth - spacing.xl * 2);
    const activeTabCenter =
      activeDayIndex * (DAY_TAB_INACTIVE_WIDTH + DAY_TAB_GAP) + DAY_TAB_ACTIVE_WIDTH / 2;
    const x = Math.max(0, activeTabCenter - viewportWidth / 2);

    requestAnimationFrame(() => {
      dayTabScrollRef.current?.scrollTo({ animated: true, x });
    });
  }, [activeDayIndex, dayTabViewportWidth, windowWidth]);

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

  const activeDay = plan.days[activeDayIndex] ?? plan.days[0];
  const planDateLabel = getPlanDateLabel(plan.days);
  const nextDayIndex = getNextDayIndex(activeDayIndex, plan.days.length);
  const nextDayLabel = activeDayIndex < plan.days.length - 1
    ? `Go to Day ${nextDayIndex + 1}`
    : "Go back to Day 1";

  function jumpToDay(index: number) {
    setActiveDayIndex(index);
    requestAnimationFrame(() => {
      scrollRef.current?.scrollTo({ animated: true, y: 0 });
    });
  }

  return (
    <Screen edges={["left", "right"]} scrollRef={scrollRef}>
      <View style={styles.hero}>
        <View style={styles.heroArtwork}>
          <View style={styles.heroBlobOrange} />
          <View style={styles.heroBlobSage} />
          <View style={styles.heroOrb}>
            <Text style={styles.heroOrbText}>{getDestinationInitials(plan.destination)}</Text>
          </View>
        </View>

        <View style={styles.heroContent}>
          <Text numberOfLines={2} style={styles.title}>{plan.title}</Text>
          <View style={styles.destinationRow}>
            <MapPin color={colors.moss} size={17} strokeWidth={2.3} />
            <Text numberOfLines={1} style={styles.destination}>{plan.destination}</Text>
          </View>

          <View style={styles.metaGrid}>
            <MetaPill icon={CalendarDays} label={planDateLabel} />
            <MetaPill icon={Clock3} label={`${plan.duration_days} days`} />
            <MetaPill icon={Navigation} label={`${getStopCount(plan.days)} stops`} />
          </View>

          {plan.highlights.length > 0 ? (
            <View style={styles.highlights}>
              {plan.highlights.slice(0, 5).map((highlight) => (
                <Pill key={highlight} label={highlight} tone="sage" />
              ))}
            </View>
          ) : null}
        </View>
      </View>

      <ScrollView
        contentContainerStyle={styles.dayTabs}
        horizontal
        onLayout={(event) => setDayTabViewportWidth(event.nativeEvent.layout.width)}
        ref={dayTabScrollRef}
        showsHorizontalScrollIndicator={false}
        style={styles.dayTabScroll}
      >
        {plan.days.map((day, index) => (
          <DayTab
            day={day}
            isActive={index === activeDayIndex}
            key={day.day_number}
            onPress={() => setActiveDayIndex(index)}
          />
        ))}
      </ScrollView>

      {activeDay ? (
        <View style={styles.dayPanel}>
          <View style={styles.dayHeader}>
            <Text style={styles.dayKicker}>Day {activeDay.day_number}</Text>
            <Text style={styles.dayTitle}>{activeDay.theme}</Text>
            <Text style={styles.dayMeta}>{getDaySummary(activeDay)}</Text>
          </View>

          <View style={styles.timeline}>
            {activeDay.cards.map((card, index) => (
              <TimelineItem
                card={card}
                isLast={index === activeDay.cards.length - 1}
                key={`${card.time}-${card.title}-${index}`}
              />
            ))}
          </View>
        </View>
      ) : null}

      <PrimaryButton label={nextDayLabel} onPress={() => jumpToDay(nextDayIndex)} tone="secondary" />
    </Screen>
  );
}

function DayTab({ day, isActive, onPress }: DayTabProps) {
  const progress = useRef(new Animated.Value(isActive ? 1 : 0)).current;

  useEffect(() => {
    Animated.timing(progress, {
      duration: 420,
      toValue: isActive ? 1 : 0,
      useNativeDriver: false,
    }).start();
  }, [isActive, progress]);

  const width = progress.interpolate({
    inputRange: [0, 1],
    outputRange: [DAY_TAB_INACTIVE_WIDTH, DAY_TAB_ACTIVE_WIDTH],
  });

  return (
    <Animated.View style={[styles.dayTabWrap, { width }]}>
      <Pressable
        accessibilityRole="button"
        accessibilityState={{ selected: isActive }}
        onPress={onPress}
        style={[styles.dayTab, isActive && styles.activeDayTab]}
      >
        {isActive ? (
          <View pointerEvents="none" style={styles.dayTabLiquid}>
            <View style={styles.dayTabOrange} />
            <View style={styles.dayTabSage} />
            <View style={styles.dayTabSheen} />
          </View>
        ) : null}
        <Text style={[styles.dayTabLabel, isActive && styles.activeDayTabText]}>
          Day {day.day_number}
        </Text>
      </Pressable>
    </Animated.View>
  );
}

function TimelineItem({ card, isLast }: { card: MobilePlanCard; isLast: boolean }) {
  const Icon = getTimelineIcon(card);
  const tone = getTimelineTone(card);
  const accentStyle = getAccentStyle(tone);

  return (
    <View style={styles.timelineRow}>
      <View style={styles.timelineRail}>
        <View style={[styles.iconBubble, accentStyle.bubble]}>
          <Icon color={accentStyle.iconColor} size={18} strokeWidth={2.4} />
        </View>
        {!isLast ? <View style={styles.timelineLine} /> : null}
      </View>

      <View style={styles.timelineCard}>
        <View style={styles.timelineCardHeader}>
          <View style={styles.cardHeaderBadges}>
            <View style={styles.timePill}>
              <Clock3 color={colors.primaryPressed} size={14} strokeWidth={2.3} />
              <Text style={styles.timePillText}>{card.time}</Text>
            </View>
          </View>
        </View>

        {card.area ? (
          <View style={styles.locationRow}>
            <MapPin color={colors.sage} size={15} strokeWidth={2.2} />
            <Text numberOfLines={2} style={styles.locationText}>{card.area}</Text>
          </View>
        ) : null}

        <Text style={styles.cardTitle}>{card.title}</Text>
        <Text numberOfLines={3} style={styles.cardDescription}>{card.description}</Text>

        {card.tags.length > 1 ? (
          <View style={styles.cardTags}>
            {card.tags.slice(1, 4).map((tag) => (
              <Text key={tag} style={styles.cardTag}>{tag}</Text>
            ))}
          </View>
        ) : null}

        {card.options.length > 0 ? (
          <View style={styles.options}>
            {card.options.slice(0, 3).map((option) => (
              <View key={`${option.category}-${option.name}`} style={styles.optionCard}>
                <View style={styles.optionTopRow}>
                  <Text style={styles.optionName}>{option.name}</Text>
                </View>
                <Text style={styles.optionMeta}>
                  {[option.category, option.estimated_cost].filter(Boolean).join(" - ")}
                </Text>
                <Text numberOfLines={2} style={styles.optionWhy}>{option.why_it_fits}</Text>
              </View>
            ))}
          </View>
        ) : null}
      </View>
    </View>
  );
}

function MetaPill({ icon: Icon, label }: { icon: LucideIcon; label: string }) {
  return (
    <View style={styles.metaPill}>
      <Icon color={colors.moss} size={15} strokeWidth={2.2} />
      <Text numberOfLines={1} style={styles.metaPillText}>{label}</Text>
    </View>
  );
}

function getTimelineIcon(card: MobilePlanCard): LucideIcon {
  if (card.kind === "meal") {
    return Utensils;
  }
  if (card.kind === "cafe") {
    return Coffee;
  }
  if (card.kind === "transport") {
    return Bus;
  }
  if (card.kind === "break_time" || card.kind === "free_time") {
    return Clock3;
  }
  if (card.kind === "accommodation") {
    return BedDouble;
  }

  return Landmark;
}

function getTimelineTone(card: MobilePlanCard): TimelineTone {
  if (card.kind === "meal" || card.kind === "cafe") {
    return "orange";
  }
  if (card.kind === "transport") {
    return "moss";
  }

  return "sage";
}

function getAccentStyle(tone: TimelineTone) {
  if (tone === "orange") {
    return {
      bubble: styles.orangeBubble,
      iconColor: colors.primaryPressed,
    };
  }

  if (tone === "moss") {
    return {
      bubble: styles.mossBubble,
      iconColor: colors.moss,
    };
  }

  return {
    bubble: styles.sageBubble,
    iconColor: colors.sage,
  };
}

function getPlanDateLabel(days: MobilePlanDay[]) {
  const dates = days.map((day) => day.date).filter(Boolean);

  if (dates.length === 0) {
    return "Dates not set";
  }

  if (dates.length === 1) {
    return formatShortDate(dates[0]);
  }

  return `${formatShortDate(dates[0])} - ${formatShortDate(dates[dates.length - 1])}`;
}

function formatShortDate(value: string | null) {
  if (!value) {
    return "Dates not set";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
  }).format(date);
}

function getStopCount(days: MobilePlanDay[]) {
  return days.reduce((total, day) => total + day.cards.length, 0);
}

function getNextDayIndex(currentIndex: number, dayCount: number) {
  if (dayCount === 0 || currentIndex >= dayCount - 1) {
    return 0;
  }

  return currentIndex + 1;
}

function getDaySummary(day: MobilePlanDay) {
  const meals = day.cards.filter((card) => card.kind === "meal" || card.kind === "cafe").length;
  const firstTime = day.cards[0]?.time.split("-")[0];
  const lastTime = day.cards[day.cards.length - 1]?.time.split("-")[1];
  const parts = [`${day.cards.length} stops`];

  if (firstTime && lastTime) {
    parts.push(`${firstTime}-${lastTime}`);
  }

  if (meals > 0) {
    parts.push(`${meals} food stops`);
  }

  return parts.join(" - ");
}

function getDestinationInitials(destination: string) {
  const parts = destination
    .split(",")
    .map((part) => part.trim())
    .filter(Boolean);

  if (parts.length >= 2) {
    return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
  }

  return destination.slice(0, 2).toUpperCase();
}

const styles = StyleSheet.create({
  hero: {
    backgroundColor: colors.surface,
    borderColor: "rgba(216, 195, 165, 0.76)",
    borderRadius: radius.lg,
    borderWidth: StyleSheet.hairlineWidth,
    overflow: "hidden",
    ...shadows.card,
  },
  heroArtwork: {
    backgroundColor: "#E9D8BF",
    height: 118,
    overflow: "hidden",
    position: "relative",
  },
  heroBlobOrange: {
    backgroundColor: "#F09A57",
    borderRadius: 100,
    height: 156,
    left: -42,
    opacity: 0.72,
    position: "absolute",
    top: -58,
    width: 156,
  },
  heroBlobSage: {
    backgroundColor: "#789B6F",
    borderRadius: 120,
    bottom: -84,
    height: 190,
    opacity: 0.78,
    position: "absolute",
    right: -46,
    width: 190,
  },
  heroOrb: {
    alignItems: "center",
    backgroundColor: "rgba(255, 249, 240, 0.78)",
    borderColor: "rgba(255, 255, 255, 0.84)",
    borderRadius: radius.pill,
    borderWidth: 1,
    height: 70,
    justifyContent: "center",
    left: spacing.xl,
    position: "absolute",
    top: spacing.xl,
    width: 70,
  },
  heroOrbText: {
    color: colors.moss,
    fontSize: 24,
    fontWeight: "900",
    letterSpacing: 1,
  },
  heroContent: {
    gap: spacing.sm,
    padding: spacing.lg,
  },
  title: {
    ...typography.heading,
  },
  destinationRow: {
    alignItems: "center",
    flexDirection: "row",
    gap: spacing.xs,
  },
  destination: {
    ...typography.subheading,
    color: colors.moss,
    flexShrink: 1,
  },
  metaGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.sm,
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
    maxWidth: 128,
  },
  highlights: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.sm,
  },
  dayTabScroll: {
    alignSelf: "center",
    backgroundColor: "rgba(255, 249, 240, 0.68)",
    borderColor: "rgba(39, 34, 29, 0.12)",
    borderRadius: radius.pill,
    borderWidth: 1,
    flexGrow: 0,
    maxWidth: "100%",
    paddingHorizontal: spacing.xs,
    paddingVertical: spacing.xs,
  },
  dayTabs: {
    alignItems: "center",
    gap: spacing.xs,
    justifyContent: "center",
  },
  dayTabWrap: {
    height: 48,
  },
  dayTab: {
    alignItems: "center",
    backgroundColor: "transparent",
    borderColor: "transparent",
    borderRadius: radius.pill,
    flex: 1,
    flexDirection: "row",
    justifyContent: "center",
    overflow: "hidden",
    paddingHorizontal: spacing.sm,
  },
  activeDayTab: {
    backgroundColor: colors.moss,
    borderColor: "transparent",
  },
  dayTabLiquid: {
    bottom: 0,
    left: 0,
    overflow: "hidden",
    position: "absolute",
    right: 0,
    top: 0,
  },
  dayTabOrange: {
    backgroundColor: "#F58A46",
    borderRadius: 54,
    height: 70,
    left: -22,
    opacity: 0.95,
    position: "absolute",
    top: -18,
    width: 82,
  },
  dayTabSage: {
    backgroundColor: "#7BAE77",
    borderRadius: 44,
    bottom: -24,
    height: 62,
    opacity: 0.88,
    position: "absolute",
    right: -12,
    width: 72,
  },
  dayTabSheen: {
    backgroundColor: "#F6C85F",
    borderRadius: 30,
    height: 14,
    left: 20,
    opacity: 0.42,
    position: "absolute",
    top: 8,
    transform: [{ rotate: "-18deg" }],
    width: 44,
  },
  dayTabNumber: {
    color: colors.ink,
    fontSize: 16,
    fontWeight: "900",
    zIndex: 1,
  },
  dayTabLabel: {
    ...typography.caption,
    color: colors.ink,
    fontWeight: "900",
    zIndex: 1,
  },
  activeDayTabText: {
    color: colors.white,
  },
  dayPanel: {
    gap: spacing.lg,
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
  dayMeta: {
    ...typography.caption,
    color: colors.muted,
  },
  timeline: {
    gap: spacing.md,
  },
  timelineRow: {
    flexDirection: "row",
    gap: spacing.md,
  },
  timelineRail: {
    alignItems: "center",
    width: 42,
  },
  iconBubble: {
    alignItems: "center",
    borderRadius: radius.pill,
    height: 38,
    justifyContent: "center",
    width: 38,
  },
  timelineLine: {
    backgroundColor: "rgba(216, 195, 165, 0.78)",
    flex: 1,
    marginTop: spacing.sm,
    minHeight: 78,
    width: 1,
  },
  timelineCard: {
    backgroundColor: colors.surface,
    borderColor: colors.clay,
    borderWidth: StyleSheet.hairlineWidth,
    borderRadius: radius.lg,
    flex: 1,
    gap: spacing.sm,
    padding: spacing.lg,
  },
  timelineCardHeader: {
    alignItems: "center",
    flexDirection: "row",
    gap: spacing.sm,
    justifyContent: "space-between",
  },
  cardHeaderBadges: {
    alignItems: "center",
    flexDirection: "row",
    flexShrink: 0,
    gap: spacing.xs,
  },
  timePill: {
    alignItems: "center",
    backgroundColor: colors.background,
    borderRadius: radius.pill,
    flexDirection: "row",
    gap: spacing.xs,
    paddingHorizontal: spacing.sm,
    paddingVertical: spacing.xs,
  },
  timePillText: {
    ...typography.caption,
    color: colors.primaryPressed,
    fontWeight: "900",
  },
  locationRow: {
    alignItems: "flex-start",
    flexDirection: "row",
    gap: spacing.xs,
  },
  locationText: {
    ...typography.caption,
    color: colors.moss,
    flexShrink: 1,
    fontWeight: "700",
  },
  cardTitle: {
    ...typography.subheading,
  },
  cardDescription: {
    ...typography.body,
    color: colors.muted,
    fontSize: 15,
    lineHeight: 22,
  },
  cardTags: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.xs,
  },
  cardTag: {
    ...typography.caption,
    backgroundColor: colors.background,
    borderRadius: radius.pill,
    color: colors.muted,
    paddingHorizontal: spacing.sm,
    paddingVertical: 3,
  },
  options: {
    gap: spacing.sm,
    marginTop: spacing.xs,
  },
  optionCard: {
    backgroundColor: "#F8EAD8",
    borderRadius: radius.md,
    gap: spacing.xs,
    padding: spacing.md,
  },
  optionTopRow: {
    alignItems: "center",
    flexDirection: "row",
    gap: spacing.sm,
    justifyContent: "space-between",
  },
  optionName: {
    ...typography.body,
    fontWeight: "800",
  },
  optionMeta: {
    ...typography.caption,
    color: colors.moss,
  },
  optionWhy: {
    ...typography.caption,
    color: colors.muted,
    fontWeight: "400",
  },
  orangeBubble: {
    backgroundColor: "rgba(232, 111, 44, 0.14)",
  },
  sageBubble: {
    backgroundColor: "rgba(111, 143, 114, 0.18)",
  },
  mossBubble: {
    backgroundColor: "rgba(53, 94, 59, 0.12)",
  },
  stateCard: {
    alignItems: "center",
    backgroundColor: colors.surface,
    borderColor: colors.clay,
    borderRadius: radius.lg,
    borderWidth: StyleSheet.hairlineWidth,
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
