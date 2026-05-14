import { router, useLocalSearchParams } from "expo-router";
import {
  CalendarDays,
  Clock3,
  Gauge,
  Plane,
  Sparkles,
  Utensils,
  Wallet,
  type LucideIcon,
} from "lucide-react-native";
import { useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  ImageBackground,
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
  type KeyboardTypeOptions,
} from "react-native";
import { Calendar, type DateData } from "react-native-calendars";

import { getDestination, getPlanRun, startPlanRun } from "../../src/api/client";
import type { Destination, ItineraryPlanRunResponse } from "../../src/api/types";
import { getDestinationImageSource } from "../../src/assets/destinationImages";
import { Pill } from "../../src/components/Pill";
import { PrimaryButton } from "../../src/components/PrimaryButton";
import { Screen } from "../../src/components/Screen";
import { colors, radius, shadows, spacing, typography } from "../../src/theme/tokens";

const BUDGET_OPTIONS = [
  { label: "Budget", value: "budget" },
  { label: "Mid-range", value: "midrange" },
  { label: "Luxury", value: "luxury" },
];

const PACE_OPTIONS = [
  { label: "Slow", value: "relaxed" },
  { label: "Balanced", value: "balanced" },
  { label: "Full", value: "fast" },
];

const INTEREST_OPTIONS = [
  "quiet neighborhoods",
  "cafes",
  "bookstores",
  "temples",
  "markets",
  "walkable",
];

const FOOD_OPTIONS = [
  "vegetarian",
  "coffee",
  "vegan",
  "local cuisine",
];

const CALENDAR_RANGE_COLOR = "#F58A46";
const CALENDAR_RANGE_MIDDLE_COLOR = "#FCE4D2";

type SectionHeaderProps = {
  description: string;
  icon: LucideIcon;
  title: string;
};

type DatePickerFieldProps = {
  label: string;
  onPress: () => void;
  placeholder: string;
  value: string;
};

type TextFieldProps = {
  helper?: string;
  icon: LucideIcon;
  keyboardType?: KeyboardTypeOptions;
  label: string;
  multiline?: boolean;
  onChangeText: (value: string) => void;
  placeholder: string;
  value: string;
};

type SelectableChipProps = {
  isSelected: boolean;
  label: string;
  onPress: () => void;
};

function firstParam(value: string | string[] | undefined): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}

function toggleValue(values: string[], value: string): string[] {
  return values.includes(value)
    ? values.filter((item) => item !== value)
    : [...values, value];
}

