import { Redirect } from "expo-router";
import { useState } from "react";
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";

import { sendNoriChat } from "../src/api/client";
import { useAuth } from "../src/auth/AuthContext";
import { AppTabBar, APP_TAB_BAR_OVERLAY_HEIGHT } from "../src/components/AppTabBar";
import { Screen } from "../src/components/Screen";
import { colors, radius, shadows, spacing, typography } from "../src/theme/tokens";

type ChatMessage = {
  role: "assistant" | "user";
  content: string;
};

const STARTER_MESSAGES: ChatMessage[] = [
  {
    role: "assistant",
    content: "I am here. Ask me for trip ideas, a quick plan tweak, or a softer version of an itinerary.",
  },
];

export default function NoriScreen() {
  const { isAuthenticated } = useAuth();
  const [messages, setMessages] = useState<ChatMessage[]>(STARTER_MESSAGES);
  const [input, setInput] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  if (!isAuthenticated) {
    return <Redirect href="/onboarding" />;
  }

  async function sendMessage() {
    const prompt = input.trim();

    if (!prompt || isSending) {
      return;
    }

    const nextMessages: ChatMessage[] = [
      ...messages,
      { role: "user", content: prompt },
    ];

    setMessages(nextMessages);
    setInput("");
    setIsSending(true);
    setErrorMessage(null);

    try {
      const response = await sendNoriChat(
        `You are Nori, a warm travel assistant inside Northstar. Keep the answer concise and practical.\n\nUser: ${prompt}`,
      );
      setMessages([
        ...nextMessages,
        { role: "assistant", content: response.message },
      ]);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Nori could not respond.");
    } finally {
      setIsSending(false);
    }
  }

  return (
    <Screen padded={false} scroll={false}>
      <KeyboardAvoidingView
        behavior={Platform.OS === "ios" ? "padding" : undefined}
        style={styles.container}
      >
        <View style={styles.header}>
          <View style={styles.orb}>
            <View style={[styles.orbBlob, styles.orbOrange]} />
            <View style={[styles.orbBlob, styles.orbSage]} />
            <View style={[styles.orbBlob, styles.orbCream]} />
            <Text style={styles.orbText}>N</Text>
          </View>
          <View style={styles.headerCopy}>
            <Text style={styles.kicker}>Nori</Text>
            <Text style={styles.title}>Ask for a trip idea.</Text>
          </View>
        </View>

        {errorMessage ? (
          <View style={styles.errorCard}>
            <Text style={styles.errorText}>{errorMessage}</Text>
          </View>
        ) : null}

        <ScrollView
          contentContainerStyle={styles.messages}
          showsVerticalScrollIndicator={false}
          style={styles.messageList}
        >
          {messages.map((message, index) => (
            <View
              key={`${message.role}-${index}`}
              style={[
                styles.bubble,
                message.role === "user" ? styles.userBubble : styles.assistantBubble,
              ]}
            >
              <Text style={styles.bubbleLabel}>{message.role === "user" ? "You" : "Nori"}</Text>
              <Text style={styles.bubbleText}>{message.content}</Text>
            </View>
          ))}

          {isSending ? (
            <View style={[styles.bubble, styles.assistantBubble]}>
              <ActivityIndicator color={colors.primary} />
            </View>
          ) : null}
        </ScrollView>

        <View style={styles.composer}>
          <TextInput
            multiline
            onChangeText={setInput}
            placeholder="Ask Nori..."
            placeholderTextColor={colors.muted}
            style={styles.input}
            value={input}
          />
          <Pressable
            accessibilityRole="button"
            disabled={!input.trim() || isSending}
            onPress={sendMessage}
            style={({ pressed }) => [
              styles.sendButton,
              pressed && styles.sendButtonPressed,
              (!input.trim() || isSending) && styles.sendButtonDisabled,
            ]}
          >
            <Text style={styles.sendButtonText}>Send</Text>
          </Pressable>
        </View>

        <AppTabBar active="chat" />
      </KeyboardAvoidingView>
    </Screen>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    gap: spacing.md,
  },
  header: {
    alignItems: "center",
    backgroundColor: colors.surface,
    borderColor: colors.clay,
    borderRadius: radius.lg,
    borderWidth: 1,
    flexDirection: "row",
    gap: spacing.lg,
    marginHorizontal: spacing.xl,
    marginTop: spacing.xl,
    padding: spacing.lg,
    ...shadows.card,
  },
  orb: {
    alignItems: "center",
    backgroundColor: colors.ink,
    borderRadius: 36,
    height: 72,
    justifyContent: "center",
    overflow: "hidden",
    width: 72,
  },
  orbBlob: {
    borderRadius: 40,
    position: "absolute",
  },
  orbOrange: {
    backgroundColor: "#F38B42",
    height: 56,
    left: -12,
    top: 8,
    width: 56,
  },
  orbSage: {
    backgroundColor: "#8AB983",
    height: 60,
    right: -14,
    top: -10,
    width: 60,
  },
  orbCream: {
    backgroundColor: "#FFE8AF",
    bottom: -14,
    height: 46,
    right: 10,
    width: 46,
  },
  orbText: {
    color: colors.white,
    fontSize: 28,
    fontWeight: "900",
    zIndex: 1,
  },
  headerCopy: {
    flex: 1,
  },
  kicker: {
    ...typography.caption,
    color: colors.primaryPressed,
    textTransform: "uppercase",
  },
  title: {
    ...typography.heading,
    marginTop: spacing.xs,
  },
  errorCard: {
    backgroundColor: "#F7D4BD",
    borderRadius: radius.md,
    marginHorizontal: spacing.xl,
    padding: spacing.md,
  },
  errorText: {
    ...typography.caption,
    color: colors.error,
  },
  messageList: {
    flex: 1,
  },
  messages: {
    gap: spacing.md,
    paddingHorizontal: spacing.xl,
    paddingBottom: spacing.md,
  },
  bubble: {
    borderRadius: radius.lg,
    gap: spacing.xs,
    maxWidth: "88%",
    padding: spacing.lg,
  },
  assistantBubble: {
    alignSelf: "flex-start",
    backgroundColor: colors.surface,
    borderColor: colors.clay,
    borderWidth: 1,
  },
  userBubble: {
    alignSelf: "flex-end",
    backgroundColor: "#F7D4BD",
  },
  bubbleLabel: {
    ...typography.caption,
    color: colors.moss,
  },
  bubbleText: {
    ...typography.body,
  },
  composer: {
    alignItems: "flex-end",
    backgroundColor: colors.surface,
    borderColor: colors.clay,
    borderRadius: radius.lg,
    borderWidth: 1,
    flexDirection: "row",
    gap: spacing.sm,
    marginBottom: APP_TAB_BAR_OVERLAY_HEIGHT,
    marginHorizontal: spacing.xl,
    padding: spacing.sm,
  },
  input: {
    ...typography.body,
    flex: 1,
    maxHeight: 120,
    minHeight: 48,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
  },
  sendButton: {
    alignItems: "center",
    backgroundColor: colors.primary,
    borderRadius: radius.pill,
    justifyContent: "center",
    minHeight: 44,
    paddingHorizontal: spacing.lg,
  },
  sendButtonPressed: {
    backgroundColor: colors.primaryPressed,
  },
  sendButtonDisabled: {
    opacity: 0.45,
  },
  sendButtonText: {
    ...typography.caption,
    color: colors.white,
  },
});
