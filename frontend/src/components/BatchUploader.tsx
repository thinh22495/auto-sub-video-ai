"use client";

import { useState, useCallback } from "react";
import { api } from "@/lib/api-client";
import type { Batch, BatchCreate, SubtitleStyle } from "@/lib/types";
import { FileExplorer } from "@/components/FileExplorer";
import {
  FolderOpen,
  X,
  Plus,
  Play,
  Loader2,
  Globe,
  FileVideo,
  ChevronDown,
  ChevronUp,
} from "lucide-react";

interface BatchFile {
  path: string;
  filename: string;
  source_language: string | null;
}

interface BatchUploaderProps {
  onBatchCreated: (batch: Batch) => void;
}

export default function BatchUploader({ onBatchCreated }: BatchUploaderProps) {
  // Files
  const [files, setFiles] = useState<BatchFile[]>([]);
  const [showBrowser, setShowBrowser] = useState(false);

  // Shared config
  const [targetLanguage, setTargetLanguage] = useState("");
  const [outputFormats, setOutputFormats] = useState<string[]>(["srt"]);
  const [burnIn, setBurnIn] = useState(false);
  const [enableDiarization, setEnableDiarization] = useState(false);
  const [whisperModel, setWhisperModel] = useState("large-v3-turbo");
  const [ollamaModel, setOllamaModel] = useState("");
  const [videoPreset, setVideoPreset] = useState("");
  const [batchName, setBatchName] = useState("");

  // UI state
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const addFile = useCallback((path: string) => {
    const filename = path.split("/").pop() || path.split("\\").pop() || path;
    setFiles((prev) => {
      if (prev.some((f) => f.path === path)) return prev;
      return [...prev, { path, filename, source_language: null }];
    });
    setShowBrowser(false);
  }, []);

  const removeFile = (index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const updateFileLanguage = (index: number, lang: string | null) => {
    setFiles((prev) => {
      const next = [...prev];
      next[index] = { ...next[index], source_language: lang };
      return next;
    });
  };

  const toggleFormat = (fmt: string) => {
    setOutputFormats((prev) =>
      prev.includes(fmt)
        ? prev.filter((f) => f !== fmt)
        : [...prev, fmt]
    );
  };

  const handleSubmit = async () => {
    if (files.length === 0) {
      setError("Please add at least one video file");
      return;
    }
    if (outputFormats.length === 0) {
      setError("Please select at least one output format");
      return;
    }

    setSubmitting(true);
    setError(null);

    try {
      const payload: BatchCreate = {
        name: batchName || undefined,
        files: files.map((f) => ({
          input_path: f.path,
          source_language: f.source_language || undefined,
        })),
        target_language: targetLanguage || undefined,
        output_formats: outputFormats,
        burn_in: burnIn,
        enable_diarization: enableDiarization,
        whisper_model: whisperModel,
        ollama_model: ollamaModel || undefined,
        video_preset: videoPreset || undefined,
      };

      const batch = await api.post<Batch>("/batch", payload);
      onBatchCreated(batch);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-4">
      {/* Batch name */}
      <div>
        <label className="mb-1 block text-sm font-medium text-foreground">
          Tên batch (tùy chọn)
        </label>
        <input
          type="text"
          value={batchName}
          onChange={(e) => setBatchName(e.target.value)}
          placeholder={`Batch (${files.length} file)`}
          className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground"
        />
      </div>

      {/* File list */}
      <div>
        <div className="mb-2 flex items-center justify-between">
          <label className="text-sm font-medium text-foreground">
            File video ({files.length})
          </label>
          <button
            onClick={() => setShowBrowser(true)}
            className="flex items-center gap-1.5 rounded-lg border border-border px-3 py-1.5 text-xs text-foreground transition-colors hover:bg-muted"
          >
            <Plus className="h-3.5 w-3.5" />
            Thêm file
          </button>
        </div>

        {showBrowser && (
          <div className="mb-3 rounded-lg border border-border">
            <FileExplorer
              onSelect={(path) => addFile(path)}
              filterType="video"
            />
          </div>
        )}

        {files.length === 0 ? (
          <div
            className="flex flex-col items-center justify-center rounded-lg border-2 border-dashed border-border py-8 text-muted-foreground cursor-pointer hover:border-primary/50"
            onClick={() => setShowBrowser(true)}
          >
            <FileVideo className="mb-2 h-8 w-8" />
            <p className="text-sm">Nhấn để duyệt và chọn file video</p>
          </div>
        ) : (
          <div className="space-y-1.5 rounded-lg border border-border p-2">
            {files.map((file, i) => (
              <div
                key={file.path}
                className="flex items-center gap-2 rounded-lg bg-muted/50 px-3 py-2"
              >
                <FileVideo className="h-4 w-4 shrink-0 text-primary" />
                <span className="flex-1 truncate text-sm text-foreground">
                  {file.filename}
                </span>
                <select
                  value={file.source_language || ""}
                  onChange={(e) => updateFileLanguage(i, e.target.value || null)}
                  className="rounded border border-border bg-background px-2 py-0.5 text-xs text-foreground"
                  title="Ghi đè ngôn ngữ nguồn"
                >
                  <option value="">Tự động</option>
                  <option value="en">Tiếng Anh</option>
                  <option value="ja">Tiếng Nhật</option>
                  <option value="zh">Tiếng Trung</option>
                  <option value="ko">Tiếng Hàn</option>
                  <option value="vi">Tiếng Việt</option>
                  <option value="fr">Tiếng Pháp</option>
                  <option value="de">Tiếng Đức</option>
                  <option value="es">Tiếng Tây Ban Nha</option>
                  <option value="pt">Tiếng Bồ Đào Nha</option>
                  <option value="ru">Tiếng Nga</option>
                  <option value="th">Tiếng Thái</option>
                </select>
                <button
                  onClick={() => removeFile(i)}
                  className="rounded p-1 text-muted-foreground hover:text-danger"
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Shared config */}
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="mb-1 block text-xs font-medium text-muted-foreground">
            Ngôn ngữ đích
          </label>
          <select
            value={targetLanguage}
            onChange={(e) => setTargetLanguage(e.target.value)}
            className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
          >
            <option value="">Không dịch</option>
            <option value="en">Tiếng Anh</option>
            <option value="vi">Tiếng Việt</option>
            <option value="ja">Tiếng Nhật</option>
            <option value="zh">Tiếng Trung</option>
            <option value="ko">Tiếng Hàn</option>
            <option value="fr">Tiếng Pháp</option>
            <option value="de">Tiếng Đức</option>
            <option value="es">Tiếng Tây Ban Nha</option>
            <option value="pt">Tiếng Bồ Đào Nha</option>
            <option value="ru">Tiếng Nga</option>
            <option value="th">Tiếng Thái</option>
          </select>
        </div>

        <div>
          <label className="mb-1 block text-xs font-medium text-muted-foreground">
            Mô hình Whisper
          </label>
          <select
            value={whisperModel}
            onChange={(e) => setWhisperModel(e.target.value)}
            className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
          >
            <option value="tiny">tiny (nhanh nhất)</option>
            <option value="base">base</option>
            <option value="small">small</option>
            <option value="medium">medium</option>
            <option value="large-v3">large-v3 (tốt nhất)</option>
            <option value="large-v3-turbo">large-v3-turbo (khuyên dùng)</option>
          </select>
        </div>
      </div>

      {/* Output formats */}
      <div>
        <label className="mb-1 block text-xs font-medium text-muted-foreground">
          Định dạng đầu ra
        </label>
        <div className="flex gap-2">
          {["srt", "ass", "vtt"].map((fmt) => (
            <button
              key={fmt}
              onClick={() => toggleFormat(fmt)}
              className={`rounded-lg border px-3 py-1.5 text-xs font-medium uppercase transition-colors ${
                outputFormats.includes(fmt)
                  ? "border-primary bg-primary/10 text-primary"
                  : "border-border text-muted-foreground hover:bg-muted"
              }`}
            >
              .{fmt}
            </button>
          ))}
        </div>
      </div>

      {/* Toggles */}
      <div className="flex gap-4">
        <label className="flex items-center gap-2 text-sm text-foreground">
          <input
            type="checkbox"
            checked={burnIn}
            onChange={(e) => setBurnIn(e.target.checked)}
            className="rounded border-border"
          />
          Gắn phụ đề vào video
        </label>
        <label className="flex items-center gap-2 text-sm text-foreground">
          <input
            type="checkbox"
            checked={enableDiarization}
            onChange={(e) => setEnableDiarization(e.target.checked)}
            className="rounded border-border"
          />
          Phân biệt người nói
        </label>
      </div>

      {/* Advanced options */}
      <button
        onClick={() => setShowAdvanced(!showAdvanced)}
        className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
      >
        {showAdvanced ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
        Tùy chọn nâng cao
      </button>

      {showAdvanced && (
        <div className="grid grid-cols-2 gap-3 rounded-lg border border-border bg-muted/30 p-3">
          <div>
            <label className="mb-1 block text-xs font-medium text-muted-foreground">
              Ollama Model (for translation)
            </label>
            <input
              type="text"
              value={ollamaModel}
              onChange={(e) => setOllamaModel(e.target.value)}
              placeholder="qwen2.5:7b"
              className="w-full rounded border border-border bg-background px-2 py-1.5 text-xs"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-muted-foreground">
              Video Preset
            </label>
            <select
              value={videoPreset}
              onChange={(e) => setVideoPreset(e.target.value)}
              className="w-full rounded border border-border bg-background px-2 py-1.5 text-xs"
            >
              <option value="">Default</option>
              <option value="netflix">Netflix</option>
              <option value="youtube">YouTube</option>
              <option value="bluray">Blu-ray</option>
              <option value="anime">Anime Fansub</option>
              <option value="accessibility">Accessibility</option>
            </select>
          </div>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="rounded-lg border border-danger/30 bg-danger/10 p-3 text-xs text-danger">
          {error}
        </div>
      )}

      {/* Submit */}
      <button
        onClick={handleSubmit}
        disabled={submitting || files.length === 0}
        className="flex w-full items-center justify-center gap-2 rounded-lg bg-primary px-4 py-3 text-sm font-medium text-white transition-colors hover:bg-primary/90 disabled:opacity-50"
      >
        {submitting ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : (
          <Play className="h-4 w-4" />
        )}
        {submitting
          ? "Creating batch..."
          : `Start Batch (${files.length} file${files.length !== 1 ? "s" : ""})`}
      </button>
    </div>
  );
}
