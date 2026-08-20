import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import {
  Check,
  Copy,
  Download,
  Expand,
  ExternalLink,
  ImageOff,
  LoaderCircle,
  RotateCcw,
  X,
} from "lucide-react";
import {
  getJob,
  thumbnailUrl,
  type Job,
  type Thumbnail,
  type ThumbnailFormat,
} from "../lib/api";
import { AppHeader } from "./AppHeader";

const FORMATS: Array<{ id: ThumbnailFormat; label: string; ratio: string }> = [
  { id: "youtube", label: "YouTube", ratio: "16:9" },
  { id: "shorts", label: "Shorts", ratio: "9:16" },
  { id: "square", label: "Square", ratio: "1:1" },
];

const STYLE_LABELS: Record<string, string> = {
  bold_dramatic: "Bold dramatic",
  clean_minimal: "Clean minimal",
  vibrant_energetic: "Vibrant energetic",
};

function formatStyle(style: string): string {
  return STYLE_LABELS[style] ?? style.replaceAll("_", " ");
}

function ProjectStatus({ job }: { job: Job }) {
  const ready = job.thumbnails.filter((thumbnail) => thumbnail.status === "uploaded").length;
  const failed = job.thumbnails.filter((thumbnail) => thumbnail.status === "failed").length;

  if (job.status === "completed") {
    return <span className="status-badge is-complete"><Check size={13} /> {ready} ready</span>;
  }
  if (job.status === "failed") {
    return <span className="status-badge is-failed"><ImageOff size={13} /> Generation failed</span>;
  }
  return (
    <span className="status-badge is-working">
      <LoaderCircle className="spinner" size={13} />
      Developing {ready + failed} of {job.num_thumbnails}
    </span>
  );
}

interface PreviewModalProps {
  imageUrl: string;
  title: string;
  onClose: () => void;
}

function PreviewModal({ imageUrl, title, onClose }: PreviewModalProps) {
  const closeRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    closeRef.current?.focus();
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    document.body.style.overflow = "hidden";
    window.addEventListener("keydown", onKeyDown);
    return () => {
      document.body.style.overflow = "";
      window.removeEventListener("keydown", onKeyDown);
    };
  }, [onClose]);

  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
      <div className="preview-modal" role="dialog" aria-modal="true" aria-labelledby="preview-title">
        <div className="modal-heading">
          <div><span className="step-label">Full preview</span><h2 id="preview-title">{title}</h2></div>
          <button ref={closeRef} type="button" className="icon-button is-dark" onClick={onClose} aria-label="Close preview"><X size={18} /></button>
        </div>
        <div className="modal-canvas"><img src={imageUrl} alt={`${title} thumbnail preview`} /></div>
      </div>
    </div>
  );
}

interface ThumbnailCardProps {
  thumbnail: Thumbnail;
  format: ThumbnailFormat;
  index: number;
  onPreview: (imageUrl: string, title: string) => void;
}

function ThumbnailCard({ thumbnail, format, index, onPreview }: ThumbnailCardProps) {
  const [copied, setCopied] = useState(false);
  const imageUrl = thumbnailUrl(thumbnail, format);
  const styleLabel = formatStyle(thumbnail.style_name);

  async function copyLink() {
    if (!imageUrl) return;
    try {
      await navigator.clipboard.writeText(imageUrl);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1800);
    } catch {
      window.open(imageUrl, "_blank", "noopener,noreferrer");
    }
  }

  async function downloadImage() {
    if (!imageUrl) return;
    try {
      const response = await fetch(imageUrl);
      if (!response.ok) throw new Error("Download failed");
      const blob = await response.blob();
      const blobUrl = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = blobUrl;
      link.download = `framecraft-${thumbnail.style_name}-${format}.${blob.type.includes("png") ? "png" : "jpg"}`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(blobUrl);
    } catch {
      window.open(imageUrl, "_blank", "noopener,noreferrer");
    }
  }

  return (
    <article className="thumbnail-card">
      <div className="thumbnail-heading">
        <div><span className="concept-index">0{index + 1}</span><h3>{styleLabel}</h3></div>
        <span className={`thumbnail-state is-${thumbnail.status}`}>{thumbnail.status === "uploaded" ? "Ready" : thumbnail.status}</span>
      </div>

      {thumbnail.status === "uploaded" && imageUrl ? (
        <div className={`thumbnail-image ratio-${format}`}>
          <img src={imageUrl} alt={`${styleLabel} generated thumbnail`} />
          <button type="button" className="preview-trigger" onClick={() => onPreview(imageUrl, styleLabel)} aria-label={`Preview ${styleLabel}`}><Expand size={17} /> Preview</button>
        </div>
      ) : thumbnail.status === "failed" ? (
        <div className={`thumbnail-placeholder is-error ratio-${format}`}>
          <ImageOff size={22} aria-hidden="true" />
          <strong>This direction could not be generated</strong>
          <span>{thumbnail.error_message ?? "The image service returned an error."}</span>
        </div>
      ) : (
        <div className={`thumbnail-placeholder ratio-${format}`} aria-label={`${styleLabel} is being generated`}>
          <span className="skeleton-line is-short" />
          <span className="skeleton-line" />
          <span className="skeleton-line is-mid" />
          <p>Composing {styleLabel.toLowerCase()}</p>
        </div>
      )}

      <div className="thumbnail-actions">
        <button type="button" onClick={() => imageUrl && onPreview(imageUrl, styleLabel)} disabled={!imageUrl || thumbnail.status !== "uploaded"}><Expand size={15} /> Preview</button>
        <button type="button" onClick={copyLink} disabled={!imageUrl || thumbnail.status !== "uploaded"}>{copied ? <Check size={15} /> : <Copy size={15} />}{copied ? "Copied" : "Copy link"}</button>
        <button type="button" className="download-button" onClick={downloadImage} disabled={!imageUrl || thumbnail.status !== "uploaded"}><Download size={15} /> Download</button>
      </div>
    </article>
  );
}

