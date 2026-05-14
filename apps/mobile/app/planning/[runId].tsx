import { Redirect, router, useLocalSearchParams } from "expo-router";
import { useEffect, useMemo, useRef, useState } from "react";
import {
  Animated,
  Easing,
  Pressable,
  StyleSheet,
  Text,
  View,
} from "react-native";

import { getPlanRun } from "../../src/api/client";
import type { ItineraryPlanRunResponse } from "../../src/api/types";
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

  const drift = useRef(new Animated.Value(0)).current;
  const bounce = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    const driftAnimation = Animated.loop(
      Animated.timing(drift, {
        duration: 3600,
        easing: Easing.inOut(Easing.sin),
        toValue: 1,
        useNativeDriver: true,
      }),
    );
    const bounceAnimation = Animated.loop(
      Animated.sequence([
        Animated.timing(bounce, {
          duration: 720,
          easing: Easing.out(Easing.cubic),
          toValue: 1,
          useNativeDriver: true,
        }),
        Animated.timing(bounce, {
          duration: 680,
          easing: Easing.in(Easing.quad),
          toValue: 0,
          useNativeDriver: true,
        }),
      ]),
    );

    driftAnimation.start();
    bounceAnimation.start();

    return () => {
      driftAnimation.stop();
      bounceAnimation.stop();
    };
  }, [bounce, drift]);

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

  const statusLabel = getStatusLabel(run?.status);
  const orangeTranslateX = drift.interpolate({
    inputRange: [0, 0.28, 0.58, 0.82, 1],
    outputRange: [-64, -22, 34, 70, -64],
  });
  const orangeTranslateY = bounce.interpolate({
    inputRange: [0, 0.5, 1],
    outputRange: [18, -34, 18],
  });
  const orangeRotate = drift.interpolate({
    inputRange: [0, 0.5, 1],
    outputRange: ["-12deg", "18deg", "-12deg"],
  });
  const sageTranslateX = drift.interpolate({
    inputRange: [0, 0.24, 0.54, 0.78, 1],
    outputRange: [56, 12, -54, -18, 56],
  });
  const sageTranslateY = bounce.interpolate({
    inputRange: [0, 0.5, 1],
    outputRange: [-16, 32, -16],
  });
  const sageRotate = drift.interpolate({
    inputRange: [0, 0.5, 1],
    outputRange: ["10deg", "-20deg", "10deg"],
  });
  const creamTranslateX = drift.interpolate({
    inputRange: [0, 0.3, 0.62, 0.84, 1],
    outputRange: [-18, 58, 12, -58, -18],
  });
  const creamTranslateY = bounce.interpolate({
    inputRange: [0, 0.5, 1],
    outputRange: [48, 4, 48],
  });
  const creamRotate = drift.interpolate({
    inputRange: [0, 0.5, 1],
    outputRange: ["18deg", "-14deg", "18deg"],
  });
  const shadowTranslateX = drift.interpolate({
    inputRange: [0, 0.5, 1],
    outputRange: [-22, 22, -22],
  });
  const shadowScale = bounce.interpolate({
    inputRange: [0, 0.5, 1],
    outputRange: [1.08, 0.78, 1.08],
  });
  const shadowOpacity = bounce.interpolate({
    inputRange: [0, 0.5, 1],
    outputRange: [0.22, 0.09, 0.22],
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
                styles.shadow,
                {
                  opacity: shadowOpacity,
                  transform: [
                    { translateX: shadowTranslateX },
                    { scaleX: shadowScale },
                  ],
                },
              ]}
            />
            <Animated.View
              style={[
                styles.shape,
                styles.orangeCircle,
                {
                  transform: [
                    { translateX: orangeTranslateX },
                    { translateY: orangeTranslateY },
                    { rotate: orangeRotate },
                  ],
                },
              ]}
            />
            <Animated.View
              style={[
                styles.shape,
                styles.sageRectangle,
                {
                  transform: [
                    { translateX: sageTranslateX },
                    { translateY: sageTranslateY },
                    { rotate: sageRotate },
                  ],
                },
              ]}
            />
            <Animated.View
              style={[
                styles.shape,
                styles.creamPill,
                {
                  transform: [
                    { translateX: creamTranslateX },
                    { translateY: creamTranslateY },
                    { rotate: creamRotate },
                  ],
                },
              ]}
            />
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
          ) : null}
        </View>

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
    height: 220,
    justifyContent: "center",
    marginBottom: spacing.md,
    width: 240,
  },
  shadow: {
    backgroundColor: "rgba(39, 34, 29, 0.22)",
    borderRadius: 45,
    bottom: 24,
    height: 18,
    position: "absolute",
    width: 128,
  },
  shape: {
    position: "absolute",
    ...shadows.card,
  },
  orangeCircle: {
    backgroundColor: colors.primary,
    borderRadius: 37,
    height: 74,
    width: 74,
  },
  sageRectangle: {
    backgroundColor: colors.sage,
    borderRadius: 23,
    height: 68,
    width: 96,
  },
  creamPill: {
    backgroundColor: "#FFE8AF",
    borderRadius: radius.pill,
    height: 42,
    width: 116,
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