export default function DestinationDetailScreen() {
  const params = useLocalSearchParams();
  const destinationId = firstParam(params.id);

  const [destination, setDestination] = useState<Destination | null>(null);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [startPlace, setStartPlace] = useState("");
  const [arrivalTime, setArrivalTime] = useState("");
  const [budgetLevel, setBudgetLevel] = useState("midrange");
  const [pace, setPace] = useState("relaxed");
  const [interests, setInterests] = useState<string[]>(["cafes", "quiet neighborhoods"]);
  const [foodPreferences, setFoodPreferences] = useState<string[]>(["vegetarian", "coffee"]);
  const [note, setNote] = useState("");
  const [run, setRun] = useState<ItineraryPlanRunResponse | null>(null);
  const [runId, setRunId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isStarting, setIsStarting] = useState(false);
  const [isCalendarVisible, setIsCalendarVisible] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;

    async function loadDestination() {
      if (!destinationId) {
        setErrorMessage("Destination id is missing.");
        setIsLoading(false);
        return;
      }

      try {
        const data = await getDestination(destinationId);
        if (isMounted) {
          setDestination(data);
          setInterests(data.vibes.slice(0, 2));
          setErrorMessage(null);
        }
      } catch (error) {
        if (isMounted) {
          setErrorMessage(error instanceof Error ? error.message : "Could not load destination.");
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    loadDestination();

    return () => {
      isMounted = false;
    };
  }, [destinationId]);

  useEffect(() => {
    if (!runId) {
      return undefined;
    }

    let isMounted = true;

    const interval = setInterval(async () => {
      try {
        const nextRun = await getPlanRun(runId);

        if (!isMounted) {
          return;
        }

        setRun(nextRun);

        if (nextRun.status === "completed" && nextRun.plan_id) {
          setRunId(null);
          router.replace({
            pathname: "/plans/[id]",
            params: { id: nextRun.plan_id },
          });
        }

        if (nextRun.status === "failed") {
          setRunId(null);
          setErrorMessage(nextRun.error_message ?? "Planning failed.");
        }
      } catch (error) {
        if (isMounted) {
          setRunId(null);
          setErrorMessage(error instanceof Error ? error.message : "Could not poll planning run.");
        }
      }
    }, 2000);

    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [runId]);

  const normalizedStartDate = useMemo(() => normalizeIsoDate(startDate), [startDate]);
  const normalizedEndDate = useMemo(() => normalizeIsoDate(endDate), [endDate]);
  const suggestedDurationDays = destination?.suggested_duration_days[0] ?? 2;
  const derivedDurationDays = getTripDurationDays(startDate, endDate);
  const durationDays = derivedDurationDays ?? suggestedDurationDays;
  const durationLabel = formatDurationLabel(durationDays, derivedDurationDays ? "from your dates" : "suggested");
  const markedDates = useMemo(() => buildMarkedDates(startDate, endDate), [endDate, startDate]);
  const initialCalendarDate = startDate || getTodayIsoDate();
  const canApplyDateRange = !startDate || Boolean(endDate);

  const additionalInfo = useMemo(() => {
    const parts = [`Duration: ${durationDays} days.`];

    if (normalizedStartDate && normalizedEndDate) {
      parts.push(`Travel dates: ${normalizedStartDate} to ${normalizedEndDate}.`);
    }

    if (startPlace.trim()) {
      parts.push(`Starting from: ${startPlace.trim()}.`);
    }

    if (arrivalTime.trim()) {
      parts.push(`Arrival or preferred start timing: ${arrivalTime.trim()}.`);
    }

    if (note.trim()) {
      parts.push(`Traveler note: ${note.trim()}`);
    }

    return parts.join("\n");
  }, [arrivalTime, durationDays, normalizedEndDate, normalizedStartDate, note, startPlace]);

  async function startPlanning() {
    if (!destinationId || isStarting || runId) {
      return;
    }

    const dateError = validateTripDates(startDate, endDate);
    if (dateError) {
      setErrorMessage(dateError);
      return;
    }

    setIsStarting(true);
    setErrorMessage(null);

    try {
      const createdRun = await startPlanRun({
        destinationId,
        additionalInfo,
        startDate: normalizedStartDate,
        endDate: normalizedEndDate,
        budgetLevel,
        pace,
        interests,
        foodPreferences,
      });

      setRun({
        run_id: createdRun.run_id,
        original_prompt: "",
        model_name: "",
        save: true,
        status: "queued",
        progress_events: createdRun.progress_events,
        error_message: null,
        plan_id: null,
        trip_request_id: null,
        created_at: createdRun.created_at,
        updated_at: createdRun.updated_at,
      });
      setRunId(createdRun.run_id);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Could not start planning.");
    } finally {
      setIsStarting(false);
    }
  }

  function openCalendar() {
    setErrorMessage(null);
    setIsCalendarVisible(true);
  }

  function selectCalendarDay(day: DateData) {
    const selectedDate = day.dateString;

    if (!startDate || endDate) {
      setStartDate(selectedDate);
      setEndDate("");
      return;
    }

    if (compareIsoDates(selectedDate, startDate) < 0) {
      setStartDate(selectedDate);
      setEndDate("");
      return;
    }

    setEndDate(selectedDate);
  }

  function clearDateRange() {
    setStartDate("");
    setEndDate("");
  }

  if (isLoading) {
    return (
      <Screen>
        <View style={styles.stateCard}>
          <ActivityIndicator color={colors.primary} />
          <Text style={styles.stateText}>Loading destination...</Text>
        </View>
      </Screen>
    );
  }

  if (!destination) {
    return (
      <Screen>
        <View style={styles.stateCard}>
          <Text style={styles.stateTitle}>Destination unavailable</Text>
          <Text style={styles.stateText}>{errorMessage}</Text>
        </View>
      </Screen>
    );
  }

  const destinationImageSource = getDestinationImageSource(destination);

  return (
    <Screen edges={["left", "right"]} padded={false} scroll={false}>
      <ScrollView
        contentContainerStyle={styles.content}
        showsVerticalScrollIndicator={false}
        style={styles.scroll}
      >
        <View style={styles.destinationCard}>
          <View style={styles.destinationArtwork}>
            {destinationImageSource ? (
              <ImageBackground
                imageStyle={styles.destinationImage}
                source={destinationImageSource}
                style={styles.destinationImageBackground}
              >
                <View style={styles.destinationImageOverlay} />
              </ImageBackground>
            ) : (
              <>
                <View style={styles.destinationBlobOrange} />
                <View style={styles.destinationBlobSage} />
              </>
            )}
          </View>

          <View style={styles.destinationCopy}>
            <Text style={styles.title}>{destination.title}</Text>
            <Text style={styles.description}>{destination.description}</Text>
            <View style={styles.pillGrid}>
              {destination.vibes.slice(0, 4).map((vibe) => (
                <Pill key={vibe} label={vibe} tone="sage" />
              ))}
            </View>
          </View>
        </View>

        <View style={styles.card}>
          <SectionHeader
            description="Dates first. The rest helps me time the days properly."
            icon={CalendarDays}
            title="Trip details"
          />

          <View style={styles.dateGrid}>
            <DatePickerField
              label="From"
              onPress={openCalendar}
              placeholder="Choose start"
              value={startDate}
            />
            <DatePickerField
              label="To"
              onPress={openCalendar}
              placeholder="Choose end"
              value={endDate}
            />
          </View>

          <View style={styles.durationBadge}>
            <CalendarDays color={colors.primaryPressed} size={16} strokeWidth={2.4} />
            <Text style={styles.durationText}>{durationLabel}</Text>
          </View>

          <TextField
            helper="Optional, but useful for travel-time assumptions."
            icon={Plane}
            label="Starting from"
            onChangeText={setStartPlace}
            placeholder="Home, airport, station..."
            value={startPlace}
          />

          <TextField
            helper="Optional. Example: land at 10 AM, start after lunch."
            icon={Clock3}
            label="Arrival or start time"
            onChangeText={setArrivalTime}
            placeholder="Land 10 AM, start after lunch..."
            value={arrivalTime}
          />
        </View>

        <View style={styles.card}>
          <SectionHeader
            description="This sets the default mood unless you nudge me."
            icon={Gauge}
            title="Travel style"
          />

          <View style={styles.field}>
            <View style={styles.labelRow}>
              <Wallet color={colors.moss} size={15} strokeWidth={2.4} />
              <Text style={styles.label}>Budget</Text>
            </View>
            <View style={styles.optionRow}>
              {BUDGET_OPTIONS.map((option) => (
                <SelectableChip
                  isSelected={budgetLevel === option.value}
                  key={option.value}
                  label={option.label}
                  onPress={() => setBudgetLevel(option.value)}
                />
              ))}
            </View>
          </View>

          <View style={styles.field}>
            <View style={styles.labelRow}>
              <Gauge color={colors.moss} size={15} strokeWidth={2.4} />
              <Text style={styles.label}>Pace</Text>
            </View>
            <View style={styles.optionRow}>
              {PACE_OPTIONS.map((option) => (
                <SelectableChip
                  isSelected={pace === option.value}
                  key={option.value}
                  label={option.label}
                  onPress={() => setPace(option.value)}
                />
              ))}
            </View>
          </View>
        </View>

        <View style={styles.card}>
          <SectionHeader
            description="Pick a few signals. One note is enough if something matters."
            icon={Sparkles}
            title="What should I lean into?"
          />

          <View style={styles.field}>
            <View style={styles.labelRow}>
              <Sparkles color={colors.moss} size={15} strokeWidth={2.4} />
              <Text style={styles.label}>Themes</Text>
            </View>
            <View style={styles.optionRow}>
              {INTEREST_OPTIONS.map((interest) => (
                <SelectableChip
                  isSelected={interests.includes(interest)}
                  key={interest}
                  label={interest}
                  onPress={() => setInterests((current) => toggleValue(current, interest))}
                />
              ))}
            </View>
          </View>

          <View style={styles.field}>
            <View style={styles.labelRow}>
              <Utensils color={colors.moss} size={15} strokeWidth={2.4} />
              <Text style={styles.label}>Food</Text>
            </View>
            <View style={styles.optionRow}>
              {FOOD_OPTIONS.map((food) => (
                <SelectableChip
                  isSelected={foodPreferences.includes(food)}
                  key={food}
                  label={food}
                  onPress={() => setFoodPreferences((current) => toggleValue(current, food))}
                />
              ))}
            </View>
          </View>

          <TextField
            icon={Sparkles}
            label="Nori note"
            multiline
            onChangeText={setNote}
            placeholder="Keep mornings gentle. Avoid crowded dinner spots."
            value={note}
          />
        </View>

        {errorMessage ? (
          <View style={styles.errorCard}>
            <Text style={styles.errorText}>{errorMessage}</Text>
          </View>
        ) : null}

        <View style={styles.ctaCard}>
          <Text style={styles.ctaTitle}>Ready when you are.</Text>
          <Text style={styles.ctaText}>I will turn this into a day-by-day plan with timing, movement, and options.</Text>
          <PrimaryButton
            disabled={isStarting || Boolean(runId)}
            label={runId ? "Nori is planning..." : "Plan this trip"}
            onPress={startPlanning}
          />
        </View>

        {run ? (
          <View style={styles.runCard}>
            <Text style={styles.sectionTitle}>Nori is planning</Text>
            {run.progress_events.map((event, index) => (
              <View key={`${event.status}-${index}`} style={styles.runEvent}>
                <View style={styles.runDot} />
                <Text style={styles.runText}>{event.message}</Text>
              </View>
            ))}
            {runId ? <ActivityIndicator color={colors.primary} /> : null}
          </View>
        ) : null}
      </ScrollView>

      <Modal
        animationType="fade"
        onRequestClose={() => setIsCalendarVisible(false)}
        transparent
        visible={isCalendarVisible}
      >
        <View style={styles.modalRoot}>
          <Pressable
            accessibilityLabel="Close date picker"
            accessibilityRole="button"
            onPress={() => setIsCalendarVisible(false)}
            style={styles.modalBackdrop}
          />
          <View style={styles.calendarSheet}>
            <View style={styles.calendarHeader}>
              <View>
                <Text style={styles.calendarTitle}>Choose trip dates</Text>
                <Text style={styles.calendarSubtitle}>
                  {startDate && !endDate
                    ? "Now tap the day you come home."
                    : "Tap a start date, then an end date."}
                </Text>
              </View>
              <Pressable
                accessibilityRole="button"
                onPress={clearDateRange}
                style={styles.clearDatesButton}
              >
                <Text style={styles.clearDatesText}>Clear</Text>
              </Pressable>
            </View>

            <Calendar
              current={initialCalendarDate}
              firstDay={0}
              markedDates={markedDates}
              markingType="period"
              minDate={getTodayIsoDate()}
              onDayPress={selectCalendarDay}
              style={styles.calendar}
              theme={calendarTheme}
            />

            <View style={styles.calendarFooter}>
              <Text style={styles.calendarRangeText}>
                {formatDateRangeSummary(startDate, endDate)}
              </Text>
              <PrimaryButton
                disabled={!canApplyDateRange}
                label="Done"
                onPress={() => setIsCalendarVisible(false)}
              />
            </View>
          </View>
        </View>
      </Modal>
    </Screen>
  );
}

function DatePickerField({ label, onPress, placeholder, value }: DatePickerFieldProps) {
  return (
    <View style={styles.inputGroup}>
      <View style={styles.labelRow}>
        <CalendarDays color={colors.moss} size={15} strokeWidth={2.4} />
        <Text style={styles.label}>{label}</Text>
      </View>
      <Pressable accessibilityRole="button" onPress={onPress} style={styles.datePickerField}>
        <Text style={[styles.datePickerValue, !value && styles.datePickerPlaceholder]}>
          {value ? formatDisplayDate(value) : placeholder}
        </Text>
        <CalendarDays color={colors.primaryPressed} size={17} strokeWidth={2.4} />
      </Pressable>
    </View>
  );
}

function SectionHeader({ description, icon: Icon, title }: SectionHeaderProps) {
  return (
    <View style={styles.sectionHeader}>
      <View style={styles.sectionIcon}>
        <Icon color={colors.moss} size={17} strokeWidth={2.4} />
      </View>
      <View style={styles.sectionCopy}>
        <Text style={styles.sectionTitle}>{title}</Text>
        <Text style={styles.sectionDescription}>{description}</Text>
      </View>
    </View>
  );
}

function TextField({
  helper,
  icon: Icon,
  keyboardType,
  label,
  multiline = false,
  onChangeText,
  placeholder,
  value,
}: TextFieldProps) {
  return (
    <View style={styles.inputGroup}>
      <View style={styles.labelRow}>
        <Icon color={colors.moss} size={15} strokeWidth={2.4} />
        <Text style={styles.label}>{label}</Text>
      </View>
      <TextInput
        autoCapitalize="none"
        keyboardType={keyboardType}
        multiline={multiline}
        onChangeText={onChangeText}
        placeholder={placeholder}
        placeholderTextColor={colors.muted}
        style={[styles.input, multiline && styles.noteInput]}
        textAlignVertical={multiline ? "top" : "center"}
        value={value}
      />
      {helper ? <Text style={styles.helperText}>{helper}</Text> : null}
    </View>
  );
}

function SelectableChip({ isSelected, label, onPress }: SelectableChipProps) {
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={{ selected: isSelected }}
      onPress={onPress}
      style={[styles.selectableChip, isSelected && styles.selectedChip]}
    >
      <Text style={[styles.selectableChipText, isSelected && styles.selectedChipText]}>
        {label}
      </Text>
    </Pressable>
  );
}

function normalizeIsoDate(value: string): string | undefined {
  const trimmed = value.trim();
  if (!trimmed || !/^\d{4}-\d{2}-\d{2}$/.test(trimmed)) {
    return undefined;
  }

  const [year, month, day] = trimmed.split("-").map(Number);
  const date = new Date(Date.UTC(year, month - 1, day));

  if (
    date.getUTCFullYear() !== year
    || date.getUTCMonth() !== month - 1
    || date.getUTCDate() !== day
  ) {
    return undefined;
  }

  return trimmed;
}

function getUtcDateValue(value: string): number | undefined {
  const normalized = normalizeIsoDate(value);
  if (!normalized) {
    return undefined;
  }

  const [year, month, day] = normalized.split("-").map(Number);
  return Date.UTC(year, month - 1, day);
}

function getTripDurationDays(start: string, end: string): number | undefined {
  const startValue = getUtcDateValue(start);
  const endValue = getUtcDateValue(end);

  if (startValue === undefined || endValue === undefined || endValue < startValue) {
    return undefined;
  }

  return Math.round((endValue - startValue) / 86_400_000) + 1;
}

function compareIsoDates(left: string, right: string) {
  const leftValue = getUtcDateValue(left);
  const rightValue = getUtcDateValue(right);

  if (leftValue === undefined || rightValue === undefined) {
    return 0;
  }

  return leftValue - rightValue;
}

function getTodayIsoDate() {
  const today = new Date();

  return formatIsoDateParts(today.getFullYear(), today.getMonth() + 1, today.getDate());
}

function addDays(value: string, days: number) {
  const dateValue = getUtcDateValue(value);

  if (dateValue === undefined) {
    return "";
  }

  return new Date(dateValue + days * 86_400_000).toISOString().slice(0, 10);
}

function formatIsoDateParts(year: number, month: number, day: number) {
  return [
    year.toString().padStart(4, "0"),
    month.toString().padStart(2, "0"),
    day.toString().padStart(2, "0"),
  ].join("-");
}

function buildMarkedDates(start: string, end: string) {
  const normalizedStart = normalizeIsoDate(start);
  const normalizedEnd = normalizeIsoDate(end);

  if (!normalizedStart) {
    return {};
  }

  if (!normalizedEnd) {
    return {
      [normalizedStart]: {
        color: CALENDAR_RANGE_COLOR,
        endingDay: true,
        startingDay: true,
        textColor: colors.surface,
      },
    };
  }

  const dateCount = getTripDurationDays(normalizedStart, normalizedEnd);

  if (!dateCount) {
    return {};
  }

  const markedDates: Record<string, {
    color: string;
    endingDay?: boolean;
    startingDay?: boolean;
    textColor: string;
  }> = {};

  for (let index = 0; index < dateCount; index += 1) {
    const date = addDays(normalizedStart, index);
    markedDates[date] = {
      color: index === 0 || index === dateCount - 1
        ? CALENDAR_RANGE_COLOR
        : CALENDAR_RANGE_MIDDLE_COLOR,
      endingDay: index === dateCount - 1,
      startingDay: index === 0,
      textColor: index === 0 || index === dateCount - 1
        ? colors.surface
        : colors.ink,
    };
  }

  return markedDates;
}

function formatDisplayDate(value: string) {
  const normalized = normalizeIsoDate(value);

  if (!normalized) {
    return value;
  }

  const dateValue = getUtcDateValue(normalized);

  if (dateValue === undefined) {
    return value;
  }

  return new Intl.DateTimeFormat("en-US", {
    day: "numeric",
    month: "short",
  }).format(new Date(dateValue));
}

function formatDateRangeSummary(start: string, end: string) {
  if (!start && !end) {
    return "No dates selected yet.";
  }

  if (start && !end) {
    return `Starts ${formatDisplayDate(start)}. Choose an end date.`;
  }

  return `${formatDisplayDate(start)} - ${formatDisplayDate(end)}`;
}

function validateTripDates(start: string, end: string): string | null {
  const hasStart = start.trim().length > 0;
  const hasEnd = end.trim().length > 0;

  if (hasStart !== hasEnd) {
    return "Add both dates, or leave the dates blank for now.";
  }

  if (!hasStart && !hasEnd) {
    return null;
  }

  if (!normalizeIsoDate(start) || !normalizeIsoDate(end)) {
    return "Use YYYY-MM-DD for travel dates.";
  }

  if (getTripDurationDays(start, end) === undefined) {
    return "End date must be after the start date.";
  }

  return null;
}

function formatDurationLabel(days: number, source: "from your dates" | "suggested") {
  const dayLabel = days === 1 ? "day" : "days";
  return `${days} ${dayLabel} ${source}`;
}

const calendarTheme = {
  arrowColor: colors.primaryPressed,
  calendarBackground: colors.surface,
  dayTextColor: colors.ink,
  monthTextColor: colors.ink,
  selectedDayBackgroundColor: CALENDAR_RANGE_COLOR,
  selectedDayTextColor: colors.surface,
  textDayFontSize: 15,
  textDayFontWeight: "600" as const,
  textDisabledColor: "#D7CFC2",
  textMonthFontSize: 17,
  textMonthFontWeight: "900" as const,
  textSectionTitleColor: colors.muted,
  todayTextColor: colors.primaryPressed,
};

const styles = StyleSheet.create({
  content: {
    gap: spacing.lg,
    paddingBottom: spacing.xxl,
    paddingHorizontal: spacing.xl,
    paddingTop: spacing.xl,
  },
  scroll: {
    flex: 1,
  },
  destinationCard: {
    backgroundColor: colors.surface,
    borderColor: "rgba(216, 195, 165, 0.76)",
    borderRadius: radius.lg,
    borderWidth: StyleSheet.hairlineWidth,
    overflow: "hidden",
    ...shadows.card,
  },
  destinationArtwork: {
    backgroundColor: "#E9D8BF",
    height: 148,
    overflow: "hidden",
    position: "relative",
  },
  destinationImageBackground: {
    ...StyleSheet.absoluteFillObject,
  },
  destinationImage: {
    borderTopLeftRadius: radius.lg,
    borderTopRightRadius: radius.lg,
  },
  destinationImageOverlay: {
    backgroundColor: "rgba(39, 34, 29, 0.18)",
    flex: 1,
  },
  destinationBlobOrange: {
    backgroundColor: "#F09A57",
    borderRadius: 100,
    height: 148,
    left: -38,
    opacity: 0.72,
    position: "absolute",
    top: -58,
    width: 148,
  },
  destinationBlobSage: {
    backgroundColor: "#789B6F",
    borderRadius: 120,
    bottom: -88,
    height: 180,
    opacity: 0.78,
    position: "absolute",
    right: -46,
    width: 180,
  },
  destinationCopy: {
    gap: spacing.sm,
    padding: spacing.lg,
  },
  title: {
    ...typography.heading,
  },
  description: {
    color: colors.muted,
    fontSize: 15,
    fontWeight: "400",
    lineHeight: 21,
  },
  pillGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.sm,
  },
  card: {
    backgroundColor: colors.surface,
    borderColor: colors.clay,
    borderRadius: radius.lg,
    borderWidth: StyleSheet.hairlineWidth,
    gap: spacing.lg,
    padding: spacing.lg,
    ...shadows.card,
  },
  sectionHeader: {
    alignItems: "flex-start",
    flexDirection: "row",
    gap: spacing.md,
  },
  sectionIcon: {
    alignItems: "center",
    backgroundColor: "#E1E9DA",
    borderRadius: radius.pill,
    height: 36,
    justifyContent: "center",
    width: 36,
  },
  sectionCopy: {
    flex: 1,
    gap: spacing.xs,
  },
  sectionTitle: {
    ...typography.subheading,
  },
  sectionDescription: {
    color: colors.muted,
    fontSize: 14,
    fontWeight: "400",
    lineHeight: 20,
  },
  dateGrid: {
    flexDirection: "row",
    gap: spacing.md,
  },
  durationBadge: {
    alignItems: "center",
    alignSelf: "flex-start",
    backgroundColor: "#F7D4BD",
    borderRadius: radius.pill,
    flexDirection: "row",
    gap: spacing.sm,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
  },
  durationText: {
    ...typography.caption,
    color: colors.primaryPressed,
    fontWeight: "800",
  },
  field: {
    gap: spacing.sm,
  },
  inputGroup: {
    flex: 1,
    gap: spacing.sm,
  },
  labelRow: {
    alignItems: "center",
    flexDirection: "row",
    gap: spacing.xs,
  },
  label: {
    ...typography.caption,
    color: colors.moss,
    fontWeight: "800",
    textTransform: "uppercase",
  },
  input: {
    backgroundColor: colors.background,
    borderColor: "rgba(216, 195, 165, 0.82)",
    borderRadius: radius.md,
    borderWidth: StyleSheet.hairlineWidth,
    color: colors.ink,
    fontSize: 16,
    fontWeight: "500",
    minHeight: 52,
    paddingHorizontal: spacing.lg,
  },
  datePickerField: {
    alignItems: "center",
    backgroundColor: colors.background,
    borderColor: "rgba(216, 195, 165, 0.82)",
    borderRadius: radius.md,
    borderWidth: StyleSheet.hairlineWidth,
    flexDirection: "row",
    gap: spacing.sm,
    justifyContent: "space-between",
    minHeight: 52,
    paddingHorizontal: spacing.lg,
  },
  datePickerValue: {
    color: colors.ink,
    flex: 1,
    fontSize: 16,
    fontWeight: "700",
  },
  datePickerPlaceholder: {
    color: colors.muted,
    fontWeight: "500",
  },
  helperText: {
    ...typography.caption,
    color: colors.muted,
  },
  noteInput: {
    minHeight: 112,
    paddingTop: spacing.md,
  },
  optionRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.sm,
  },
  selectableChip: {
    backgroundColor: colors.background,
    borderColor: colors.clay,
    borderRadius: radius.pill,
    borderWidth: StyleSheet.hairlineWidth,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
  },
  selectedChip: {
    backgroundColor: "#F7D4BD",
    borderColor: colors.primary,
  },
  selectableChipText: {
    ...typography.caption,
    color: colors.muted,
  },
  selectedChipText: {
    color: colors.primaryPressed,
    fontWeight: "800",
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
  ctaCard: {
    backgroundColor: colors.moss,
    borderRadius: radius.lg,
    gap: spacing.md,
    padding: spacing.lg,
    ...shadows.card,
  },
  ctaTitle: {
    ...typography.subheading,
    color: colors.surface,
  },
  ctaText: {
    color: "#E9F0E2",
    fontSize: 14,
    fontWeight: "400",
    lineHeight: 20,
  },
  runCard: {
    backgroundColor: colors.surface,
    borderColor: colors.clay,
    borderRadius: radius.lg,
    borderWidth: StyleSheet.hairlineWidth,
    gap: spacing.md,
    padding: spacing.lg,
  },
  runEvent: {
    alignItems: "center",
    flexDirection: "row",
    gap: spacing.sm,
  },
  runDot: {
    backgroundColor: colors.primary,
    borderRadius: radius.pill,
    height: 10,
    width: 10,
  },
  runText: {
    ...typography.body,
    color: colors.muted,
    flex: 1,
  },
  stateCard: {
    alignItems: "center",
    backgroundColor: colors.surface,
    borderColor: colors.clay,
    borderRadius: radius.lg,
    borderWidth: StyleSheet.hairlineWidth,
    gap: spacing.md,
    padding: spacing.xl,
  },
  stateTitle: {
    ...typography.heading,
  },
  stateText: {
    ...typography.body,
    color: colors.muted,
    textAlign: "center",
  },
  modalRoot: {
    flex: 1,
    justifyContent: "flex-end",
  },
  modalBackdrop: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: "rgba(39, 34, 29, 0.36)",
  },
  calendarSheet: {
    backgroundColor: colors.surface,
    borderTopLeftRadius: radius.lg,
    borderTopRightRadius: radius.lg,
    gap: spacing.lg,
    padding: spacing.xl,
    paddingBottom: spacing.xxl,
  },
  calendarHeader: {
    alignItems: "flex-start",
    flexDirection: "row",
    gap: spacing.md,
    justifyContent: "space-between",
  },
  calendarTitle: {
    ...typography.subheading,
  },
  calendarSubtitle: {
    color: colors.muted,
    fontSize: 14,
    fontWeight: "400",
    lineHeight: 20,
    marginTop: spacing.xs,
  },
  clearDatesButton: {
    backgroundColor: colors.background,
    borderColor: colors.clay,
    borderRadius: radius.pill,
    borderWidth: StyleSheet.hairlineWidth,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
  },
  clearDatesText: {
    ...typography.caption,
    color: colors.primaryPressed,
    fontWeight: "800",
  },
  calendar: {
    borderColor: colors.clay,
    borderRadius: radius.lg,
    borderWidth: StyleSheet.hairlineWidth,
    overflow: "hidden",
  },
  calendarFooter: {
    gap: spacing.md,
  },
  calendarRangeText: {
    ...typography.body,
    color: colors.moss,
    fontWeight: "800",
    textAlign: "center",
  },
});
