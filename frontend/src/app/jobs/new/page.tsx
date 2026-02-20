"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api-client";
import type { JobCreate } from "@/lib/types";
import {
  Play,
  FileVideo,
  Languages,
  Subtitles,
  Settings2,
  Loader2,
} from "lucide-react";

interface LanguageOption {
  code: string;
  name: string;
}

export default function NewJobPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [languages, setLanguages] = useState<LanguageOption[]>([]);

  // Form state
  const [inputPath, setInputPath] = useState("");
  const [sourceLanguage, setSourceLanguage] = useState<string>("auto");
  const [targetLanguage, setTargetLanguage] = useState<string>("");
  const [outputFormats, setOutputFormats] = useState<string[]>(["srt"]);
  const [burnIn, setBurnIn] = useState(false);
  const [whisperModel, setWhisperModel] = useState("large-v3-turbo");

  useEffect(() => {
    api
      .get<LanguageOption[]>("/languages")
      .then(setLanguages)
      .catch(() => {});
  }, []);

  const toggleFormat = (fmt: string) => {
    setOutputFormats((prev) =>
      prev.includes(fmt) ? prev.filter((f) => f !== fmt) : [...prev, fmt]
    );
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputPath.trim()) {
      setError("Please enter a video file path");
      return;
    }
    if (outputFormats.length === 0) {
      setError("Please select at least one output format");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const body: JobCreate = {
        input_path: inputPath.trim(),
        source_language: sourceLanguage === "auto" ? null : sourceLanguage,
        target_language: targetLanguage || null,
        output_formats: outputFormats,
        burn_in: burnIn,
        whisper_model: whisperModel,
      };

      const job = await api.post<{ id: string }>("/jobs", body);
      router.push(`/jobs/${job.id}/`);
    } catch (err: any) {
      setError(err.message || "Failed to create job");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground">New Subtitle Job</h1>
        <p className="text-sm text-muted-foreground">
          Configure and start a new subtitle generation job
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Input File */}
        <Section icon={<FileVideo className="h-5 w-5" />} title="Input Video">
          <label className="block text-sm font-medium text-muted-foreground">
            Video File Path
          </label>
          <input
            type="text"
            value={inputPath}
            onChange={(e) => setInputPath(e.target.value)}
            placeholder="/data/videos/my_video.mp4"
            className="mt-1 w-full rounded-lg border border-border bg-muted px-4 py-2.5 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
          />
          <p className="mt-1 text-xs text-muted-foreground">
            Path to the video file inside the Docker container (mounted at /data/videos/)
          </p>
        </Section>

        {/* Language Settings */}
        <Section icon={<Languages className="h-5 w-5" />} title="Language">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-muted-foreground">
                Source Language
              </label>
              <select
                value={sourceLanguage}
                onChange={(e) => setSourceLanguage(e.target.value)}
                className="mt-1 w-full rounded-lg border border-border bg-muted px-4 py-2.5 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
              >
                <option value="auto">Auto-detect</option>
                {languages.map((lang) => (
                  <option key={lang.code} value={lang.code}>
                    {lang.name} ({lang.code})
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-muted-foreground">
                Target Language (Translation)
              </label>
              <select
                value={targetLanguage}
                onChange={(e) => setTargetLanguage(e.target.value)}
                className="mt-1 w-full rounded-lg border border-border bg-muted px-4 py-2.5 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
              >
                <option value="">No translation</option>
                {languages.map((lang) => (
                  <option key={lang.code} value={lang.code}>
                    {lang.name} ({lang.code})
                  </option>
                ))}
              </select>
            </div>
          </div>
        </Section>

        {/* Output Settings */}
        <Section icon={<Subtitles className="h-5 w-5" />} title="Output">
          <div>
            <label className="mb-2 block text-sm font-medium text-muted-foreground">
              Subtitle Formats
            </label>
            <div className="flex gap-3">
              {["srt", "ass", "vtt"].map((fmt) => (
                <button
                  key={fmt}
                  type="button"
                  onClick={() => toggleFormat(fmt)}
                  className={`rounded-lg border px-4 py-2 text-sm font-medium uppercase transition-colors ${
                    outputFormats.includes(fmt)
                      ? "border-primary bg-primary/10 text-primary"
                      : "border-border bg-muted text-muted-foreground hover:border-foreground/30"
                  }`}
                >
                  .{fmt}
                </button>
              ))}
            </div>
          </div>

          <div className="mt-4">
            <label className="flex items-center gap-3">
              <input
                type="checkbox"
                checked={burnIn}
                onChange={(e) => setBurnIn(e.target.checked)}
                className="h-4 w-4 rounded border-border bg-muted text-primary focus:ring-primary"
              />
              <span className="text-sm text-foreground">
                Also generate video with burned-in subtitles
              </span>
            </label>
          </div>
        </Section>

        {/* Model Settings */}
        <Section icon={<Settings2 className="h-5 w-5" />} title="Model">
          <label className="block text-sm font-medium text-muted-foreground">
            Whisper Model
          </label>
          <select
            value={whisperModel}
            onChange={(e) => setWhisperModel(e.target.value)}
            className="mt-1 w-full rounded-lg border border-border bg-muted px-4 py-2.5 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
          >
            <option value="tiny">tiny (fastest, lowest accuracy)</option>
            <option value="base">base</option>
            <option value="small">small</option>
            <option value="medium">medium</option>
            <option value="large-v2">large-v2</option>
            <option value="large-v3">large-v3</option>
            <option value="large-v3-turbo">large-v3-turbo (recommended)</option>
          </select>
        </Section>

        {/* Error */}
        {error && (
          <div className="rounded-lg border border-danger/30 bg-danger/10 p-4 text-sm text-danger">
            {error}
          </div>
        )}

        {/* Submit */}
        <button
          type="submit"
          disabled={loading}
          className="flex w-full items-center justify-center gap-2 rounded-lg bg-primary py-3 text-sm font-semibold text-primary-foreground transition-colors hover:bg-primary/90 disabled:opacity-50"
        >
          {loading ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Creating job...
            </>
          ) : (
            <>
              <Play className="h-4 w-4" />
              Start Transcription
            </>
          )}
        </button>
      </form>
    </div>
  );
}

function Section({
  icon,
  title,
  children,
}: {
  icon: React.ReactNode;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-xl border border-border bg-card p-6">
      <div className="mb-4 flex items-center gap-2">
        <span className="text-primary">{icon}</span>
        <h2 className="text-base font-semibold text-foreground">{title}</h2>
      </div>
      <div className="space-y-3">{children}</div>
    </div>
  );
}
