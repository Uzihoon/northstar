# Northstar Mobile

React Native mobile app for the Northstar travel planner.

## Run Locally

```bash
cd apps/mobile
npm install
cp .env.example .env
npm run ios
```

The app expects the Northstar API at `EXPO_PUBLIC_API_BASE_URL`.

For iOS simulator on the same Mac:

```bash
EXPO_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
```

For a physical phone, use your Mac's LAN IP instead:

```bash
EXPO_PUBLIC_API_BASE_URL=http://192.168.x.x:8000
```

## First Slice

- `Meet Nori`: starts the LLM onboarding chat and saves travel preferences through the API.
- `Explore`: shows supported destinations from the backend catalog.
- `Trip Setup`: sends destination plus trip preferences to the async itinerary job endpoint.
- `Itinerary`: reads the mobile summary endpoint and renders traveler-friendly cards.
