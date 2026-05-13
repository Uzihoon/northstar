import type { ReactNode } from "react";
import { ScrollView, StyleSheet, View } from "react-native";
import { SafeAreaView, type Edges } from "react-native-safe-area-context";

import { colors, spacing } from "../theme/tokens";

type ScreenProps = {
  children: ReactNode;
  edges?: Edges;
  scroll?: boolean;
};

export function Screen({
  children,
  edges = ["top", "left", "right"],
  scroll = true,
}: ScreenProps) {
  if (!scroll) {
    return (
      <SafeAreaView edges={edges} style={styles.safeArea}>
        <View style={[styles.content, styles.staticContent]}>{children}</View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView edges={edges} style={styles.safeArea}>
      <ScrollView
        style={styles.scroll}
        contentContainerStyle={styles.content}
        showsVerticalScrollIndicator={false}
      >
        {children}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: colors.background,
  },
  scroll: {
    flex: 1,
  },
  content: {
    gap: spacing.lg,
    padding: spacing.xl,
    paddingBottom: spacing.xxl,
  },
  staticContent: {
    flex: 1,
  },
});
