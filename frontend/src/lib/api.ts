export type ThumbnailStatus = "pending" | "generating" | "uploaded" | "failed";
export type JobStatus = "pending" | "processing" | "completed" | "failed";
export type ThumbnailFormat = "youtube" | "shorts" | "square";

export type ThumbnailVariants = Partial<Record<ThumbnailFormat, string>>;

export interface Thumbnail {
  id: string;
  style_name: string;
  status: ThumbnailStatus;
  imagekit_url: string | null;
  error_message: string | null;
  variants: ThumbnailVariants | null;
}

export interface Job {
  id: string;
  prompt: string;
  num_thumbnails: number;
  headshot_url: string;
  status: JobStatus;
  thumbnails: Thumbnail[];
}

interface CreateJobInput {
  prompt: string;
  numThumbnails: number;
  headshotUrl: string;
}

const API_URL = (
  import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000"
).replace(/\/$/, "");

function getErrorMessage(payload: unknown, fallback: string): string {
  if (!payload || typeof payload !== "object") return fallback;
  const detail = (payload as { detail?: unknown }).detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const first = detail[0] as { msg?: unknown } | undefined;
    if (typeof first?.msg === "string") return first.msg;
  }
  return fallback;
}

async function parseResponse<T>(response: Response, fallback: string): Promise<T> {
  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(getErrorMessage(payload, fallback));
  }
  return payload as T;
}

export async function uploadHeadshot(file: File): Promise<string> {
  const formData = new FormData();
  formData.append("file", file);
  const response = await fetch(`${API_URL}/api/upload-headshot`, {
    method: "POST",
    body: formData,
  });
  const payload = await parseResponse<{ url: string }>(
    response,
    "The portrait could not be uploaded.",
  );
  return payload.url;
}

export async function createJob(input: CreateJobInput): Promise<string> {
  const response = await fetch(`${API_URL}/api/job`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      prompt: input.prompt,
      num_thumbnails: input.numThumbnails,
      headshot_url: input.headshotUrl,
    }),
  });
  const payload = await parseResponse<{ job_id: string }>(
    response,
    "The project could not be started.",
  );
  return payload.job_id;
}

export async function getJob(jobId: string): Promise<Job> {
  const response = await fetch(`${API_URL}/api/job/${encodeURIComponent(jobId)}`, {
    cache: "no-store",
  });
  return parseResponse<Job>(response, "The project could not be loaded.");
}

export function thumbnailUrl(
  thumbnail: Thumbnail,
  format: ThumbnailFormat,
): string | null {
  return thumbnail.variants?.[format] ?? thumbnail.imagekit_url;
}

export function serverApiUrl(): string {
  return API_URL;
}
