"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api-client";
import type { JobCreate, Preset, SubtitleStyle } from "@/lib/types";
import { LanguageSelector } from "@/components/LanguageSelector";
import { SubtitlePreview } from "@/components/SubtitlePreview";
import { SubtitleStyler } from "@/components/SubtitleStyler";
import { FileExplorer } from "@/components/FileExplorer";
import {
  Play,
  FileVideo,
  Languages,
  Subtitles,
  Settings2,
  Loader2,
  HardDrive,
  Palette,
  ChevronDown,
  ChevronUp,
  FolderOpen,
} from "lucide-react";

interface OllamaModelOption {
  name: string;
  size_gb: number;
  parameter_size: string;
}

const DEFAULT_STYLE: SubtitleStyle = {
  font_name: "Arial",
  font_size: 24,
  primary_color: "#FFFFFF",
  secondary_color: "#FFFF00",
  outline_color: "#000000",
  shadow_color: "#000000",
  outline_width: 2.0,
  shadow_depth: 1.0,
  alignment: 2,
  margin_left: 10,
  margin_right: 10,
  margin_vertical: 30,
  bold: false,
  italic: false,
  max_line_length: 42,
  max_lines: 2,
};

export default function NewJobPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [ollamaModels, setOllamaModels] = useState<OllamaModelOption[]>([]);
  const [presets, setPresets] = useState<Preset[]>([]);

  // Form state
  const [inputPath, setInputPath] = useState("");
  const [sourceLanguage, setSourceLanguage] = useState<string>("auto");
  const [targetLanguage, setTargetLanguage] = useState<string>("");
  const [outputFormats, setOutputFormats] = useState<string[]>(["srt"]);
  const [burnIn, setBurnIn] = useState(false);
  const [whisperModel, setWhisperModel] = useState("large-v3-turbo");
  const [ollamaModel, setOllamaModel] = useState<string>("");
  const [selectedPreset, setSelectedPreset] = useState<string>("");
  const [subtitleStyle, setSubtitleStyle] = useState<SubtitleStyle>(DEFAULT_STYLE);
  const [showStyleEditor, setShowStyleEditor] = useState(false);
  const [showFileBrowser, setShowFileBrowser] = useState(false);

  useEffect(() => {
    // Load Ollama models and presets in parallel
    api
      .get<OllamaModelOption[]>("/models/ollama")
      .then((models) => {
        setOllamaModels(models);
        const defaultModel = models.find((m) =>
          m.name.includes("qwen2.5")
        );
        if (defaultModel) setOllamaModel(defaultModel.name);
        else if (models.length > 0) setOllamaModel(models[0].name);
      })
      .catch(() => {});

    api
      .get<Preset[]>("/presets")
      .then((data) => setPresets(data))
      .catch(() => {});
  }, []);

  const handlePresetChange = (presetId: string) => {
    setSelectedPreset(presetId);
    if (presetId) {
      const preset = presets.find((p) => p.id === presetId);
      if (preset) {
        setSubtitleStyle({ ...DEFAULT_STYLE, ...preset.subtitle_style });
      }
    } else {
      setSubtitleStyle(DEFAULT_STYLE);
    }
  };

  const toggleFormat = (fmt: string) => {
    setOutputFormats((prev) =>
      prev.includes(fmt) ? prev.filter((f) => f !== fmt) : [...prev, fmt]
    );
  };

  const needsTranslation = targetLanguage !== "";

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
    if (needsTranslation && !ollamaModel) {
      setError("Please select a translation model or install one from the Models page");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      // Resolve preset key for backend (strip builtin_ prefix)
      let videoPreset: string | undefined;
      if (selectedPreset.startsWith("builtin_")) {
        videoPreset = selectedPreset.replace("builtin_", "");
      }

      const body: JobCreate = {
        input_path: inputPath.trim(),
        source_language: sourceLanguage === "auto" ? null : sourceLanguage,
        target_language: targetLanguage || null,
        output_formats: outputFormats,
        burn_in: burnIn,
        whisper_model: whisperModel,
        ollama_model: needsTranslation ? ollamaModel : undefined,
        subtitle_style: subtitleStyle,
        video_preset: videoPreset,
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
        <h1 className="text-2xl font-bold text-foreground">Tạo phụ đề mới</h1>
        <p className="text-sm text-muted-foreground">
          Cấu hình và bắt đầu tạo phụ đề cho video
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Input File */}
        <Section icon={<FileVideo className="h-5 w-5" />} title="Video đầu vào">
          <label className="block text-sm font-medium text-muted-foreground">
            Đường dẫn file video
          </label>
          <div className="mt-1 flex gap-2">
            <input
              type="text"
              value={inputPath}
              onChange={(e) => setInputPath(e.target.value)}
              placeholder="/data/videos/my_video.mp4"
              className="flex-1 rounded-lg border border-border bg-muted px-4 py-2.5 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
            />
            <button
              type="button"
              onClick={() => setShowFileBrowser(!showFileBrowser)}
              className={`flex items-center gap-1.5 rounded-lg border px-3 py-2.5 text-sm transition-colors ${
                showFileBrowser
                  ? "border-primary bg-primary/10 text-primary"
                  : "border-border bg-muted text-muted-foreground hover:border-foreground/30"
              }`}
            >
              <FolderOpen className="h-4 w-4" />
              Duyệt
            </button>
          </div>
          {showFileBrowser && (
            <div className="mt-3">
              <FileExplorer
                filterType="video"
                onSelect={(path) => {
                  setInputPath(path);
                  setShowFileBrowser(false);
                }}
              />
            </div>
          )}
          <p className="mt-1 text-xs text-muted-foreground">
            Chọn file video hoặc nhập đường dẫn thủ công
          </p>
        </Section>

        {/* Language Settings */}
        <Section icon={<Languages className="h-5 w-5" />} title="Ngôn ngữ">
          <div className="grid grid-cols-2 gap-4">
            <LanguageSelector
              value={sourceLanguage}
              onChange={setSourceLanguage}
              label="Ngôn ngữ nguồn"
              allowAuto
            />
            <LanguageSelector
              value={targetLanguage}
              onChange={setTargetLanguage}
              label="Ngôn ngữ đích (Dịch thuật)"
              allowNone
              noneLabel="Không dịch"
            />
          </div>
          {needsTranslation && (
            <p className="text-xs text-accent">
              Đã bật dịch thuật: phụ đề sẽ được dịch qua Ollama
            </p>
          )}
        </Section>

        {/* Translation Model (shown only when translation is needed) */}
        {needsTranslation && (
          <Section
            icon={<HardDrive className="h-5 w-5" />}
            title="Mô hình dịch thuật"
          >
            {ollamaModels.length === 0 ? (
              <div className="rounded-lg border border-warning/30 bg-warning/10 p-3 text-xs text-warning">
                Chưa cài đặt mô hình Ollama nào. Truy cập{" "}
                <a href="/models/" className="underline">
                  trang Mô hình
                </a>{" "}
                để tải mô hình dịch thuật trước.
              </div>
            ) : (
              <>
                <label className="block text-sm font-medium text-muted-foreground">
                  Mô hình Ollama
                </label>
                <select
                  value={ollamaModel}
                  onChange={(e) => setOllamaModel(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-border bg-muted px-4 py-2.5 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                >
                  {ollamaModels.map((m) => (
                    <option key={m.name} value={m.name}>
                      {m.name} ({m.size_gb}GB
                      {m.parameter_size ? `, ${m.parameter_size}` : ""})
                    </option>
                  ))}
                </select>
              </>
            )}
          </Section>
        )}

        {/* Output Settings */}
        <Section icon={<Subtitles className="h-5 w-5" />} title="Đầu ra">
          <div>
            <label className="mb-2 block text-sm font-medium text-muted-foreground">
              Định dạng phụ đề
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
                Đồng thời tạo video có gắn phụ đề
              </span>
            </label>
          </div>
        </Section>

        {/* Subtitle Style & Preset */}
        <Section icon={<Palette className="h-5 w-5" />} title="Kiểu phụ đề">
          <label className="block text-sm font-medium text-muted-foreground">
            Mẫu kiểu có sẵn
          </label>
          <select
            value={selectedPreset}
            onChange={(e) => handlePresetChange(e.target.value)}
            className="mt-1 w-full rounded-lg border border-border bg-muted px-4 py-2.5 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
          >
            <option value="">Mặc định</option>
            {presets.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
                {p.is_builtin ? " (có sẵn)" : ""}
              </option>
            ))}
          </select>

          {/* Live Preview */}
          <div className="mt-3 flex justify-center">
            <SubtitlePreview style={subtitleStyle} width={560} height={200} />
          </div>

          {/* Expand/collapse style editor */}
          <button
            type="button"
            onClick={() => setShowStyleEditor(!showStyleEditor)}
            className="mt-3 flex items-center gap-1.5 text-xs text-muted-foreground transition-colors hover:text-foreground"
          >
            {showStyleEditor ? (
              <ChevronUp className="h-3.5 w-3.5" />
            ) : (
              <ChevronDown className="h-3.5 w-3.5" />
            )}
            {showStyleEditor ? "Ẩn" : "Hiện"} tùy chọn kiểu nâng cao
          </button>

          {showStyleEditor && (
            <div className="mt-3 rounded-lg border border-border bg-background p-4">
              <SubtitleStyler style={subtitleStyle} onChange={setSubtitleStyle} />
            </div>
          )}
        </Section>

        {/* Whisper Model Settings */}
        <Section icon={<Settings2 className="h-5 w-5" />} title="Mô hình Whisper">
          <label className="block text-sm font-medium text-muted-foreground">
            Mô hình chuyển giọng nói thành văn bản
          </label>
          <select
            value={whisperModel}
            onChange={(e) => setWhisperModel(e.target.value)}
            className="mt-1 w-full rounded-lg border border-border bg-muted px-4 py-2.5 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
          >
            <option value="tiny">tiny - Nhanh nhất, độ chính xác thấp nhất (~75MB)</option>
            <option value="base">base - Nhanh, độ chính xác thấp (~142MB)</option>
            <option value="small">small - Tốc độ vừa phải, độ chính xác trung bình (~466MB)</option>
            <option value="medium">medium - Chậm hơn, độ chính xác tốt (~1.5GB)</option>
            <option value="large-v2">large-v2 - Chậm, độ chính xác cao (~3.1GB)</option>
            <option value="large-v3">large-v3 - Chậm, độ chính xác cao (~3.1GB)</option>
            <option value="large-v3-turbo">
              large-v3-turbo - Cân bằng tốc độ &amp; chất lượng (~1.6GB, khuyên dùng)
            </option>
          </select>
          <p className="mt-1 text-xs text-muted-foreground">
            Models are downloaded automatically on first use
          </p>
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
