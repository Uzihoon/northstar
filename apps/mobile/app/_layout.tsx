import { Stack } from "expo-router";
import { StatusBar } from "expo-status-bar";

import { colors } from "../src/theme/tokens";

export default function RootLayout() {
  return (
    <>
      <StatusBar style="dark" />
      <Stack
        screenOptions={{
          contentStyle: { backgroundColor: colors.background },
          headerBackTitle: "Back",
          headerShadowVisible: false,
          headerStyle: { backgroundColor: colors.background },
          headerTintColor: colors.ink,
          headerTitleStyle: { fontWeight: "800" },
        }}
      >
        <Stack.Screen name="index" options={{ headerShown: false }} />
        <Stack.Screen name="onboarding" options={{ title: "Meet Nori" }} />
        <Stack.Screen name="destinations/[id]" options={{ title: "Trip Setup" }} />
        <Stack.Screen name="plans/[id]" options={{ title: "Itinerary" }} />
      </Stack>
    </>
  );
}
