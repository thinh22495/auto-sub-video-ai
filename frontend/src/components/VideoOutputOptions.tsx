"use client";

import { useState } from "react";
import type { VideoOutputSettings } from "@/lib/types";
import { ChevronDown, ChevronUp } from "lucide-react";

interface VideoOutputOptionsProps {
  settings: VideoOutputSettings;
  onChange: (settings: VideoOutputSettings) => void;
}

const FORMAT_OPTIONS = [
  { value: "mp4", label: "MP4", desc: "Phổ biến nhất, tương thích cao" },
  { value: "mkv", label: "MKV", desc: "Hỗ trợ nhiều codec, linh hoạt" },
  { value: "webm", label: "WebM", desc: "Tối ưu cho web (VP9 + Opus)" },
];

const CODEC_OPTIONS = [
  { value: "", label: "Tự động (H.264)", desc: "Tương thích tốt nhất" },
  { value: "h264", label: "H.264", desc: "Phổ biến, nhanh, GPU hỗ trợ" },
  { value: "h265", label: "H.265 / HEVC", desc: "Chất lượng cao hơn, file nhỏ hơn" },
  { value: "vp9", label: "VP9", desc: "Mã nguồn mở, dùng cho WebM" },
];

const PRESET_OPTIONS = [
  { value: "ultrafast", label: "Cực nhanh (ultrafast)" },
  { value: "veryfast", label: "Rất nhanh (veryfast)" },
  { value: "fast", label: "Nhanh (fast)" },
  { value: "medium", label: "Cân bằng (medium)" },
  { value: "slow", label: "Chậm (slow)" },
  { value: "veryslow", label: "Rất chậm (veryslow)" },
];

const RESOLUTION_OPTIONS = [
  { value: "", label: "Giữ nguyên" },
  { value: "1080p", label: "1080p (Full HD)" },
  { value: "720p", label: "720p (HD)" },
  { value: "480p", label: "480p (SD)" },
];

const AUDIO_OPTIONS = [
  { value: "copy", label: "Giữ nguyên (copy)" },
  { value: "aac", label: "AAC" },
  { value: "opus", label: "Opus" },
];

const FPS_OPTIONS = [
  { value: "", label: "Giữ nguyên" },
  { value: "60", label: "60 FPS" },
  { value: "30", label: "30 FPS" },
  { value: "24", label: "24 FPS" },
];

function getCrfLabel(crf: number): string {
  if (crf <= 15) return "Gần lossless";
  if (crf <= 18) return "Chất lượng cao";
  if (crf <= 23) return "Cân bằng";
  if (crf <= 28) return "File nhỏ";
  return "Nén mạnh";
}

// Codec tương thích với từng container
function getCompatibleCodecs(format: string) {
  switch (format) {
    case "webm": return ["vp9"];
    case "mp4": return ["", "h264", "h265"];
    case "mkv": return ["", "h264", "h265", "vp9"];
    default: return ["", "h264", "h265", "vp9"];
  }
}

function getCompatibleAudio(format: string) {
  switch (format) {
    case "webm": return ["opus"];
    case "mp4": return ["copy", "aac"];
    case "mkv": return ["copy", "aac", "opus"];
    default: return ["copy", "aac", "opus"];
  }
}

