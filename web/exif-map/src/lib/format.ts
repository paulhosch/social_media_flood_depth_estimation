import { imageBaseUrl } from "./config";

export function formatCoord(value: number): string {
  return value.toFixed(6);
}

export function formatDateTime(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

export function imageUrl(fileName: string): string {
  return `${imageBaseUrl}/${encodeURIComponent(fileName)}`;
}
