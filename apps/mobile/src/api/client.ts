import type {
  ChatResponse,
  Destination,
  DestinationListResponse,
  ItineraryPlanRunResponse,
  ItineraryPlanRunStartResponse,
  MobilePlanSummary,
  OnboardingMessage,
  OnboardingTurnResponse,
  SavedPlanListResponse,
  SavedPlanSummary,
  UserPreferenceProfile,
} from "./types";

const API_BASE_URL = process.env.EXPO_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
    ...options,
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Northstar API request failed: ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export async function listDestinations(): Promise<Destination[]> {
  const data = await request<DestinationListResponse>("/destinations");
  return data.destinations;
}

export async function getDestination(destinationId: string): Promise<Destination> {
  return request<Destination>(`/destinations/${destinationId}`);
}

export async function startPlanRun(input: {
  destinationId: string;
  additionalInfo?: string;
  startDate?: string;
  endDate?: string;
  budgetLevel?: string;
  pace?: string;
  interests?: string[];
  foodPreferences?: string[];
}): Promise<ItineraryPlanRunStartResponse> {
  return request<ItineraryPlanRunStartResponse>("/itinerary-plan-runs", {
    method: "POST",
    body: JSON.stringify({
      destination_ids: [input.destinationId],
      additional_info: input.additionalInfo,
      start_date: input.startDate,
      end_date: input.endDate,
      budget_level: input.budgetLevel,
      pace: input.pace,
      interests: input.interests ?? [],
      food_preferences: input.foodPreferences ?? [],
      save: true,
    }),
  });
}

export async function getPlanRun(runId: string): Promise<ItineraryPlanRunResponse> {
  return request<ItineraryPlanRunResponse>(`/itinerary-plan-runs/${runId}`);
}

export async function getPlanSummary(planId: string): Promise<MobilePlanSummary> {
  return request<MobilePlanSummary>(`/itinerary-plans/${planId}/summary`);
}

export async function listSavedPlans(): Promise<SavedPlanSummary[]> {
  const data = await request<SavedPlanListResponse>("/itinerary-plans");
  return data.plans;
}

export async function sendOnboardingMessages(
  messages: OnboardingMessage[],
): Promise<OnboardingTurnResponse> {
  return request<OnboardingTurnResponse>("/onboarding/messages", {
    method: "POST",
    body: JSON.stringify({ messages }),
  });
}

export async function getPreferenceProfile(): Promise<UserPreferenceProfile> {
  return request<UserPreferenceProfile>("/profile");
}

export async function sendNoriChat(prompt: string): Promise<ChatResponse> {
  return request<ChatResponse>("/chat", {
    method: "POST",
    body: JSON.stringify({ prompt }),
  });
}
