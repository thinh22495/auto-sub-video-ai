"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { api, API_BASE } from "@/lib/api-client";
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
  ChevronLeft,
  ChevronRight,
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
  vram_gb: number;
  parameters: string;
  quality: string;
  speed: string;
  languages: string;
  installed: boolean;
}

interface DownloadProgress {
  task_id: string;
  model_name: string;
  status: string;
  progress_percent: number;
  message: string;
}

const WS_BASE =
  typeof window !== "undefined"
    ? `${window.location.protocol === "https:" ? "wss:" : "ws:"}//${window.location.host}/api`
    : "ws://localhost:8000/api";

export default function ModelsPage() {
  const [whisperModels, setWhisperModels] = useState<WhisperModel[]>([]);
  const [ollamaModels, setOllamaModels] = useState<OllamaModel[]>([]);
  const [recommended, setRecommended] = useState<RecommendedModel[]>([]);
  const [ollamaHealth, setOllamaHealth] = useState<{ status: string } | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [downloadProgress, setDownloadProgress] = useState<Record<string, DownloadProgress>>({});
  const [ollamaProgress, setOllamaProgress] = useState<
    Record<string, { status: string; percent: number; message: string }>
  >({});
  const [recPage, setRecPage] = useState(0);
  const REC_PER_PAGE = 5;
  const wsRefs = useRef<Record<string, WebSocket>>({});

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
    return () => {
      // Cleanup all WebSocket connections
      Object.values(wsRefs.current).forEach((ws) => ws.close());
    };
  }, [fetchAll]);

  const connectDownloadWS = useCallback(
    (taskId: string, modelName: string) => {
      const url = `${WS_BASE}/ws/model-download/${taskId}`;
      const ws = new WebSocket(url);

      ws.onmessage = (event) => {
        try {
          const data: DownloadProgress = JSON.parse(event.data);
          setDownloadProgress((prev) => ({ ...prev, [modelName]: data }));

          if (data.status === "completed") {
            ws.close();
            delete wsRefs.current[modelName];
            // Refresh model list after successful download
            fetchAll();
            // Clear progress after a short delay
            setTimeout(() => {
              setDownloadProgress((prev) => {
                const next = { ...prev };
                delete next[modelName];
                return next;
              });
            }, 2000);
          } else if (data.status === "failed") {
            ws.close();
            delete wsRefs.current[modelName];
            // Clear progress after showing error
            setTimeout(() => {
              setDownloadProgress((prev) => {
                const next = { ...prev };
                delete next[modelName];
                return next;
              });
            }, 5000);
          }
        } catch (e) {
          console.error("Failed to parse download progress:", e);
        }
      };

      ws.onclose = () => {
        delete wsRefs.current[modelName];
      };

      ws.onerror = (err) => {
        console.error("Download WebSocket error:", err);
        ws.close();
      };

      wsRefs.current[modelName] = ws;
    },
    [fetchAll],
  );

  const handleWhisperDownload = async (name: string) => {
    try {
      const result = await api.post<{ task_id: string; model_name: string; status: string }>(
        "/models/whisper/download",
        { name },
      );

      // Set initial progress
      setDownloadProgress((prev) => ({
        ...prev,
        [name]: {
          task_id: result.task_id,
          model_name: name,
          status: "downloading",
          progress_percent: 0,
          message: "Đang bắt đầu tải...",
        },
      }));

      // Connect WebSocket for progress updates
      connectDownloadWS(result.task_id, name);
    } catch (err: any) {
      alert(`Tải xuống thất bại: ${err.message}`);
    }
  };

  const handleWhisperDelete = async (name: string) => {
    if (!confirm(`Xóa mô hình Whisper "${name}"?`)) return;
    setActionLoading(`whisper-${name}`);
    try {
      await api.delete(`/models/whisper/${name}`);
      await fetchAll();
    } catch (err: any) {
      alert(`Xóa thất bại: ${err.message}`);
    } finally {
      setActionLoading(null);
    }
  };

  const handleOllamaPull = async (name: string) => {
    setOllamaProgress((prev) => ({
      ...prev,
      [name]: { status: "downloading", percent: 0, message: "Đang bắt đầu tải..." },
    }));
    try {
      const resp = await fetch(`${API_BASE}/models/ollama/pull`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name }),
      });
      if (!resp.ok) {
        throw new Error(`Lỗi server: ${resp.status} ${resp.statusText}`);
      }
      const reader = resp.body?.getReader();
      const decoder = new TextDecoder();
      let hasError = false;
      if (reader) {
        let buffer = "";
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";
          for (const line of lines) {
            if (!line) continue;
            try {
              const data = JSON.parse(line);
              if (data.status === "error") {
                hasError = true;
                setOllamaProgress((prev) => ({
                  ...prev,
                  [name]: { status: "failed", percent: 0, message: data.error || "Lỗi" },
                }));
                break;
              }
              const percent = data.percent ?? 0;
              const message = data.status || "Đang tải...";
              setOllamaProgress((prev) => ({
                ...prev,
                [name]: { status: "downloading", percent, message },
              }));
            } catch {}
          }
          if (hasError) break;
        }
      }
      if (!hasError) {
        setOllamaProgress((prev) => ({
          ...prev,
          [name]: { status: "completed", percent: 100, message: "Hoàn tất" },
        }));
        await fetchAll();
      }
      setTimeout(
        () => {
          setOllamaProgress((prev) => {
            const next = { ...prev };
            delete next[name];
            return next;
          });
        },
        hasError ? 5000 : 2000,
      );
    } catch (err: any) {
      setOllamaProgress((prev) => ({
        ...prev,
        [name]: { status: "failed", percent: 0, message: err.message },
      }));
      setTimeout(() => {
        setOllamaProgress((prev) => {
          const next = { ...prev };
          delete next[name];
          return next;
        });
      }, 5000);
    }
  };

  const handleOllamaDelete = async (name: string) => {
    if (!confirm(`Xóa mô hình Ollama "${name}"?`)) return;
    setActionLoading(`ollama-${name}`);
    try {
      await api.delete(`/models/ollama/${encodeURIComponent(name)}`);
      await fetchAll();
    } catch (err: any) {
      alert(`Xóa thất bại: ${err.message}`);
    } finally {
      setActionLoading(null);
    }
  };

  const isDownloading = (modelName: string) => {
    const p = downloadProgress[modelName];
    return p && p.status === "downloading";
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
          <h1 className="text-2xl font-bold text-foreground">Quản lý mô hình</h1>
          <p className="text-sm text-muted-foreground">
            Tải xuống và quản lý các mô hình Whisper (Chuyển giọng nói thành văn bản) và Ollama
            (Dịch thuật)
          </p>
        </div>
        <button
          onClick={fetchAll}
          className="flex items-center gap-2 rounded-lg border border-border px-3 py-2 text-sm text-foreground transition-colors hover:bg-muted"
        >
          <RefreshCw className="h-4 w-4" />
          Làm mới
        </button>
      </div>

      {/* Whisper Models */}
      <section>
        <h2 className="mb-4 flex items-center gap-2 text-lg font-semibold text-foreground">
          <Cpu className="h-5 w-5 text-primary" />
          Mô hình Whisper (Chuyển giọng nói thành văn bản)
        </h2>

        {/* Đã tải */}
        {whisperModels.filter((m) => m.downloaded).length > 0 && (
          <div className="mb-6">
            <h3 className="mb-2 text-sm font-medium text-muted-foreground">
              Đã tải ({whisperModels.filter((m) => m.downloaded).length})
            </h3>
            <div className="grid gap-3">
              {whisperModels
                .filter((m) => m.downloaded)
                .map((model) => (
                  <div
                    key={model.name}
                    className="flex items-center gap-4 rounded-xl border border-success/30 bg-card p-4"
                  >
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <CheckCircle2 className="h-4 w-4 text-success" />
                        <span className="font-medium text-foreground">{model.name}</span>
                        {model.is_default && (
                          <span className="rounded bg-primary/10 px-2 py-0.5 text-xs text-primary">
                            Mặc định
                          </span>
                        )}
                        {model.size_on_disk_mb > 0 && (
                          <span className="text-xs text-muted-foreground">
                            ({model.size_on_disk_mb}MB trên ổ đĩa)
                          </span>
                        )}
                      </div>
                      <div className="mt-1 flex gap-4 text-xs text-muted-foreground">
                        <span>VRAM: ~{model.vram_mb}MB</span>
                        <span>Tốc độ: {model.speed}</span>
                        <span>Chất lượng: {model.quality}</span>
                      </div>
                    </div>
                    <div>
                      {actionLoading === `whisper-${model.name}` ? (
                        <Loader2 className="h-5 w-5 animate-spin text-primary" />
                      ) : (
                        <button
                          onClick={() => handleWhisperDelete(model.name)}
                          className="flex items-center gap-1.5 rounded-lg border border-danger/30 px-3 py-1.5 text-xs text-danger transition-colors hover:bg-danger/10"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                          Xóa
                        </button>
                      )}
                    </div>
                  </div>
                ))}
            </div>
          </div>
        )}

        {/* Chưa tải */}
        {whisperModels.filter((m) => !m.downloaded).length > 0 && (
          <div>
            <h3 className="mb-2 text-sm font-medium text-muted-foreground">
              Chưa tải ({whisperModels.filter((m) => !m.downloaded).length})
            </h3>
            <div className="grid gap-3">
              {whisperModels
                .filter((m) => !m.downloaded)
                .map((model) => {
                  const progress = downloadProgress[model.name];
                  const downloading = isDownloading(model.name);
                  const failed = progress?.status === "failed";
                  const completed = progress?.status === "completed";

                  return (
                    <div
                      key={model.name}
                      className={cn(
                        "rounded-xl border bg-card p-4",
                        downloading
                          ? "border-primary/30"
                          : failed
                            ? "border-danger/30"
                            : completed
                              ? "border-success/30"
                              : "border-border opacity-75",
                      )}
                    >
                      <div className="flex items-center gap-4">
                        <div className="flex-1">
                          <div className="flex items-center gap-2">
                            {downloading ? (
                              <Loader2 className="h-4 w-4 animate-spin text-primary" />
                            ) : (
                              <XCircle className="h-4 w-4 text-muted-foreground" />
                            )}
                            <span className="font-medium text-foreground">{model.name}</span>
                            {model.is_default && (
                              <span className="rounded bg-primary/10 px-2 py-0.5 text-xs text-primary">
                                Mặc định
                              </span>
                            )}
                          </div>
                          <div className="mt-1 flex gap-4 text-xs text-muted-foreground">
                            <span>Kích thước: ~{model.size_mb}MB</span>
                            <span>VRAM: ~{model.vram_mb}MB</span>
                            <span>Tốc độ: {model.speed}</span>
                            <span>Chất lượng: {model.quality}</span>
                          </div>
                        </div>
                        <div>
                          {downloading ? (
                            <span className="text-xs text-primary">Đang tải...</span>
                          ) : (
                            <button
                              onClick={() => handleWhisperDownload(model.name)}
                              className="flex items-center gap-1.5 rounded-lg bg-primary px-3 py-1.5 text-xs text-primary-foreground transition-colors hover:bg-primary/90"
                            >
                              <Download className="h-3.5 w-3.5" />
                              Tải xuống
                            </button>
                          )}
                        </div>
                      </div>

                      {/* Progress bar */}
                      {progress && (downloading || failed || completed) && (
                        <div className="mt-3">
                          <div className="mb-1 flex items-center justify-between text-xs">
                            <span
                              className={cn(
                                failed
                                  ? "text-danger"
                                  : completed
                                    ? "text-success"
                                    : "text-muted-foreground",
                              )}
                            >
                              {progress.message}
                            </span>
                            {downloading && (
                              <span className="text-muted-foreground">
                                {progress.progress_percent}%
                              </span>
                            )}
                          </div>
                          <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
                            <div
                              className={cn(
                                "h-full rounded-full transition-all duration-500",
                                failed
                                  ? "bg-danger"
                                  : completed
                                    ? "bg-success"
                                    : "bg-primary",
                                downloading && progress.progress_percent < 100 && "animate-pulse",
                              )}
                              style={{
                                width: `${failed ? 100 : progress.progress_percent}%`,
                              }}
                            />
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
            </div>
          </div>
        )}
      </section>

      {/* Ollama Models */}
      <section>
        <h2 className="mb-4 flex items-center gap-2 text-lg font-semibold text-foreground">
          <HardDrive className="h-5 w-5 text-accent" />
          Mô hình Ollama (Dịch thuật)
          <span
            className={cn(
              "ml-2 rounded px-2 py-0.5 text-xs",
              ollamaHealth?.status === "up"
                ? "bg-success/10 text-success"
                : "bg-danger/10 text-danger",
            )}
          >
            {ollamaHealth?.status === "up" ? "Đã kết nối" : "Mất kết nối"}
          </span>
        </h2>

        {/* Installed Ollama Models */}
        <div className="grid gap-3">
          {ollamaModels.map((model) => (
            <div
              key={model.name}
              className="flex items-center gap-4 rounded-xl border border-success/30 bg-card p-4"
            >
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-success" />
                  <span className="font-medium text-foreground">{model.name}</span>
                  {model.is_default && (
                    <span className="rounded bg-accent/10 px-2 py-0.5 text-xs text-accent">
                      Mặc định
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
                    Xóa
                  </button>
                )}
              </div>
            </div>
          ))}

          {ollamaModels.length === 0 && Object.keys(ollamaProgress).length === 0 && (
            <p className="py-4 text-center text-sm text-muted-foreground">
              {ollamaHealth?.status === "up"
                ? "Chưa có mô hình nào. Hãy tải một mô hình đề xuất bên dưới."
                : "Không thể kết nối đến Ollama."}
            </p>
          )}

          {/* Ollama download progress cards */}
          {Object.entries(ollamaProgress).map(([name, prog]) => (
            <div
              key={`prog-${name}`}
              className={cn(
                "rounded-xl border bg-card p-4",
                prog.status === "failed"
                  ? "border-danger/30"
                  : prog.status === "completed"
                    ? "border-success/30"
                    : "border-primary/30",
              )}
            >
              <div className="flex items-center gap-2">
                {prog.status === "downloading" ? (
                  <Loader2 className="h-4 w-4 animate-spin text-primary" />
                ) : prog.status === "completed" ? (
                  <CheckCircle2 className="h-4 w-4 text-success" />
                ) : (
                  <XCircle className="h-4 w-4 text-danger" />
                )}
                <span className="font-medium text-foreground">{name}</span>
              </div>
              <div className="mt-2">
                <div className="mb-1 flex items-center justify-between text-xs">
                  <span
                    className={cn(
                      prog.status === "failed"
                        ? "text-danger"
                        : prog.status === "completed"
                          ? "text-success"
                          : "text-muted-foreground",
                    )}
                  >
                    {prog.message}
                  </span>
                  {prog.status === "downloading" && prog.percent > 0 && (
                    <span className="text-muted-foreground">{prog.percent}%</span>
                  )}
                </div>
                <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
                  <div
                    className={cn(
                      "h-full rounded-full transition-all duration-500",
                      prog.status === "failed"
                        ? "bg-danger"
                        : prog.status === "completed"
                          ? "bg-success"
                          : "bg-primary",
                      prog.status === "downloading" && prog.percent < 100 && "animate-pulse",
                    )}
                    style={{
                      width: `${prog.status === "failed" ? 100 : prog.percent}%`,
                    }}
                  />
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Recommended Models - detailed table with pagination */}
        {(() => {
          const notInstalled = [...recommended.filter((m) => !m.installed)].sort(
            (a, b) => a.size_gb - b.size_gb,
          );
          const totalPages = Math.ceil(notInstalled.length / REC_PER_PAGE);
          const page = Math.min(recPage, Math.max(totalPages - 1, 0));
          const paged = notInstalled.slice(page * REC_PER_PAGE, (page + 1) * REC_PER_PAGE);
          const startIdx = page * REC_PER_PAGE + 1;
          const endIdx = Math.min((page + 1) * REC_PER_PAGE, notInstalled.length);

          if (notInstalled.length === 0) return null;

          return (
            <div className="mt-6">
              <h3 className="mb-3 flex items-center gap-2 text-sm font-medium text-muted-foreground">
                <Star className="h-4 w-4" />
                Đề xuất cho dịch thuật ({notInstalled.length})
              </h3>

              <div className="overflow-hidden rounded-xl border border-border">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border bg-muted/50">
                      <th className="px-4 py-2.5 text-left font-medium text-muted-foreground">
                        Mô hình
                      </th>
                      <th className="px-3 py-2.5 text-center font-medium text-muted-foreground">
                        Tham số
                      </th>
                      <th className="px-3 py-2.5 text-center font-medium text-muted-foreground">
                        Dung lượng
                      </th>
                      <th className="px-3 py-2.5 text-center font-medium text-muted-foreground">
                        VRAM
                      </th>
                      <th className="px-3 py-2.5 text-center font-medium text-muted-foreground">
                        Chất lượng
                      </th>
                      <th className="px-3 py-2.5 text-center font-medium text-muted-foreground">
                        Tốc độ
                      </th>
                      <th className="px-3 py-2.5 text-right font-medium text-muted-foreground">
                        Hành động
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {paged.map((model, idx) => (
                      <tr
                        key={model.name}
                        className={cn(
                          "transition-colors hover:bg-muted/30",
                          idx < paged.length - 1 && "border-b border-border",
                        )}
                      >
                        <td className="px-4 py-3">
                          <div className="font-medium text-foreground">{model.name}</div>
                          <div className="mt-0.5 text-xs text-muted-foreground">
                            {model.description}
                          </div>
                          <div className="mt-0.5 text-xs text-muted-foreground/70">
                            {model.languages}
                          </div>
                        </td>
                        <td className="px-3 py-3 text-center text-xs text-muted-foreground">
                          {model.parameters}
                        </td>
                        <td className="px-3 py-3 text-center text-xs text-muted-foreground">
                          {model.size_gb}GB
                        </td>
                        <td className="px-3 py-3 text-center text-xs text-muted-foreground">
                          ~{model.vram_gb}GB
                        </td>
                        <td className="px-3 py-3 text-center">
                          <span
                            className={cn(
                              "rounded-full px-2 py-0.5 text-xs",
                              model.quality === "xuất sắc"
                                ? "bg-success/10 text-success"
                                : model.quality === "rất tốt"
                                  ? "bg-primary/10 text-primary"
                                  : model.quality === "tốt"
                                    ? "bg-accent/10 text-accent"
                                    : "bg-muted text-muted-foreground",
                            )}
                          >
                            {model.quality}
                          </span>
                        </td>
                        <td className="px-3 py-3 text-center">
                          <span
                            className={cn(
                              "rounded-full px-2 py-0.5 text-xs",
                              model.speed === "rất nhanh"
                                ? "bg-success/10 text-success"
                                : model.speed === "nhanh"
                                  ? "bg-primary/10 text-primary"
                                  : model.speed === "vừa phải"
                                    ? "bg-accent/10 text-accent"
                                    : "bg-warning/10 text-warning",
                            )}
                          >
                            {model.speed}
                          </span>
                        </td>
                        <td className="px-3 py-3 text-right">
                          {ollamaProgress[model.name] ? (
                            <Loader2 className="ml-auto h-4 w-4 animate-spin text-primary" />
                          ) : (
                            <button
                              onClick={() => handleOllamaPull(model.name)}
                              disabled={ollamaHealth?.status !== "up"}
                              className="inline-flex items-center gap-1 rounded-lg bg-accent px-3 py-1.5 text-xs text-accent-foreground transition-colors hover:bg-accent/90 disabled:opacity-50"
                            >
                              <Download className="h-3 w-3" />
                              Tải về
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>

                {/* Pagination footer */}
                {totalPages > 1 && (
                  <div className="flex items-center justify-between border-t border-border bg-muted/30 px-4 py-2.5">
                    <span className="text-xs text-muted-foreground">
                      Hiển thị {startIdx}–{endIdx} / {notInstalled.length} mô hình
                    </span>
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => setRecPage((p) => Math.max(0, p - 1))}
                        disabled={page === 0}
                        className="rounded-lg px-2 py-1 text-xs text-muted-foreground transition-colors hover:bg-muted disabled:opacity-30"
                      >
                        <ChevronLeft className="h-4 w-4" />
                      </button>
                      {Array.from({ length: totalPages }, (_, i) => (
                        <button
                          key={i}
                          onClick={() => setRecPage(i)}
                          className={cn(
                            "min-w-[1.75rem] rounded-lg px-2 py-1 text-xs transition-colors",
                            i === page
                              ? "bg-primary text-primary-foreground"
                              : "text-muted-foreground hover:bg-muted",
                          )}
                        >
                          {i + 1}
                        </button>
                      ))}
                      <button
                        onClick={() => setRecPage((p) => Math.min(totalPages - 1, p + 1))}
                        disabled={page >= totalPages - 1}
                        className="rounded-lg px-2 py-1 text-xs text-muted-foreground transition-colors hover:bg-muted disabled:opacity-30"
                      >
                        <ChevronRight className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          );
        })()}
      </section>
    </div>
  );
}
