import { router } from "expo-router";
import {
  Compass,
  Luggage,
  UserRound,
  type LucideIcon,
} from "lucide-react-native";
import {
  Animated,
  Easing,
  Pressable,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { useEffect, useRef, useState } from "react";

import { colors, radius, spacing, typography } from "../theme/tokens";

type TabKey = "explore" | "trips" | "profile";

type AppTabBarProps = {
  active: TabKey;
};

type TabConfig = {
  key: TabKey;
  label: string;
  Icon: LucideIcon;
};

type ActiveMotion = {
  from: TabKey;
  to: TabKey;
};

const TABS: TabConfig[] = [
  { key: "explore", label: "Explore", Icon: Compass },
  { key: "trips", label: "Trips", Icon: Luggage },
  { key: "profile", label: "Profile", Icon: UserRound },
];

const BAR_HORIZONTAL_PADDING = spacing.sm;
const BAR_VERTICAL_PADDING = 6;
const ACTIVE_SLOT_WIDTH = 118;
const INACTIVE_SLOT_WIDTH = 52;
const COLLAPSED_PILL_SIZE = 52;
const PILL_HEIGHT = 52;
const COLLAPSED_BAR_WIDTH = BAR_HORIZONTAL_PADDING * 2 + INACTIVE_SLOT_WIDTH * TABS.length;
const EXPANDED_BAR_WIDTH =
  BAR_HORIZONTAL_PADDING * 2 + ACTIVE_SLOT_WIDTH + INACTIVE_SLOT_WIDTH * (TABS.length - 1);
const MOTION_INPUT_RANGE = [0, 0.52, 1];
const MENU_BAR_BACKGROUND = "rgba(255, 249, 240, 0.68)";
const TAB_BAR_BOTTOM_OFFSET = spacing.xl;

export const APP_TAB_BAR_OVERLAY_HEIGHT = 92;

export function AppTabBar({ active }: AppTabBarProps) {
  const [selectedTab, setSelectedTab] = useState<TabKey>(active);
  const [motion, setMotion] = useState<ActiveMotion | null>(null);
  const motionProgress = useRef(new Animated.Value(1)).current;
  const animationRef = useRef<Animated.CompositeAnimation | null>(null);
  const animationRun = useRef(0);
  const isAnimatingRef = useRef(false);
  const queuedTabRef = useRef<TabKey | null>(null);
  const settledTabRef = useRef<TabKey>(active);

  useEffect(() => {
    if (isAnimatingRef.current) {
      return;
    }

    stopActiveAnimation();
    motionProgress.setValue(1);
    settledTabRef.current = active;
    setSelectedTab(active);
    setMotion(null);
  }, [active, motionProgress]);

  useEffect(() => {
    return () => {
      stopActiveAnimation();
      animationRun.current += 1;
    };
  }, []);

  function navigate(tab: TabKey) {
    if (isAnimatingRef.current) {
      queuedTabRef.current = tab;
      return;
    }

    if (tab === settledTabRef.current) {
      setSelectedTab(tab);
      return;
    }

    startTransition(settledTabRef.current, tab);
  }

  function stopActiveAnimation() {
    animationRun.current += 1;

    if (animationRef.current) {
      animationRef.current.stop();
      animationRef.current = null;
    }

    motionProgress.stopAnimation();
  }

  function startTransition(from: TabKey, to: TabKey) {
    if (from === to) {
      settledTabRef.current = to;
      setSelectedTab(to);
      setMotion(null);
      return;
    }

    setSelectedTab(to);
    setMotion({ from, to });
    motionProgress.setValue(0);
    isAnimatingRef.current = true;

    const runId = animationRun.current + 1;
    animationRun.current = runId;
    animationRef.current = Animated.timing(motionProgress, {
      duration: 640,
      easing: Easing.bezier(0.22, 0.78, 0.22, 1),
      toValue: 1,
      useNativeDriver: false,
    });

    animationRef.current.start(({ finished }) => {
      if (!finished || animationRun.current !== runId) {
        return;
      }

      animationRef.current = null;
      settledTabRef.current = to;
      setMotion(null);
      motionProgress.setValue(1);

      const queuedTab = queuedTabRef.current;
      queuedTabRef.current = null;

      if (queuedTab && queuedTab !== to) {
        startTransition(to, queuedTab);
        return;
      }

      isAnimatingRef.current = false;
      navigateTo(to);
    });
  }

  const activeMotion = motion ?? { from: selectedTab, to: selectedTab };
  const fromActiveLeft = getActiveIndicatorLeft(activeMotion.from);
  const toCollapsedLeft = getCollapsedIndicatorLeft(activeMotion.to);
  const toActiveLeft = getActiveIndicatorLeft(activeMotion.to);
  const animatedBarWidth = motionProgress.interpolate({
    inputRange: MOTION_INPUT_RANGE,
    outputRange: [EXPANDED_BAR_WIDTH, COLLAPSED_BAR_WIDTH, EXPANDED_BAR_WIDTH],
  });
  const indicatorWidth = motionProgress.interpolate({
    inputRange: MOTION_INPUT_RANGE,
    outputRange: [ACTIVE_SLOT_WIDTH, COLLAPSED_PILL_SIZE, ACTIVE_SLOT_WIDTH],
  });
  const indicatorLeft = motionProgress.interpolate({
    inputRange: MOTION_INPUT_RANGE,
    outputRange: [fromActiveLeft, toCollapsedLeft, toActiveLeft],
  });
  const fromContentOpacity = motionProgress.interpolate({
    inputRange: [0, 0.16, 0.32],
    outputRange: [1, 0.35, 0],
  });
  const toContentOpacity = motionProgress.interpolate({
    inputRange: [0.52, 0.72, 1],
    outputRange: [0, 0.6, 1],
  });

  return (
    <View pointerEvents="box-none" style={styles.wrap}>
      <Animated.View
        style={[styles.bar, { width: animatedBarWidth }]}
      >
        <Animated.View
          pointerEvents="none"
          style={[
            styles.activeIndicator,
            {
              left: indicatorLeft,
              width: indicatorWidth,
            },
          ]}
        >
          <View style={styles.liquidLayer}>
            <View style={[styles.liquidBlob, styles.liquidOrange]} />
            <View style={[styles.liquidBlob, styles.liquidSage]} />
            <View style={[styles.liquidBlob, styles.liquidCream]} />
            <View style={styles.liquidSheen} />
          </View>

          {motion ? (
            <>
              <ActiveIndicatorContent opacity={fromContentOpacity} tab={motion.from} />
              <ActiveIndicatorContent opacity={toContentOpacity} tab={motion.to} />
            </>
          ) : (
            <ActiveIndicatorContent opacity={1} tab={selectedTab} />
          )}
        </Animated.View>

        {TABS.map((tab) => (
          <TabButton
            Icon={tab.Icon}
            key={tab.key}
            label={tab.label}
            motionProgress={motionProgress}
            motion={motion}
            onPress={() => navigate(tab.key)}
            stableActive={selectedTab === tab.key}
            selected={selectedTab === tab.key}
            tab={tab.key}
          />
        ))}
      </Animated.View>
    </View>
  );
}

function ActiveIndicatorContent({
  opacity,
  tab,
}: {
  opacity: Animated.AnimatedInterpolation<number> | number;
  tab: TabKey;
}) {
  const tabConfig = getTabConfig(tab);
  const Icon = tabConfig.Icon;

  return (
    <Animated.View style={[styles.activeIndicatorContent, { opacity }]}>
      <Icon color={colors.white} size={21} strokeWidth={2.2} />
      <Text numberOfLines={1} style={styles.activeLabel}>
        {tabConfig.label}
      </Text>
    </Animated.View>
  );
}

function TabButton({
  Icon,
  label,
  motion,
  motionProgress,
  onPress,
  stableActive,
  selected,
  tab,
}: {
  Icon: LucideIcon;
  label: string;
  motion: ActiveMotion | null;
  motionProgress: Animated.Value;
  onPress: () => void;
  stableActive: boolean;
  selected: boolean;
  tab: TabKey;
}) {
  const width = getTabWidth({ motion, motionProgress, stableActive, tab });

  return (
    <Animated.View style={[styles.tabSlot, { width }]}>
      <Pressable
        accessibilityLabel={label}
        accessibilityRole="button"
        accessibilityState={{ selected }}
        onPress={onPress}
        style={styles.tabPressable}
      >
        <Icon color={colors.ink} size={21} strokeWidth={2.2} />
      </Pressable>
    </Animated.View>
  );
}

function getTabWidth({
  motion,
  motionProgress,
  stableActive,
  tab,
}: {
  motion: ActiveMotion | null;
  motionProgress: Animated.Value;
  stableActive: boolean;
  tab: TabKey;
}) {
  if (!motion) {
    return stableActive ? ACTIVE_SLOT_WIDTH : INACTIVE_SLOT_WIDTH;
  }

  if (tab === motion.from) {
    return motionProgress.interpolate({
      inputRange: MOTION_INPUT_RANGE,
      outputRange: [ACTIVE_SLOT_WIDTH, INACTIVE_SLOT_WIDTH, INACTIVE_SLOT_WIDTH],
    });
  }

  if (tab === motion.to) {
    return motionProgress.interpolate({
      inputRange: MOTION_INPUT_RANGE,
      outputRange: [INACTIVE_SLOT_WIDTH, INACTIVE_SLOT_WIDTH, ACTIVE_SLOT_WIDTH],
    });
  }

  return INACTIVE_SLOT_WIDTH;
}

function getTabConfig(tab: TabKey) {
  return TABS.find((item) => item.key === tab) ?? TABS[0];
}

function getActiveIndicatorLeft(tab: TabKey) {
  const tabIndex = TABS.findIndex((item) => item.key === tab);

  return BAR_HORIZONTAL_PADDING + tabIndex * INACTIVE_SLOT_WIDTH;
}

function getCollapsedIndicatorLeft(tab: TabKey) {
  const tabIndex = TABS.findIndex((item) => item.key === tab);

  return BAR_HORIZONTAL_PADDING + tabIndex * INACTIVE_SLOT_WIDTH;
}

function navigateTo(tab: TabKey) {
  if (tab === "explore") {
    router.replace("/");
  } else if (tab === "trips") {
    router.replace("/itineraries");
  } else {
    router.replace("/profile");
  }
}

const styles = StyleSheet.create({
  wrap: {
    alignItems: "center",
    bottom: TAB_BAR_BOTTOM_OFFSET,
    left: 0,
    position: "absolute",
    right: 0,
    zIndex: 20,
  },
  bar: {
    alignItems: "center",
    alignSelf: "center",
    backgroundColor: MENU_BAR_BACKGROUND,
    borderColor: "rgba(39, 34, 29, 0.12)",
    borderWidth: 1,
    borderRadius: radius.pill,
    flexDirection: "row",
    justifyContent: "center",
    minHeight: 64,
    overflow: "hidden",
    paddingHorizontal: BAR_HORIZONTAL_PADDING,
    paddingVertical: BAR_VERTICAL_PADDING,
    position: "relative",
    shadowColor: "#6A4B2B",
    shadowOffset: { width: 0, height: 12 },
    shadowOpacity: 0.1,
    shadowRadius: 24,
    elevation: 8,
  },
  activeIndicator: {
    alignItems: "center",
    backgroundColor: colors.primary,
    borderRadius: radius.pill,
    height: PILL_HEIGHT,
    justifyContent: "center",
    overflow: "hidden",
    position: "absolute",
    top: BAR_VERTICAL_PADDING,
    zIndex: 2,
  },
  liquidLayer: {
    bottom: 0,
    left: 0,
    overflow: "hidden",
    position: "absolute",
    right: 0,
    top: 0,
  },
  liquidBlob: {
    position: "absolute",
  },
  liquidOrange: {
    backgroundColor: "#F58A46",
    borderRadius: 54,
    height: 70,
    left: -22,
    opacity: 0.95,
    top: -14,
    width: 82,
  },
  liquidSage: {
    backgroundColor: "#7BAE77",
    borderRadius: 44,
    bottom: -20,
    height: 62,
    opacity: 0.88,
    right: -12,
    width: 72,
  },
  liquidCream: {
    backgroundColor: "#FFE3A3",
    borderRadius: 34,
    height: 44,
    opacity: 0.7,
    right: 28,
    top: -14,
    width: 48,
  },
  liquidSheen: {
    backgroundColor: colors.white,
    borderRadius: 30,
    height: 18,
    left: 22,
    opacity: 0.18,
    position: "absolute",
    top: 8,
    transform: [{ rotate: "-18deg" }],
    width: 58,
  },
  activeIndicatorContent: {
    alignItems: "center",
    bottom: 0,
    flexDirection: "row",
    gap: spacing.sm,
    justifyContent: "center",
    left: 0,
    paddingHorizontal: spacing.sm,
    position: "absolute",
    right: 0,
    top: 0,
  },
  tabSlot: {
    minHeight: 56,
    zIndex: 1,
  },
  tabPressable: {
    alignItems: "center",
    flex: 1,
    justifyContent: "center",
    minHeight: 56,
  },
  activeLabel: {
    ...typography.caption,
    color: colors.white,
    fontWeight: "800",
  },
});
