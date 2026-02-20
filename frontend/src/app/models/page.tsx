"use client";

import { useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api-client";
import {
  Cpu,
  Download,
  Trash2,
  CheckCircle2,
  XCircle,
  Loader2,
  HardDrive,
  Star,
  RefreshCw,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface WhisperModel {
  name: string;
  downloaded: boolean;
  size_mb: number;
  size_on_disk_mb: number;
  vram_mb: number;
  speed: string;
  quality: string;
  is_default: boolean;
}

interface OllamaModel {
  name: string;
  size_gb: number;
  parameter_size: string;
  quantization: string;
  family: string;
  is_default: boolean;
}

interface RecommendedModel {
  name: string;
  description: string;
  size_gb: number;
  languages: string;
  installed: boolean;
}

export default function ModelsPage() {
  const [whisperModels, setWhisperModels] = useState<WhisperModel[]>([]);
  const [ollamaModels, setOllamaModels] = useState<OllamaModel[]>([]);
  const [recommended, setRecommended] = useState<RecommendedModel[]>([]);
  const [ollamaHealth, setOllamaHealth] = useState<{ status: string } | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const fetchAll = useCallback(async () => {
    setLoading(true);
    try {
      const [wm, om, rec, health] = await Promise.all([
        api.get<WhisperModel[]>("/models/whisper"),
        api.get<OllamaModel[]>("/models/ollama"),
        api.get<RecommendedModel[]>("/models/ollama/recommended"),
        api.get<{ status: string }>("/models/ollama/health"),
      ]);
      setWhisperModels(wm);
      setOllamaModels(om);
      setRecommended(rec);
      setOllamaHealth(health);
    } catch (err) {
      console.error("Failed to fetch models:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  const handleWhisperDownload = async (name: string) => {
    setActionLoading(`whisper-${name}`);
    try {
      await api.post("/models/whisper/download", { name });
      await fetchAll();
    } catch (err: any) {
      alert(`Download failed: ${err.message}`);
    } finally {
      setActionLoading(null);
    }
  };

  const handleWhisperDelete = async (name: string) => {
    if (!confirm(`Delete Whisper model "${name}"?`)) return;
    setActionLoading(`whisper-${name}`);
    try {
      await api.delete(`/models/whisper/${name}`);
      await fetchAll();
    } catch (err: any) {
      alert(`Delete failed: ${err.message}`);
    } finally {
      setActionLoading(null);
    }
  };

  const handleOllamaPull = async (name: string) => {
    setActionLoading(`ollama-${name}`);
    try {
      const resp = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api"}/models/ollama/pull`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name }),
        }
      );
      // Read NDJSON stream
      const reader = resp.body?.getReader();
      const decoder = new TextDecoder();
      if (reader) {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          const lines = decoder.decode(value).split("\n").filter(Boolean);
          for (const line of lines) {
            try {
              const data = JSON.parse(line);
              if (data.status === "error") {
                alert(`Pull failed: ${data.error}`);
                break;
              }
            } catch {}
          }
        }
      }
      await fetchAll();
    } catch (err: any) {
      alert(`Pull failed: ${err.message}`);
    } finally {
      setActionLoading(null);
    }
  };

  const handleOllamaDelete = async (name: string) => {
    if (!confirm(`Delete Ollama model "${name}"?`)) return;
    setActionLoading(`ollama-${name}`);
    try {
      await api.delete(`/models/ollama/${encodeURIComponent(name)}`);
      await fetchAll();
    } catch (err: any) {
      alert(`Delete failed: ${err.message}`);
    } finally {
      setActionLoading(null);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Model Management</h1>
          <p className="text-sm text-muted-foreground">
            Download and manage Whisper (STT) and Ollama (Translation) models
          </p>
        </div>
        <button
          onClick={fetchAll}
          className="flex items-center gap-2 rounded-lg border border-border px-3 py-2 text-sm text-foreground transition-colors hover:bg-muted"
        >
          <RefreshCw className="h-4 w-4" />
          Refresh
        </button>
      </div>

      {/* Whisper Models */}
      <section>
        <h2 className="mb-4 flex items-center gap-2 text-lg font-semibold text-foreground">
          <Cpu className="h-5 w-5 text-primary" />
          Whisper Models (Speech-to-Text)
        </h2>
        <div className="grid gap-3">
          {whisperModels.map((model) => (
            <div
              key={model.name}
              className="flex items-center gap-4 rounded-xl border border-border bg-card p-4"
            >
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <span className="font-medium text-foreground">{model.name}</span>
                  {model.is_default && (
                    <span className="rounded bg-primary/10 px-2 py-0.5 text-xs text-primary">
                      Default
                    </span>
                  )}
                  {model.downloaded && (
                    <CheckCircle2 className="h-4 w-4 text-success" />
                  )}
                </div>
                <div className="mt-1 flex gap-4 text-xs text-muted-foreground">
                  <span>Size: ~{model.size_mb}MB</span>
                  <span>VRAM: ~{model.vram_mb}MB</span>
                  <span>Speed: {model.speed}</span>
                  <span>Quality: {model.quality}</span>
                </div>
              </div>
              <div>
                {actionLoading === `whisper-${model.name}` ? (
                  <Loader2 className="h-5 w-5 animate-spin text-primary" />
                ) : model.downloaded ? (
                  <button
                    onClick={() => handleWhisperDelete(model.name)}
                    className="flex items-center gap-1.5 rounded-lg border border-danger/30 px-3 py-1.5 text-xs text-danger transition-colors hover:bg-danger/10"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                    Delete
                  </button>
                ) : (
                  <button
                    onClick={() => handleWhisperDownload(model.name)}
                    className="flex items-center gap-1.5 rounded-lg bg-primary px-3 py-1.5 text-xs text-primary-foreground transition-colors hover:bg-primary/90"
                  >
                    <Download className="h-3.5 w-3.5" />
                    Download
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Ollama Models */}
      <section>
        <h2 className="mb-4 flex items-center gap-2 text-lg font-semibold text-foreground">
          <HardDrive className="h-5 w-5 text-accent" />
          Ollama Models (Translation)
          <span
            className={cn(
              "ml-2 rounded px-2 py-0.5 text-xs",
              ollamaHealth?.status === "up"
                ? "bg-success/10 text-success"
                : "bg-danger/10 text-danger"
            )}
          >
            {ollamaHealth?.status === "up" ? "Connected" : "Disconnected"}
          </span>
        </h2>

        {/* Installed Models */}
        {ollamaModels.length > 0 && (
          <div className="mb-6">
            <h3 className="mb-2 text-sm font-medium text-muted-foreground">
              Installed ({ollamaModels.length})
            </h3>
            <div className="grid gap-3">
              {ollamaModels.map((model) => (
                <div
                  key={model.name}
                  className="flex items-center gap-4 rounded-xl border border-border bg-card p-4"
                >
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-foreground">
                        {model.name}
                      </span>
                      {model.is_default && (
                        <span className="rounded bg-accent/10 px-2 py-0.5 text-xs text-accent">
                          Default
                        </span>
                      )}
                    </div>
                    <div className="mt-1 flex gap-4 text-xs text-muted-foreground">
                      <span>{model.size_gb}GB</span>
                      {model.parameter_size && <span>{model.parameter_size}</span>}
                      {model.quantization && <span>Q: {model.quantization}</span>}
                      {model.family && <span>{model.family}</span>}
                    </div>
                  </div>
                  <div>
                    {actionLoading === `ollama-${model.name}` ? (
                      <Loader2 className="h-5 w-5 animate-spin text-primary" />
                    ) : (
                      <button
                        onClick={() => handleOllamaDelete(model.name)}
                        className="flex items-center gap-1.5 rounded-lg border border-danger/30 px-3 py-1.5 text-xs text-danger transition-colors hover:bg-danger/10"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                        Delete
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Recommended Models */}
        <div>
          <h3 className="mb-2 flex items-center gap-2 text-sm font-medium text-muted-foreground">
            <Star className="h-4 w-4" />
            Recommended for Translation
          </h3>
          <div className="grid gap-3">
            {recommended.map((model) => (
              <div
                key={model.name}
                className="flex items-center gap-4 rounded-xl border border-border bg-card p-4"
              >
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-foreground">
                      {model.name}
                    </span>
                    {model.installed && (
                      <CheckCircle2 className="h-4 w-4 text-success" />
                    )}
                  </div>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {model.description}
                  </p>
                  <div className="mt-1 flex gap-4 text-xs text-muted-foreground">
                    <span>{model.size_gb}GB</span>
                    <span>{model.languages}</span>
                  </div>
                </div>
                <div>
                  {actionLoading === `ollama-${model.name}` ? (
                    <Loader2 className="h-5 w-5 animate-spin text-primary" />
                  ) : model.installed ? (
                    <span className="text-xs text-success">Installed</span>
                  ) : (
                    <button
                      onClick={() => handleOllamaPull(model.name)}
                      disabled={ollamaHealth?.status !== "up"}
                      className="flex items-center gap-1.5 rounded-lg bg-accent px-3 py-1.5 text-xs text-accent-foreground transition-colors hover:bg-accent/90 disabled:opacity-50"
                    >
                      <Download className="h-3.5 w-3.5" />
                      Pull
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}
