import type { ReactNode, RefObject } from "react";
import { ScrollView, StyleSheet, View } from "react-native";
import { SafeAreaView, type Edges } from "react-native-safe-area-context";

import { colors, spacing } from "../theme/tokens";

type ScreenProps = {
  children: ReactNode;
  edges?: Edges;
  padded?: boolean;
  scroll?: boolean;
  scrollRef?: RefObject<ScrollView | null>;
};

export function Screen({
  children,
  edges = ["top", "left", "right"],
  padded = true,
  scroll = true,
  scrollRef,
}: ScreenProps) {
  if (!scroll) {
    return (
      <SafeAreaView edges={edges} style={styles.safeArea}>
        <View style={[padded ? styles.content : null, styles.staticContent]}>{children}</View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView edges={edges} style={styles.safeArea}>
      <ScrollView
        ref={scrollRef}
        style={styles.scroll}
        contentContainerStyle={padded ? styles.content : undefined}
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
