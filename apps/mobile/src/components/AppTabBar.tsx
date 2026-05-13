import { router } from "expo-router";
import {
  Bookmark,
  Home,
  Luggage,
  UserRound,
  type LucideIcon,
} from "lucide-react-native";
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
            Icon={Home}
            label="Home"
            onPress={() => router.replace("/")}
          />
          <TabButton
            active={active === "saved"}
            Icon={Bookmark}
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
            Icon={Luggage}
            label="Trips"
            onPress={() => router.replace("/itineraries")}
          />
          <TabButton
            active={active === "profile"}
            Icon={UserRound}
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
  Icon: LucideIcon;
  label: string;
  onPress: () => void;
};

function TabButton({ active, Icon, label, onPress }: TabButtonProps) {
  const color = active ? colors.ink : colors.muted;

  return (
    <Pressable
      accessibilityRole="button"
      onPress={onPress}
      style={styles.tabButton}
    >
      <View style={[styles.iconWrap, active && styles.activeIconWrap]}>
        <Icon color={color} size={21} strokeWidth={2.2} />
      </View>
      <Text style={[styles.tabLabel, active && styles.activeLabel]}>{label}</Text>
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
    gap: 3,
    justifyContent: "center",
    minHeight: 62,
  },
  iconWrap: {
    alignItems: "center",
    borderRadius: radius.pill,
    height: 32,
    justifyContent: "center",
    width: 38,
  },
  activeIconWrap: {
    backgroundColor: "#F7D4BD",
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
