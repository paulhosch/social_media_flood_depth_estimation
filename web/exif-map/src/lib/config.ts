const DEFAULT_MAP_INDEX_URL = "/data/map-index.json";
const DEFAULT_IMAGE_BASE_URL = "/dataset/images";

function trimTrailingSlash(value: string): string {
  return value.replace(/\/+$/, "");
}

function readEnvValue(value: string | undefined, fallback: string): string {
  if (!value) {
    return fallback;
  }
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : fallback;
}

export const mapIndexUrl = readEnvValue(
  import.meta.env.VITE_MAP_INDEX_URL,
  DEFAULT_MAP_INDEX_URL,
);

export const imageBaseUrl = trimTrailingSlash(
  readEnvValue(import.meta.env.VITE_IMAGE_BASE_URL, DEFAULT_IMAGE_BASE_URL),
);
