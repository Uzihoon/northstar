import { Redirect, router, useLocalSearchParams } from "expo-router";
import { Sparkles } from "lucide-react-native";
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

  const bounce = useRef(new Animated.Value(0)).current;
  const mix = useRef(new Animated.Value(0)).current;
  const sparkle = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    const bounceAnimation = Animated.loop(
      Animated.sequence([
        Animated.timing(bounce, {
          duration: 520,
          easing: Easing.out(Easing.cubic),
          toValue: 1,
          useNativeDriver: true,
        }),
        Animated.timing(bounce, {
          duration: 420,
          easing: Easing.in(Easing.quad),
          toValue: 0,
          useNativeDriver: true,
        }),
      ]),
    );
    const mixAnimation = Animated.loop(
      Animated.timing(mix, {
        duration: 2100,
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

    bounceAnimation.start();
    mixAnimation.start();
    sparkleAnimation.start();

    return () => {
      bounceAnimation.stop();
      mixAnimation.stop();
      sparkleAnimation.stop();
    };
  }, [bounce, mix, sparkle]);

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
  const orbTranslateY = bounce.interpolate({
    inputRange: [0, 0.55, 1],
    outputRange: [22, -34, 22],
  });
  const orbScaleX = bounce.interpolate({
    inputRange: [0, 0.18, 0.55, 1],
    outputRange: [1.13, 0.96, 1, 1.13],
  });
  const orbScaleY = bounce.interpolate({
    inputRange: [0, 0.18, 0.55, 1],
    outputRange: [0.88, 1.08, 1, 0.88],
  });
  const shadowScale = bounce.interpolate({
    inputRange: [0, 0.55, 1],
    outputRange: [1.18, 0.72, 1.18],
  });
  const shadowOpacity = bounce.interpolate({
    inputRange: [0, 0.55, 1],
    outputRange: [0.24, 0.08, 0.24],
  });
  const glowScale = bounce.interpolate({
    inputRange: [0, 0.55, 1],
    outputRange: [0.98, 1.18, 0.98],
  });
  const mixRotate = mix.interpolate({
    inputRange: [0, 1],
    outputRange: ["0deg", "360deg"],
  });
  const counterMixRotate = mix.interpolate({
    inputRange: [0, 1],
    outputRange: ["360deg", "0deg"],
  });
  const spoonRotate = bounce.interpolate({
    inputRange: [0, 0.5, 1],
    outputRange: ["-18deg", "18deg", "-18deg"],
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
                  transform: [{ scale: glowScale }],
                },
              ]}
            />
            <Animated.View
              style={[
                styles.shadow,
                {
                  opacity: shadowOpacity,
                  transform: [{ scaleX: shadowScale }],
                },
              ]}
            />
            <Animated.View style={[styles.mixingTrail, { transform: [{ rotate: mixRotate }] }]}>
              <Animated.View
                style={[
                  styles.ingredientDot,
                  styles.orangeDot,
                  { transform: [{ rotate: counterMixRotate }] },
                ]}
              />
              <Animated.View
                style={[
                  styles.ingredientDot,
                  styles.sageDot,
                  { transform: [{ rotate: counterMixRotate }] },
                ]}
              />
              <Animated.View
                style={[
                  styles.ingredientDot,
                  styles.creamDot,
                  { transform: [{ rotate: counterMixRotate }] },
                ]}
              />
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
            <Animated.View
              style={[
                styles.spoon,
                {
                  transform: [
                    { rotate: spoonRotate },
                    { translateY: -8 },
                  ],
                },
              ]}
            />
            <Animated.View
              style={[
                styles.noriOrb,
                {
                  transform: [
                    { translateY: orbTranslateY },
                    { scaleX: orbScaleX },
                    { scaleY: orbScaleY },
                  ],
                },
              ]}
            >
              <View style={[styles.noriBlob, styles.noriOrange]} />
              <View style={[styles.noriBlob, styles.noriSage]} />
              <View style={[styles.noriBlob, styles.noriCream]} />
              <Text style={styles.noriText}>N</Text>
            </Animated.View>
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
    height: 240,
    justifyContent: "center",
    marginBottom: spacing.md,
    width: 240,
  },
  glowRing: {
    backgroundColor: "rgba(255, 225, 199, 0.72)",
    borderRadius: 105,
    height: 210,
    position: "absolute",
    width: 210,
  },
  shadow: {
    backgroundColor: "rgba(39, 34, 29, 0.3)",
    borderRadius: 45,
    bottom: 30,
    height: 22,
    position: "absolute",
    width: 108,
  },
  mixingTrail: {
    alignItems: "center",
    borderColor: "rgba(111, 143, 114, 0.24)",
    borderRadius: 92,
    borderWidth: 1,
    height: 184,
    justifyContent: "flex-start",
    position: "absolute",
    width: 184,
  },
  ingredientDot: {
    borderColor: "rgba(255, 255, 255, 0.82)",
    borderRadius: 16,
    borderWidth: 2,
    height: 30,
    position: "absolute",
    width: 30,
  },
  orangeDot: {
    backgroundColor: colors.primary,
    top: -15,
  },
  sageDot: {
    backgroundColor: colors.sage,
    right: 2,
    top: 128,
  },
  creamDot: {
    backgroundColor: "#FFE8AF",
    left: 0,
    top: 118,
  },
  sparkleBubble: {
    alignItems: "center",
    backgroundColor: colors.moss,
    borderRadius: 27,
    height: 54,
    justifyContent: "center",
    position: "absolute",
    right: 18,
    top: 36,
    width: 54,
    zIndex: 3,
  },
  spoon: {
    backgroundColor: "rgba(255, 249, 240, 0.96)",
    borderColor: "rgba(39, 34, 29, 0.12)",
    borderRadius: 18,
    borderWidth: StyleSheet.hairlineWidth,
    height: 112,
    position: "absolute",
    right: 44,
    top: 24,
    width: 16,
    zIndex: 1,
  },
  noriOrb: {
    alignItems: "center",
    backgroundColor: colors.ink,
    borderRadius: 72,
    height: 144,
    justifyContent: "center",
    overflow: "hidden",
    width: 144,
    zIndex: 2,
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
