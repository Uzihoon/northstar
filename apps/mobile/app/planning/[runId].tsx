import { Redirect, router, useLocalSearchParams } from "expo-router";
import { Sparkles } from "lucide-react-native";
import { useEffect, useMemo, useRef, useState } from "react";
import {
  ActivityIndicator,
  Animated,
  Easing,
  Pressable,
  StyleSheet,
  Text,
  View,
} from "react-native";

import { getPlanRun } from "../../src/api/client";
import type { ItineraryPlanRunResponse, PlanRunEvent } from "../../src/api/types";
import { useAuth } from "../../src/auth/AuthContext";
import { PrimaryButton } from "../../src/components/PrimaryButton";
import { Screen } from "../../src/components/Screen";
import { colors, radius, shadows, spacing, typography } from "../../src/theme/tokens";

const LOADING_LINES = [
  "Nori is checking if that cafe is actually worth the hype.",
  "Sorting temples, snacks, and please-don't-wake-me-up-too-early energy.",
  "Building the gentle route, not the spreadsheet route.",
  "Negotiating with time so your afternoon still has breathing room.",
  "Finding the version of this trip with better coffee and fewer regrets.",
];

const POLL_INTERVAL_MS = 2000;

function firstParam(value: string | string[] | undefined): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}

export default function PlanningRunScreen() {
  const { isAuthenticated } = useAuth();
  const params = useLocalSearchParams();
  const runId = firstParam(params.runId);
  const [run, setRun] = useState<ItineraryPlanRunResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const loadingLine = useMemo(() => {
    const index = Math.floor(Math.random() * LOADING_LINES.length);

    return LOADING_LINES[index] ?? LOADING_LINES[0];
  }, []);

  const pulse = useRef(new Animated.Value(0)).current;
  const orbit = useRef(new Animated.Value(0)).current;
  const sparkle = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    const pulseAnimation = Animated.loop(
      Animated.sequence([
        Animated.timing(pulse, {
          duration: 1450,
          easing: Easing.inOut(Easing.sin),
          toValue: 1,
          useNativeDriver: true,
        }),
        Animated.timing(pulse, {
          duration: 1450,
          easing: Easing.inOut(Easing.sin),
          toValue: 0,
          useNativeDriver: true,
        }),
      ]),
    );
    const orbitAnimation = Animated.loop(
      Animated.timing(orbit, {
        duration: 5200,
        easing: Easing.linear,
        toValue: 1,
        useNativeDriver: true,
      }),
    );
    const sparkleAnimation = Animated.loop(
      Animated.sequence([
        Animated.timing(sparkle, {
          duration: 900,
          easing: Easing.out(Easing.quad),
          toValue: 1,
          useNativeDriver: true,
        }),
        Animated.timing(sparkle, {
          duration: 900,
          easing: Easing.in(Easing.quad),
          toValue: 0,
          useNativeDriver: true,
        }),
      ]),
    );

    pulseAnimation.start();
    orbitAnimation.start();
    sparkleAnimation.start();

    return () => {
      pulseAnimation.stop();
      orbitAnimation.stop();
      sparkleAnimation.stop();
    };
  }, [orbit, pulse, sparkle]);

  useEffect(() => {
    if (!runId) {
      setErrorMessage("Planning run id is missing.");
      return undefined;
    }

    const planningRunId = runId;
    let isMounted = true;
    let interval: ReturnType<typeof setInterval> | undefined;

    async function loadRun() {
      try {
        const nextRun = await getPlanRun(planningRunId);

        if (!isMounted) {
          return;
        }

        setRun(nextRun);
        setErrorMessage(null);

        if (nextRun.status === "completed" && nextRun.plan_id) {
          router.replace({
            pathname: "/plans/[id]",
            params: { id: nextRun.plan_id },
          });
        }

        if (nextRun.status === "failed") {
          setErrorMessage(nextRun.error_message ?? "Nori could not finish this plan.");
          if (interval) {
            clearInterval(interval);
          }
        }
      } catch (error) {
        if (isMounted) {
          setErrorMessage(error instanceof Error ? error.message : "Could not check planning status.");
        }
      }
    }

    loadRun();
    interval = setInterval(loadRun, POLL_INTERVAL_MS);

    return () => {
      isMounted = false;
      if (interval) {
        clearInterval(interval);
      }
    };
  }, [runId]);

  if (!isAuthenticated) {
    return <Redirect href="/onboarding" />;
  }

  const progressEvents = run?.progress_events ?? [];
  const statusLabel = getStatusLabel(run?.status);
  const pulseScale = pulse.interpolate({
    inputRange: [0, 1],
    outputRange: [0.96, 1.08],
  });
  const pulseOpacity = pulse.interpolate({
    inputRange: [0, 1],
    outputRange: [0.58, 0.9],
  });
  const orbitRotate = orbit.interpolate({
    inputRange: [0, 1],
    outputRange: ["0deg", "360deg"],
  });
  const sparkleScale = sparkle.interpolate({
    inputRange: [0, 1],
    outputRange: [0.82, 1.18],
  });
  const sparkleOpacity = sparkle.interpolate({
    inputRange: [0, 1],
    outputRange: [0.36, 1],
  });

  return (
    <Screen edges={["top", "left", "right", "bottom"]} padded={false} scroll={false}>
      <View style={styles.container}>
        <View style={styles.backgroundBlobOrange} />
        <View style={styles.backgroundBlobSage} />

        <View style={styles.centerStage}>
          <View style={styles.animationWrap}>
            <Animated.View
              style={[
                styles.glowRing,
                {
                  opacity: pulseOpacity,
                  transform: [{ scale: pulseScale }],
                },
              ]}
            />
            <Animated.View style={[styles.orbitRing, { transform: [{ rotate: orbitRotate }] }]}>
              <View style={styles.orbitDot} />
              <View style={[styles.orbitDot, styles.orbitDotTwo]} />
            </Animated.View>
            <Animated.View
              style={[
                styles.sparkleBubble,
                {
                  opacity: sparkleOpacity,
                  transform: [{ scale: sparkleScale }],
                },
              ]}
            >
              <Sparkles color={colors.surface} size={24} strokeWidth={2.4} />
            </Animated.View>
            <View style={styles.noriOrb}>
              <View style={[styles.noriBlob, styles.noriOrange]} />
              <View style={[styles.noriBlob, styles.noriSage]} />
              <View style={[styles.noriBlob, styles.noriCream]} />
              <Text style={styles.noriText}>N</Text>
            </View>
          </View>

          <Text style={styles.statusLabel}>{statusLabel}</Text>
          <Text style={styles.title}>Nori is making the itinerary.</Text>
          <Text style={styles.loadingLine}>{loadingLine}</Text>
          <Text style={styles.leaveNote}>
            You can leave this page now. Nori will keep planning and save the trip when it is ready.
          </Text>

          {errorMessage ? (
            <View style={styles.errorCard}>
              <Text style={styles.errorText}>{errorMessage}</Text>
            </View>
          ) : (
            <ActivityIndicator color={colors.primary} />
          )}
        </View>

        <ProgressCard events={progressEvents} />

        <View style={styles.actions}>
          <PrimaryButton label="Explore while Nori plans" onPress={() => router.replace("/")} />
          <Pressable
            accessibilityRole="button"
            onPress={() => router.replace("/itineraries")}
            style={styles.secondaryAction}
          >
            <Text style={styles.secondaryActionText}>View saved journeys</Text>
          </Pressable>
        </View>
      </View>
    </Screen>
  );
}

