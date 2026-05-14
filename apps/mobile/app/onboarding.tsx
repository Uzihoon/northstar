import { router } from "expo-router";
import { useEffect, useState } from "react";
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

import { sendOnboardingMessages } from "../src/api/client";
import type { OnboardingMessage } from "../src/api/types";
import { useAuth } from "../src/auth/AuthContext";
import { Pill } from "../src/components/Pill";
import { PrimaryButton } from "../src/components/PrimaryButton";
import { Screen } from "../src/components/Screen";
import { colors, radius, shadows, spacing, typography } from "../src/theme/tokens";

const QUICK_REPLIES = [
  "I loved quiet cafes in Kyoto.",
  "I like slow days and bookstores.",
  "Food matters a lot when I travel.",
];

export default function OnboardingScreen() {
  const { completeOnboarding } = useAuth();
  const [messages, setMessages] = useState<OnboardingMessage[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isSending, setIsSending] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;

    async function loadOpeningMessage() {
      try {
        const response = await sendOnboardingMessages([]);
        if (isMounted) {
          setMessages([{ role: "assistant", content: response.assistant_message }]);
          setErrorMessage(null);
        }
      } catch (error) {
        if (isMounted) {
          setErrorMessage(error instanceof Error ? error.message : "Nori could not start onboarding.");
          setMessages([
            {
              role: "assistant",
              content: "Hi, I'm Nori. I'll learn your travel style through a few easy questions. What was a trip or city you really enjoyed?",
            },
          ]);
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    loadOpeningMessage();

    return () => {
      isMounted = false;
    };
  }, []);

  async function sendMessage(messageText = input) {
    const trimmed = messageText.trim();

    if (!trimmed || isSending) {
      return;
    }

    const nextMessages: OnboardingMessage[] = [
      ...messages,
      { role: "user", content: trimmed },
    ];

    setInput("");
    setMessages(nextMessages);
    setIsSending(true);
    setErrorMessage(null);

    try {
      const response = await sendOnboardingMessages(nextMessages);
      setMessages([
        ...nextMessages,
        { role: "assistant", content: response.assistant_message },
      ]);
      if (response.is_complete) {
        completeOnboarding();
        router.replace("/");
      }
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Nori could not save that preference.");
    } finally {
      setIsSending(false);
    }
  }

  function enterDashboard() {
    completeOnboarding();
    router.replace("/");
  }

  return (
    <Screen scroll={false}>
      <KeyboardAvoidingView
        behavior={Platform.OS === "ios" ? "padding" : undefined}
        style={styles.container}
      >
        <View style={styles.topCard}>
          <Pill label="Meet Nori" tone="sage" />
          <Text style={styles.title}>Let's make future trips feel less generic.</Text>
          <Text style={styles.subtitle}>
            Tell me what feels good when you travel, and I’ll remember the useful bits.
          </Text>
          <PrimaryButton
            label="Skip chat"
            onPress={enterDashboard}
            tone="secondary"
          />
        </View>

        {errorMessage ? (
          <View style={styles.errorCard}>
            <Text style={styles.errorText}>{errorMessage}</Text>
          </View>
        ) : null}

        <ScrollView
          contentContainerStyle={styles.messages}
          showsVerticalScrollIndicator={false}
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

          {isLoading || isSending ? (
            <View style={[styles.bubble, styles.assistantBubble]}>
              <ActivityIndicator color={colors.primary} />
            </View>
          ) : null}

        </ScrollView>

        <View style={styles.quickReplies}>
          {QUICK_REPLIES.map((reply) => (
            <Pressable key={reply} onPress={() => sendMessage(reply)} style={styles.quickReply}>
              <Text style={styles.quickReplyText}>{reply}</Text>
            </Pressable>
          ))}
        </View>

        <View style={styles.composer}>
          <TextInput
            multiline
            onChangeText={setInput}
            placeholder="Tell Nori about a trip you loved..."
            placeholderTextColor={colors.muted}
            style={styles.input}
            value={input}
          />
          <Pressable
            accessibilityRole="button"
            disabled={!input.trim() || isSending}
            onPress={() => sendMessage()}
            style={({ pressed }) => [
              styles.sendButton,
              pressed && styles.sendButtonPressed,
              (!input.trim() || isSending) && styles.sendButtonDisabled,
            ]}
          >
            <Text style={styles.sendButtonText}>Send</Text>
          </Pressable>
        </View>
      </KeyboardAvoidingView>
    </Screen>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    gap: spacing.md,
  },
  topCard: {
    backgroundColor: colors.surface,
    borderColor: colors.clay,
    borderRadius: radius.lg,
    borderWidth: 1,
    gap: spacing.sm,
    padding: spacing.lg,
    ...shadows.card,
  },
  title: {
    ...typography.heading,
  },
  subtitle: {
    color: colors.muted,
    fontSize: 15,
    fontWeight: "400",
    lineHeight: 21,
  },
  errorCard: {
    backgroundColor: "#F7D4BD",
    borderRadius: radius.md,
    padding: spacing.md,
  },
  errorText: {
    ...typography.caption,
    color: colors.error,
  },
  messages: {
    gap: spacing.md,
    paddingBottom: spacing.md,
  },
  bubble: {
    borderRadius: radius.lg,
    gap: spacing.xs,
    maxWidth: "86%",
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
  quickReplies: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.sm,
  },
  quickReply: {
    backgroundColor: colors.surface,
    borderColor: colors.clay,
    borderRadius: radius.pill,
    borderWidth: 1,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
  },
  quickReplyText: {
    ...typography.caption,
    color: colors.moss,
  },
  composer: {
    alignItems: "flex-end",
    backgroundColor: colors.surface,
    borderColor: colors.clay,
    borderRadius: radius.lg,
    borderWidth: 1,
    flexDirection: "row",
    gap: spacing.sm,
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