export function JobStudio({ jobId }: { jobId: string }) {
  const [format, setFormat] = useState<ThumbnailFormat>("youtube");
  const [preview, setPreview] = useState<{ imageUrl: string; title: string } | null>(null);
  const jobQuery = useQuery({
    queryKey: ["job", jobId],
    queryFn: () => getJob(jobId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "completed" || status === "failed" ? false : 2_000;
    },
  });

  useEffect(() => {
    if (jobQuery.data) {
      document.title = `${jobQuery.data.prompt.slice(0, 54)} — Framecraft`;
    }
    return () => {
      document.title = "Framecraft — YouTube Thumbnail Studio";
    };
  }, [jobQuery.data]);

  if (jobQuery.isPending) {
    return (
      <main className="site-shell results-shell">
        <AppHeader backHref="/" rightLabel="Loading project" />
        <section className="load-state"><LoaderCircle className="spinner" size={25} /><p>Opening your studio…</p></section>
      </main>
    );
  }

  if (jobQuery.isError || !jobQuery.data) {
    return (
      <main className="site-shell results-shell">
        <AppHeader backHref="/" rightLabel="Project unavailable" />
        <section className="error-state">
          <span className="eyebrow">Unable to open project</span>
          <h1>The studio lost this frame.</h1>
          <p>{jobQuery.error instanceof Error ? jobQuery.error.message : "The project could not be loaded."}</p>
          <div className="error-actions">
            <button type="button" className="secondary-button" onClick={() => jobQuery.refetch()}><RotateCcw size={16} /> Try again</button>
            <Link className="primary-button" to="/">Start a new project</Link>
          </div>
        </section>
      </main>
    );
  }

  const job = jobQuery.data;
  const selectedFormat = FORMATS.find((option) => option.id === format)!;

  return (
    <main className="site-shell results-shell">
      <AppHeader backHref="/" rightLabel={`Project ${job.id.slice(0, 8)}`} />
      <section className="results-intro">
        <div className="results-title">
          <div><span className="eyebrow">Creative directions</span><h1>Your frames,<br /><em>developed.</em></h1></div>
          <ProjectStatus job={job} />
        </div>
        <div className="project-brief">
          <img src={job.headshot_url} alt="Source portrait" />
          <div><span>Creative brief</span><p>{job.prompt}</p></div>
        </div>
      </section>

      <section className="results-toolbar" aria-label="Thumbnail format">
        <div><span className="toolbar-label">Output format</span><strong>{selectedFormat.ratio}</strong></div>
        <div className="format-tabs" role="group" aria-label="Choose image format">
          {FORMATS.map((option) => (
            <button key={option.id} type="button" className={format === option.id ? "is-active" : ""} onClick={() => setFormat(option.id)} aria-pressed={format === option.id}>
              {option.label}<span>{option.ratio}</span>
            </button>
          ))}
        </div>
        <Link className="new-project-link" to="/">New project <ExternalLink size={14} /></Link>
      </section>

      <section className={`thumbnail-grid count-${job.thumbnails.length}`}>
        {job.thumbnails.map((thumbnail, index) => (
          <ThumbnailCard key={thumbnail.id} thumbnail={thumbnail} format={format} index={index} onPreview={(imageUrl, title) => setPreview({ imageUrl, title })} />
        ))}
      </section>

      {job.status === "failed" ? (
        <div className="job-failure-note"><ImageOff size={18} /><div><strong>This project did not finish.</strong><p>Review the individual errors above or start again with a different brief.</p></div><Link to="/">Start over</Link></div>
      ) : null}

      {preview ? <PreviewModal imageUrl={preview.imageUrl} title={`${preview.title} · ${selectedFormat.label}`} onClose={() => setPreview(null)} /> : null}
    </main>
  );
}
