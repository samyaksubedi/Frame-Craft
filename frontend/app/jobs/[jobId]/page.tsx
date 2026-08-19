import type { Metadata } from "next";
import { JobStudio } from "../../components/JobStudio";
import { serverApiUrl, type Job } from "../../lib/api";

interface JobPageProps {
  params: Promise<{ jobId: string }>;
}

async function loadJob(jobId: string): Promise<Job | null> {
  try {
    const response = await fetch(`${serverApiUrl()}/api/job/${encodeURIComponent(jobId)}`, { cache: "no-store" });
    if (!response.ok) return null;
    return (await response.json()) as Job;
  } catch {
    return null;
  }
}

export async function generateMetadata({ params }: JobPageProps): Promise<Metadata> {
  const { jobId } = await params;
  const job = await loadJob(jobId);
  if (!job) return { title: "Project unavailable — Framecraft" };

  const description = job.prompt.length > 155 ? `${job.prompt.slice(0, 152)}…` : job.prompt;
  const socialImage = job.thumbnails.find((thumbnail) => thumbnail.status === "uploaded")?.variants?.youtube;
  const images = socialImage ? [{ url: socialImage, alt: "Generated Framecraft thumbnail" }] : [];

  return {
    title: `${job.prompt.slice(0, 54)} — Framecraft`,
    description,
    openGraph: { title: "Framecraft creative directions", description, images },
    twitter: { card: socialImage ? "summary_large_image" : "summary", title: "Framecraft creative directions", description, images },
  };
}

export default async function JobPage({ params }: JobPageProps) {
  const { jobId } = await params;
  return <JobStudio jobId={jobId} />;
}
