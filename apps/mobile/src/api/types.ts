export type Destination = {
  id: string;
  city: string;
  country: string;
  country_slug: string;
  city_slug: string;
  title: string;
  summary: string;
  description: string;
  vibes: string[];
  best_for: string[];
  avoid_if: string[];
  suggested_duration_days: number[];
  hero_image_url: string | null;
  tags: string[];
};

export type DestinationListResponse = {
  destinations: Destination[];
};

export type ItineraryPlanRunStartResponse = {
  run_id: string;
  status: string;
  poll_url: string;
  progress_events: PlanRunEvent[];
  created_at: string;
  updated_at: string;
};

export type ItineraryPlanRunResponse = {
  run_id: string;
  original_prompt: string;
  model_name: string;
  save: boolean;
  status: "queued" | "running" | "completed" | "failed";
  progress_events: PlanRunEvent[];
  error_message: string | null;
  plan_id: string | null;
  trip_request_id: string | null;
  created_at: string;
  updated_at: string;
};

export type PlanRunEvent = {
  status: string;
  message: string;
};

export type ChatResponse = {
  model: string;
  message: string;
};

export type OnboardingMessage = {
  role: "assistant" | "user";
  content: string;
};

export type OnboardingTurnResponse = {
  assistant_message: string;
  profile_patch: Record<string, unknown>;
  profile: Record<string, unknown>;
  is_complete: boolean;
  next_focus: string;
};

export type UserPreferenceProfile = {
  pace: string | null;
  budget_level: string | null;
  interests: string[];
  food_preferences: string[];
  dislikes: string[];
  notes: string[];
};

export type SavedPlanSummary = {
  plan_id: string;
  trip_request_id: string;
  original_prompt: string;
  title: string;
  destination: string;
  created_at: string;
};

export type SavedPlanListResponse = {
  plans: SavedPlanSummary[];
};

export type MobilePlanSummary = {
  plan_id: string;
  title: string;
  destination: string;
  duration_days: number;
  status: "ready" | "ready_with_warnings";
  highlights: string[];
  days: MobilePlanDay[];
  quality: {
    status: string;
    visible_to_user: boolean;
    issue_count: number;
  };
};

export type MobilePlanDay = {
  day_number: number;
  date: string | null;
  theme: string;
  cards: MobilePlanCard[];
};

export type MobilePlanCard = {
  kind: string;
  time: string;
  title: string;
  description: string;
  area: string | null;
  tags: string[];
  options: MobilePlanOption[];
};

export type MobilePlanOption = {
  name: string;
  category: string;
  area: string | null;
  why_it_fits: string;
  estimated_cost: string | null;
  reservation_recommended: boolean | null;
  tradeoffs: string[];
};
