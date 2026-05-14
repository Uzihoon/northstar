import type { ImageSourcePropType } from "react-native";

type DestinationImageInput =
  | string
  | {
    city?: string | null;
    country?: string | null;
    destination?: string | null;
  }
  | null
  | undefined;

const kyotoImage = require("../../assets/destinations/kyoto.png") as ImageSourcePropType;
const seoulImage = require("../../assets/destinations/seoul.png") as ImageSourcePropType;

export function getDestinationImageSource(input: DestinationImageInput): ImageSourcePropType | null {
  const label = getDestinationLabel(input);

  if (label.includes("kyoto")) {
    return kyotoImage;
  }

  if (label.includes("seoul")) {
    return seoulImage;
  }

  return null;
}

function getDestinationLabel(input: DestinationImageInput) {
  if (!input) {
    return "";
  }

  if (typeof input === "string") {
    return input.toLowerCase();
  }

  return [
    input.city,
    input.country,
    input.destination,
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();
}