function ProgressCard({ events }: { events: PlanRunEvent[] }) {
  const visibleEvents = events.length > 0
    ? events.slice(-3)
    : [{ status: "queued", message: "Planning run queued." }];

  return (
    <View style={styles.progressCard}>
      <Text style={styles.progressTitle}>Tiny travel machine status</Text>
      {visibleEvents.map((event, index) => (
        <View key={`${event.status}-${index}`} style={styles.progressRow}>
          <View style={styles.progressDot} />
          <Text style={styles.progressText}>{event.message}</Text>
        </View>
      ))}
    </View>
  );
}

function getStatusLabel(status: ItineraryPlanRunResponse["status"] | undefined) {
  if (status === "running") {
    return "Mixing route magic";
  }

  if (status === "completed") {
    return "Ready";
  }

  if (status === "failed") {
    return "Needs another try";
  }

  return "Warming up";
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: "space-between",
    overflow: "hidden",
    padding: spacing.xl,
    paddingBottom: spacing.xxl,
  },
  backgroundBlobOrange: {
    backgroundColor: "#F7D4BD",
    borderRadius: 170,
    height: 260,
    opacity: 0.62,
    position: "absolute",
    right: -96,
    top: 72,
    width: 260,
  },
  backgroundBlobSage: {
    backgroundColor: "#DDE8D4",
    borderRadius: 190,
    bottom: 96,
    height: 290,
    left: -130,
    opacity: 0.72,
    position: "absolute",
    width: 290,
  },
  centerStage: {
    alignItems: "center",
    flex: 1,
    gap: spacing.md,
    justifyContent: "center",
    paddingTop: spacing.xxl,
  },
  animationWrap: {
    alignItems: "center",
    height: 210,
    justifyContent: "center",
    marginBottom: spacing.md,
    width: 210,
  },
  glowRing: {
    backgroundColor: "#FFE1C7",
    borderRadius: 95,
    height: 190,
    position: "absolute",
    width: 190,
  },
  orbitRing: {
    alignItems: "center",
    borderColor: "rgba(111, 143, 114, 0.34)",
    borderRadius: 96,
    borderWidth: 1,
    height: 192,
    justifyContent: "flex-start",
    position: "absolute",
    width: 192,
  },
  orbitDot: {
    backgroundColor: colors.primary,
    borderRadius: 8,
    height: 16,
    top: -8,
    width: 16,
  },
  orbitDotTwo: {
    backgroundColor: colors.sage,
    position: "absolute",
    top: 184,
  },
  sparkleBubble: {
    alignItems: "center",
    backgroundColor: colors.moss,
    borderRadius: 27,
    height: 54,
    justifyContent: "center",
    position: "absolute",
    right: 16,
    top: 30,
    width: 54,
    zIndex: 3,
  },
  noriOrb: {
    alignItems: "center",
    backgroundColor: colors.ink,
    borderRadius: 72,
    height: 144,
    justifyContent: "center",
    overflow: "hidden",
    width: 144,
    ...shadows.card,
  },
  noriBlob: {
    borderRadius: 80,
    position: "absolute",
  },
  noriOrange: {
    backgroundColor: "#F58A46",
    height: 118,
    left: -28,
    top: 24,
    width: 118,
  },
  noriSage: {
    backgroundColor: "#7BAE77",
    height: 128,
    right: -32,
    top: -22,
    width: 128,
  },
  noriCream: {
    backgroundColor: "#FFE8AF",
    bottom: -24,
    height: 92,
    right: 20,
    width: 92,
  },
  noriText: {
    color: colors.surface,
    fontSize: 52,
    fontWeight: "900",
    zIndex: 2,
  },
  statusLabel: {
    ...typography.caption,
    color: colors.primaryPressed,
    fontWeight: "900",
    letterSpacing: 0.8,
    textTransform: "uppercase",
  },
  title: {
    ...typography.heading,
    maxWidth: 290,
    textAlign: "center",
  },
  loadingLine: {
    color: colors.moss,
    fontSize: 18,
    fontWeight: "800",
    lineHeight: 25,
    maxWidth: 320,
    textAlign: "center",
  },
  leaveNote: {
    color: colors.muted,
    fontSize: 15,
    fontWeight: "400",
    lineHeight: 22,
    maxWidth: 326,
    textAlign: "center",
  },
  errorCard: {
    backgroundColor: "#F7D4BD",
    borderRadius: radius.md,
    marginTop: spacing.xs,
    padding: spacing.md,
  },
  errorText: {
    ...typography.caption,
    color: colors.error,
    textAlign: "center",
  },
  progressCard: {
    backgroundColor: "rgba(255, 249, 240, 0.82)",
    borderColor: "rgba(39, 34, 29, 0.1)",
    borderRadius: radius.lg,
    borderWidth: StyleSheet.hairlineWidth,
    gap: spacing.md,
    padding: spacing.lg,
  },
  progressTitle: {
    ...typography.caption,
    color: colors.primaryPressed,
    fontWeight: "900",
    textTransform: "uppercase",
  },
  progressRow: {
    alignItems: "center",
    flexDirection: "row",
    gap: spacing.sm,
  },
  progressDot: {
    backgroundColor: colors.primary,
    borderRadius: radius.pill,
    height: 9,
    width: 9,
  },
  progressText: {
    ...typography.caption,
    color: colors.muted,
    flex: 1,
  },
  actions: {
    gap: spacing.sm,
    paddingTop: spacing.lg,
  },
  secondaryAction: {
    alignItems: "center",
    minHeight: 44,
    justifyContent: "center",
  },
  secondaryActionText: {
    ...typography.body,
    color: colors.moss,
    fontWeight: "800",
  },
});
