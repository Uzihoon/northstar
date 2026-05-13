import { ImageBackground, Pressable, StyleSheet, Text, View } from "react-native";

import type { Destination } from "../api/types";
import { colors, radius, shadows, spacing, typography } from "../theme/tokens";
import { Pill } from "./Pill";

type DestinationCardProps = {
  destination: Destination;
  onPress: () => void;
};

export function DestinationCard({ destination, onPress }: DestinationCardProps) {
  return (
    <Pressable accessibilityRole="button" onPress={onPress} style={styles.card}>
      {destination.hero_image_url ? (
        <ImageBackground
          imageStyle={styles.heroImage}
          source={{ uri: destination.hero_image_url }}
          style={styles.imagePlaceholder}
        >
          <HeroOverlay destination={destination} />
        </ImageBackground>
      ) : (
        <View style={styles.imagePlaceholder}>
          <View style={styles.sunBlob} />
          <View style={styles.hillBlob} />
          <View style={styles.pathBlob} />
          <HeroOverlay destination={destination} />
        </View>
      )}
      <View style={styles.body}>
        <Text style={styles.title}>{destination.city}, {destination.country}</Text>
        <Text ellipsizeMode="tail" numberOfLines={3} style={styles.summary}>{destination.summary}</Text>
        <View style={styles.pills}>
          {destination.vibes.slice(0, 2).map((vibe) => (
            <Pill key={vibe} label={vibe} tone="sage" />
          ))}
        </View>
      </View>
    </Pressable>
  );
}

type HeroOverlayProps = {
  destination: Destination;
};

function HeroOverlay({ destination }: HeroOverlayProps) {
  return (
    <View style={styles.heroOverlay}>
      <View>
        <Text style={styles.imageText}>{destination.city.slice(0, 2).toUpperCase()}</Text>
        <Text style={styles.imageCaption}>{destination.vibes[0] ?? "personal trip"}</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.surface,
    borderColor: colors.clay,
    borderRadius: radius.lg,
    borderWidth: 1,
    flex: 1,
    overflow: "hidden",
    ...shadows.card,
  },
  imagePlaceholder: {
    backgroundColor: "#244A32",
    height: 232,
    justifyContent: "flex-end",
    overflow: "hidden",
  },
  heroImage: {
    borderTopLeftRadius: radius.lg,
    borderTopRightRadius: radius.lg,
  },
  sunBlob: {
    backgroundColor: "#F59E45",
    borderRadius: 90,
    height: 150,
    opacity: 0.95,
    position: "absolute",
    right: -18,
    top: -24,
    width: 150,
  },
  hillBlob: {
    backgroundColor: "#7FA56E",
    borderRadius: 140,
    bottom: -88,
    height: 210,
    left: -34,
    opacity: 0.95,
    position: "absolute",
    width: 280,
  },
  pathBlob: {
    backgroundColor: "#F7D4BD",
    borderRadius: 90,
    bottom: -44,
    height: 124,
    opacity: 0.75,
    position: "absolute",
    right: -12,
    transform: [{ rotate: "-18deg" }],
    width: 170,
  },
  heroOverlay: {
    backgroundColor: "rgba(39, 34, 29, 0.18)",
    flex: 1,
    justifyContent: "flex-end",
    padding: spacing.lg,
  },
  imageText: {
    color: colors.background,
    fontSize: 58,
    fontWeight: "900",
    letterSpacing: 2,
  },
  imageCaption: {
    ...typography.caption,
    color: colors.background,
    textTransform: "uppercase",
  },
  body: {
    flex: 1,
    gap: spacing.sm,
    padding: spacing.lg,
  },
  title: {
    ...typography.subheading,
  },
  summary: {
    ...typography.body,
    color: colors.muted,
    maxHeight: 72,
  },
  pills: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.sm,
    paddingTop: spacing.xs,
  },
});
