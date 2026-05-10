import { router } from "expo-router";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { colors, radius, shadows, spacing, typography } from "../theme/tokens";

type TabKey = "home" | "saved" | "itineraries" | "profile" | "nori";

type AppTabBarProps = {
  active: TabKey;
};

export function AppTabBar({ active }: AppTabBarProps) {
  return (
    <View style={styles.wrap}>
      <View style={styles.bar}>
        <View style={styles.tabGroup}>
          <TabButton
            active={active === "home"}
            label="Home"
            onPress={() => router.replace("/")}
          />
          <TabButton
            active={active === "saved"}
            label="Saved"
            onPress={() => router.replace("/saved")}
          />
        </View>

        <View style={styles.noriLane}>
          <Pressable
            accessibilityLabel="Chat with Nori"
            accessibilityRole="button"
            onPress={() => router.push("/nori")}
            style={[styles.noriButton, active === "nori" && styles.activeNoriButton]}
          >
            <View style={styles.noriOrb}>
              <View style={[styles.orbBlob, styles.orbOrange]} />
              <View style={[styles.orbBlob, styles.orbSage]} />
              <View style={[styles.orbBlob, styles.orbCream]} />
              <Text style={styles.noriText}>N</Text>
            </View>
          </Pressable>
        </View>

        <View style={styles.tabGroup}>
          <TabButton
            active={active === "itineraries"}
            label="Trips"
            onPress={() => router.replace("/itineraries")}
          />
          <TabButton
            active={active === "profile"}
            label="Profile"
            onPress={() => router.replace("/profile")}
          />
        </View>
      </View>
    </View>
  );
}

type TabButtonProps = {
  active: boolean;
  label: string;
  onPress: () => void;
};

function TabButton({ active, label, onPress }: TabButtonProps) {
  return (
    <Pressable
      accessibilityRole="button"
      disabled={!label}
      onPress={onPress}
      style={styles.tabButton}
    >
      {label ? (
        <>
          <View style={[styles.tabDot, active && styles.activeDot]} />
          <Text style={[styles.tabLabel, active && styles.activeLabel]}>{label}</Text>
        </>
      ) : null}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  wrap: {
    paddingTop: spacing.sm,
  },
  bar: {
    alignItems: "center",
    backgroundColor: colors.surface,
    borderColor: colors.clay,
    borderRadius: radius.lg,
    borderWidth: 1,
    flexDirection: "row",
    minHeight: 78,
    paddingHorizontal: spacing.sm,
    ...shadows.card,
  },
  tabGroup: {
    flex: 1,
    flexDirection: "row",
  },
  noriLane: {
    alignItems: "center",
    justifyContent: "center",
    minHeight: 78,
    width: 92,
  },
  tabButton: {
    alignItems: "center",
    flex: 1,
    gap: spacing.xs,
    justifyContent: "center",
    minHeight: 58,
  },
  tabDot: {
    backgroundColor: "transparent",
    borderRadius: radius.pill,
    height: 6,
    width: 6,
  },
  activeDot: {
    backgroundColor: colors.primary,
  },
  tabLabel: {
    ...typography.caption,
    color: colors.muted,
  },
  activeLabel: {
    color: colors.ink,
  },
  noriButton: {
    alignItems: "center",
    justifyContent: "center",
    transform: [{ translateY: -22 }],
  },
  activeNoriButton: {
    transform: [{ translateY: -22 }, { scale: 1.05 }],
  },
  noriOrb: {
    alignItems: "center",
    backgroundColor: colors.ink,
    borderColor: colors.surface,
    borderRadius: 34,
    borderWidth: 4,
    height: 68,
    justifyContent: "center",
    overflow: "hidden",
    width: 68,
    ...shadows.card,
  },
  orbBlob: {
    borderRadius: 40,
    position: "absolute",
  },
  orbOrange: {
    backgroundColor: "#F38B42",
    height: 52,
    left: -12,
    top: 6,
    width: 52,
  },
  orbSage: {
    backgroundColor: "#8AB983",
    height: 58,
    right: -14,
    top: -10,
    width: 58,
  },
  orbCream: {
    backgroundColor: "#FFE8AF",
    bottom: -16,
    height: 46,
    right: 10,
    width: 46,
  },
  noriText: {
    color: colors.white,
    fontSize: 24,
    fontWeight: "900",
    zIndex: 1,
  },
});
