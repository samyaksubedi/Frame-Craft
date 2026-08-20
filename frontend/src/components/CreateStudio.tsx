import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowUpRight, ImagePlus, LoaderCircle, X } from "lucide-react";
import { createJob, uploadHeadshot } from "../lib/api";
import { AppHeader } from "./AppHeader";

const ACCEPTED_TYPES = new Set(["image/jpeg", "image/png", "image/webp"]);
const MAX_FILE_SIZE = 10 * 1024 * 1024;

type SubmitStage = "idle" | "uploading" | "creating";

function validateFile(file: File): string | null {
  if (!ACCEPTED_TYPES.has(file.type)) return "Choose a JPEG, PNG, or WebP image.";
  if (file.size > MAX_FILE_SIZE) return "The portrait must be 10 MB or smaller.";
  return null;
}

export function CreateStudio() {
  const navigate = useNavigate();
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const previewUrl = useMemo(() => (file ? URL.createObjectURL(file) : null), [file]);
  const [prompt, setPrompt] = useState("");
  const [count, setCount] = useState(3);
  const [stage, setStage] = useState<SubmitStage>("idle");
  const [error, setError] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  function chooseFile(nextFile: File | undefined) {
    if (!nextFile) return;
    const validationError = validateFile(nextFile);
    if (validationError) {
      setError(validationError);
      if (inputRef.current) inputRef.current.value = "";
      return;
    }
    setFile(nextFile);
    setError(null);
  }

  function clearFile() {
    setFile(null);
    if (inputRef.current) inputRef.current.value = "";
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    const cleanPrompt = prompt.trim();

    if (!file) {
      setError("Add a portrait before creating your frames.");
      return;
    }
    if (cleanPrompt.length < 3) {
      setError("Write at least 3 characters in the creative brief.");
      return;
    }

    try {
      setStage("uploading");
      const headshotUrl = await uploadHeadshot(file);
      setStage("creating");
      const jobId = await createJob({ prompt: cleanPrompt, numThumbnails: count, headshotUrl });
      navigate(`/jobs/${jobId}`);
    } catch (cause) {
      setError(
        cause instanceof Error
          ? cause.message
          : "Something went wrong while starting the project.",
      );
      setStage("idle");
    }
  }

  const isSubmitting = stage !== "idle";
  const buttonLabel =
    stage === "uploading"
      ? "Uploading portrait"
      : stage === "creating"
        ? "Opening studio"
        : "Create frames";

  return (
    <main className="site-shell">
      <AppHeader rightLabel="YouTube · Shorts · Square" />
      <section className="studio-grid">
        <div className="intro-panel">
          <span className="eyebrow">Thumbnail direction, considered</span>
          <h1>Make the frame<br /><em>worth the click.</em></h1>
          <p>
            Bring a clean portrait and the story you want to tell. Framecraft
            develops up to three distinct art directions and prepares each one
            for your channel.
          </p>
          <div className="process-note" aria-label="Three step process">
            <span>01</span> Portrait <span>02</span> Direction <span>03</span> Frames
          </div>
        </div>

        <form className="composer-card" onSubmit={handleSubmit} noValidate>
          <div className="composer-heading">
            <div><span className="step-label">New project</span><h2>Set the direction</h2></div>
            <span className="project-number">01 / 03</span>
          </div>

          <div className="field-group">
            <div className="field-heading">
              <label htmlFor="portrait">Portrait</label>
              <span>JPG, PNG or WebP · 10 MB max</span>
            </div>
            {previewUrl ? (
              <div className="selected-file">
                <img src={previewUrl} alt="Selected portrait preview" />
                <div className="selected-file-copy">
                  <strong>{file?.name}</strong>
                  <span>{file ? `${(file.size / 1024 / 1024).toFixed(1)} MB` : ""}</span>
                </div>
                <button type="button" className="icon-button" onClick={clearFile} aria-label="Remove selected portrait" disabled={isSubmitting}>
                  <X size={17} aria-hidden="true" />
                </button>
              </div>
            ) : (
              <label
                className={`upload-zone${isDragging ? " is-dragging" : ""}`}
                htmlFor="portrait"
                onDragEnter={(event) => { event.preventDefault(); setIsDragging(true); }}
                onDragOver={(event) => event.preventDefault()}
                onDragLeave={(event) => { event.preventDefault(); setIsDragging(false); }}
                onDrop={(event) => { event.preventDefault(); setIsDragging(false); chooseFile(event.dataTransfer.files[0]); }}
              >
                <input ref={inputRef} id="portrait" type="file" accept="image/jpeg,image/png,image/webp" onChange={(event) => chooseFile(event.target.files?.[0])} disabled={isSubmitting} />
                <span className="upload-icon"><ImagePlus size={22} strokeWidth={1.6} aria-hidden="true" /></span>
                <span><strong>Drop a clean portrait here</strong><small>or choose a file from your device</small></span>
                <span className="upload-action">Browse</span>
              </label>
            )}
          </div>

          <div className="field-group">
            <div className="field-heading">
              <label htmlFor="brief">Creative brief</label><span>{prompt.length} / 1000</span>
            </div>
            <textarea id="brief" rows={5} minLength={3} maxLength={1000} value={prompt} onChange={(event) => setPrompt(event.target.value)} placeholder="A bold thumbnail about rebuilding a startup in 30 days — focused, cinematic, minimal text..." disabled={isSubmitting} />
          </div>

          <div className="composer-footer">
            <fieldset className="count-control" disabled={isSubmitting}>
              <legend>Concepts</legend>
              <div>
                {[1, 2, 3].map((option) => (
                  <button className={count === option ? "is-active" : ""} key={option} type="button" onClick={() => setCount(option)} aria-pressed={count === option}>{option}</button>
                ))}
              </div>
            </fieldset>
            <button className="primary-button" type="submit" disabled={isSubmitting}>
              {isSubmitting ? <LoaderCircle className="spinner" size={17} aria-hidden="true" /> : null}
              {buttonLabel}
              {!isSubmitting ? <ArrowUpRight size={18} aria-hidden="true" /> : null}
            </button>
          </div>
          <p className="form-error" role="alert" aria-live="polite">{error}</p>
        </form>
      </section>
    </main>
  );
}