export function VideoOutputOptions({ settings, onChange }: VideoOutputOptionsProps) {
  const [showAdvanced, setShowAdvanced] = useState(false);

  const update = (partial: Partial<VideoOutputSettings>) => {
    const next = { ...settings, ...partial };

    // Tự động điều chỉnh khi đổi format
    if (partial.output_format) {
      const compatCodecs = getCompatibleCodecs(partial.output_format);
      const compatAudio = getCompatibleAudio(partial.output_format);

      if (partial.output_format === "webm") {
        next.video_codec = "vp9";
        next.audio_codec = "opus";
      } else {
        if (next.video_codec && !compatCodecs.includes(next.video_codec)) {
          next.video_codec = null;
        }
        if (!compatAudio.includes(next.audio_codec)) {
          next.audio_codec = compatAudio[0];
        }
      }
    }

    onChange(next);
  };

  const isWebm = settings.output_format === "webm";
  const compatCodecs = getCompatibleCodecs(settings.output_format);
  const compatAudio = getCompatibleAudio(settings.output_format);

  return (
    <div className="space-y-4">
      {/* Định dạng đầu ra */}
      <div>
        <label className="mb-1.5 block text-sm font-medium text-muted-foreground">
          Định dạng đầu ra
        </label>
        <div className="flex gap-3">
          {FORMAT_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              type="button"
              onClick={() => update({ output_format: opt.value })}
              className={`rounded-lg border px-4 py-2 text-sm font-medium uppercase transition-colors ${
                settings.output_format === opt.value
                  ? "border-primary bg-primary/10 text-primary"
                  : "border-border bg-muted text-muted-foreground hover:border-foreground/30"
              }`}
              title={opt.desc}
            >
              .{opt.label}
            </button>
          ))}
        </div>
      </div>

      {/* Codec video */}
      <div>
        <label className="mb-1.5 block text-sm font-medium text-muted-foreground">
          Codec video
        </label>
        <select
          value={settings.video_codec || ""}
          onChange={(e) => update({ video_codec: e.target.value || null })}
          disabled={isWebm}
          className="w-full rounded-lg border border-border bg-muted px-4 py-2.5 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary disabled:opacity-50"
        >
          {CODEC_OPTIONS.filter((opt) => compatCodecs.includes(opt.value)).map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label} — {opt.desc}
            </option>
          ))}
        </select>
      </div>

      {/* Chất lượng CRF */}
      <div>
        <label className="mb-1.5 block text-sm font-medium text-muted-foreground">
          Chất lượng (CRF): {settings.crf}
          <span className="ml-2 text-xs font-normal text-accent">
            {getCrfLabel(settings.crf)}
          </span>
        </label>
        <input
          type="range"
          min={0}
          max={51}
          value={settings.crf}
          onChange={(e) => update({ crf: parseInt(e.target.value) })}
          className="w-full accent-primary"
        />
        <div className="mt-0.5 flex justify-between text-[10px] text-muted-foreground">
          <span>0 (lossless)</span>
          <span>18 (cao)</span>
          <span>23 (TB)</span>
          <span>28 (nhỏ)</span>
          <span>51 (thấp)</span>
        </div>
      </div>

      {/* Tốc độ encode */}
      <div>
        <label className="mb-1.5 block text-sm font-medium text-muted-foreground">
          Tốc độ mã hóa
        </label>
        <select
          value={settings.preset}
          onChange={(e) => update({ preset: e.target.value })}
          className="w-full rounded-lg border border-border bg-muted px-4 py-2.5 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
        >
          {PRESET_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
        <p className="mt-1 text-xs text-muted-foreground">
          Chậm hơn = chất lượng tốt hơn với cùng CRF, nhưng mất nhiều thời gian hơn
        </p>
      </div>

      {/* Nâng cao */}
      <button
        type="button"
        onClick={() => setShowAdvanced(!showAdvanced)}
        className="flex items-center gap-1.5 text-xs text-muted-foreground transition-colors hover:text-foreground"
      >
        {showAdvanced ? (
          <ChevronUp className="h-3.5 w-3.5" />
        ) : (
          <ChevronDown className="h-3.5 w-3.5" />
        )}
        {showAdvanced ? "Ẩn" : "Hiện"} tùy chọn nâng cao
      </button>

      {showAdvanced && (
        <div className="space-y-3 rounded-lg border border-border bg-background p-4">
          {/* Độ phân giải */}
          <div>
            <label className="mb-1 block text-xs font-medium text-muted-foreground">
              Độ phân giải
            </label>
            <select
              value={settings.resolution || ""}
              onChange={(e) => update({ resolution: e.target.value || null })}
              className="w-full rounded-lg border border-border bg-muted px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none"
            >
              {RESOLUTION_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>

          {/* Audio */}
          <div>
            <label className="mb-1 block text-xs font-medium text-muted-foreground">
              Audio codec
            </label>
            <select
              value={settings.audio_codec}
              onChange={(e) => update({ audio_codec: e.target.value })}
              disabled={isWebm}
              className="w-full rounded-lg border border-border bg-muted px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none disabled:opacity-50"
            >
              {AUDIO_OPTIONS.filter((opt) => compatAudio.includes(opt.value)).map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>

          {/* Audio bitrate - chỉ hiện khi không copy */}
          {settings.audio_codec !== "copy" && (
            <div>
              <label className="mb-1 block text-xs font-medium text-muted-foreground">
                Audio bitrate: {settings.audio_bitrate} kbps
              </label>
              <input
                type="range"
                min={64}
                max={320}
                step={32}
                value={settings.audio_bitrate}
                onChange={(e) => update({ audio_bitrate: parseInt(e.target.value) })}
                className="w-full accent-primary"
              />
              <div className="mt-0.5 flex justify-between text-[10px] text-muted-foreground">
                <span>64</span>
                <span>128</span>
                <span>192</span>
                <span>256</span>
                <span>320</span>
              </div>
            </div>
          )}

          {/* FPS */}
          <div>
            <label className="mb-1 block text-xs font-medium text-muted-foreground">
              Tốc độ khung hình (FPS)
            </label>
            <select
              value={settings.fps?.toString() || ""}
              onChange={(e) => update({ fps: e.target.value ? parseInt(e.target.value) : null })}
              className="w-full rounded-lg border border-border bg-muted px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none"
            >
              {FPS_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
        </div>
      )}
    </div>
  );
}
