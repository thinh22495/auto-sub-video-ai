"use client";

import { useParams, useRouter } from "next/navigation";
import { useJob } from "@/hooks/useJob";
import { api } from "@/lib/api-client";
import type { SubtitleSegment, ParsedSubtitles, SubtitleVersion } from "@/lib/types";
import WaveformDisplay from "@/components/WaveformDisplay";
import SubtitleTimeline from "@/components/SubtitleTimeline";
import { useState, useEffect, useCallback, useRef } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  Save,
  Undo2,
  Redo2,
  Loader2,
  Play,
  Pause,
  SkipBack,
  SkipForward,
  Scissors,
  Merge,
  Plus,
  Trash2,
  History,
  X,
  RotateCcw,
  Volume2,
} from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

// Undo/redo history
interface HistoryEntry {
  segments: SubtitleSegment[];
  description: string;
}

export default function SubtitleEditorPage() {
  const params = useParams();
  const router = useRouter();
  const jobId = params.id as string;
  const { job, loading: jobLoading } = useJob(jobId);

  // Segments state
  const [segments, setSegments] = useState<SubtitleSegment[]>([]);
  const [originalSegments, setOriginalSegments] = useState<SubtitleSegment[]>([]);
  const [loadingSubtitles, setLoadingSubtitles] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Editor state
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null);
  const [hasChanges, setHasChanges] = useState(false);

  // Undo/redo
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [historyIndex, setHistoryIndex] = useState(-1);

  // Audio/video state
  const videoRef = useRef<HTMLVideoElement>(null);
  const [playing, setPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);

  // Version history panel
  const [showVersions, setShowVersions] = useState(false);
  const [versions, setVersions] = useState<SubtitleVersion[]>([]);

  // Load subtitles
  useEffect(() => {
    if (!jobId) return;
    const loadSubtitles = async () => {
      setLoadingSubtitles(true);
      try {
        const data = await api.get<ParsedSubtitles>(`/jobs/${jobId}/subtitles/parsed`);
        setSegments(data.segments);
        setOriginalSegments(JSON.parse(JSON.stringify(data.segments)));
        pushHistory(data.segments, "Loaded original");
      } catch (err: any) {
        setError(err.message);
      } finally {
        setLoadingSubtitles(false);
      }
    };
    loadSubtitles();
  }, [jobId]);

  // Track changes
  useEffect(() => {
    setHasChanges(JSON.stringify(segments) !== JSON.stringify(originalSegments));
  }, [segments, originalSegments]);

  // Video time sync
  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    const onTimeUpdate = () => setCurrentTime(video.currentTime);
    const onLoaded = () => setDuration(video.duration);
    const onPlay = () => setPlaying(true);
    const onPause = () => setPlaying(false);

    video.addEventListener("timeupdate", onTimeUpdate);
    video.addEventListener("loadedmetadata", onLoaded);
    video.addEventListener("play", onPlay);
    video.addEventListener("pause", onPause);

    return () => {
      video.removeEventListener("timeupdate", onTimeUpdate);
      video.removeEventListener("loadedmetadata", onLoaded);
      video.removeEventListener("play", onPlay);
      video.removeEventListener("pause", onPause);
    };
  }, []);

  // Auto-scroll to selected segment in the list
  useEffect(() => {
    if (selectedIndex === null) return;
    const el = document.getElementById(`seg-${selectedIndex}`);
    el?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [selectedIndex]);

  // Find active segment from current time
  useEffect(() => {
    if (playing && segments.length > 0) {
      const idx = segments.findIndex(
        (s) => currentTime >= s.start && currentTime <= s.end
      );
      if (idx !== -1 && idx !== selectedIndex) {
        setSelectedIndex(idx);
      }
    }
  }, [currentTime, playing, segments]);

  // --- History management ---
  const pushHistory = (segs: SubtitleSegment[], desc: string) => {
    const newEntry: HistoryEntry = {
      segments: JSON.parse(JSON.stringify(segs)),
      description: desc,
    };
    setHistory((prev) => {
      const trimmed = prev.slice(0, historyIndex + 1);
      return [...trimmed, newEntry];
    });
    setHistoryIndex((prev) => prev + 1);
  };

  const undo = useCallback(() => {
    if (historyIndex <= 0) return;
    const newIdx = historyIndex - 1;
    setHistoryIndex(newIdx);
    setSegments(JSON.parse(JSON.stringify(history[newIdx].segments)));
  }, [history, historyIndex]);

  const redo = useCallback(() => {
    if (historyIndex >= history.length - 1) return;
    const newIdx = historyIndex + 1;
    setHistoryIndex(newIdx);
    setSegments(JSON.parse(JSON.stringify(history[newIdx].segments)));
  }, [history, historyIndex]);

  // --- Segment operations ---
  const updateSegment = (index: number, updates: Partial<SubtitleSegment>) => {
    setSegments((prev) => {
      const next = [...prev];
      next[index] = { ...next[index], ...updates };
      return next;
    });
  };

  const commitSegmentEdit = (description: string) => {
    pushHistory(segments, description);
  };

  const handleSegmentTimeChange = (index: number, start: number, end: number) => {
    updateSegment(index, { start, end });
  };

  const splitSegment = () => {
    if (selectedIndex === null) return;
    const seg = segments[selectedIndex];
    const splitTime = currentTime > seg.start && currentTime < seg.end
      ? currentTime
      : (seg.start + seg.end) / 2;

    const words = seg.text.split(" ");
    const midWord = Math.ceil(words.length / 2);
    const text1 = words.slice(0, midWord).join(" ");
    const text2 = words.slice(midWord).join(" ");

    const newSegments = [...segments];
    newSegments.splice(selectedIndex, 1, {
      ...seg,
      end: splitTime,
      text: text1,
      index: seg.index,
    }, {
      ...seg,
      start: splitTime,
      text: text2,
      index: seg.index + 1,
    });

    // Re-index
    newSegments.forEach((s, i) => (s.index = i + 1));
    setSegments(newSegments);
    pushHistory(newSegments, "Split segment");
  };

  const mergeWithNext = () => {
    if (selectedIndex === null || selectedIndex >= segments.length - 1) return;
    const seg = segments[selectedIndex];
    const next = segments[selectedIndex + 1];

    const newSegments = [...segments];
    newSegments.splice(selectedIndex, 2, {
      ...seg,
      end: next.end,
      text: `${seg.text} ${next.text}`,
    });

    newSegments.forEach((s, i) => (s.index = i + 1));
    setSegments(newSegments);
    pushHistory(newSegments, "Merge segments");
  };

  const addSegment = () => {
    const insertAfter = selectedIndex ?? segments.length - 1;
    const prevEnd = insertAfter >= 0 ? segments[insertAfter].end : 0;
    const nextStart = insertAfter < segments.length - 1 ? segments[insertAfter + 1].start : prevEnd + 2;
    const newStart = prevEnd + 0.1;
    const newEnd = Math.min(newStart + 2, nextStart - 0.05);

    if (newEnd <= newStart) return;

    const newSegments = [...segments];
    newSegments.splice(insertAfter + 1, 0, {
      index: insertAfter + 2,
      start: Math.round(newStart * 1000) / 1000,
      end: Math.round(newEnd * 1000) / 1000,
      text: "",
      speaker: null,
    });

    newSegments.forEach((s, i) => (s.index = i + 1));
    setSegments(newSegments);
    setSelectedIndex(insertAfter + 1);
    pushHistory(newSegments, "Add segment");
  };

  const deleteSegment = () => {
    if (selectedIndex === null) return;
    const newSegments = segments.filter((_, i) => i !== selectedIndex);
    newSegments.forEach((s, i) => (s.index = i + 1));
    setSegments(newSegments);
    setSelectedIndex(null);
    pushHistory(newSegments, "Delete segment");
  };

  // --- Save ---
  const handleSave = async () => {
    setSaving(true);
    try {
      await api.put(`/jobs/${jobId}/subtitles`, {
        segments,
        format: "srt",
        description: `Edited ${segments.length} segments`,
      });
      setOriginalSegments(JSON.parse(JSON.stringify(segments)));
    } catch (err: any) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  // --- Version history ---
  const loadVersions = async () => {
    try {
      const data = await api.get<SubtitleVersion[]>(`/jobs/${jobId}/subtitles/versions`);
      setVersions(data);
      setShowVersions(true);
    } catch (err: any) {
      console.error("Failed to load versions:", err);
    }
  };

  const restoreVersion = async (versionId: string) => {
    try {
      await api.post(`/jobs/${jobId}/subtitles/versions/${versionId}/restore`);
      // Reload subtitles
      const data = await api.get<ParsedSubtitles>(`/jobs/${jobId}/subtitles/parsed`);
      setSegments(data.segments);
      pushHistory(data.segments, "Restored version");
      setShowVersions(false);
    } catch (err: any) {
      console.error("Failed to restore version:", err);
    }
  };

  // --- Playback ---
  const togglePlay = () => {
    const video = videoRef.current;
    if (!video) return;
    if (playing) video.pause();
    else video.play();
  };

  const seekTo = (time: number) => {
    const video = videoRef.current;
    if (video) video.currentTime = time;
    setCurrentTime(time);
  };

  const skip = (delta: number) => {
    seekTo(Math.max(0, Math.min(duration, currentTime + delta)));
  };

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;

      if (e.key === " ") {
        e.preventDefault();
        togglePlay();
      } else if (e.key === "ArrowLeft") {
        skip(-5);
      } else if (e.key === "ArrowRight") {
        skip(5);
      } else if (e.ctrlKey && e.key === "z") {
        e.preventDefault();
        undo();
      } else if (e.ctrlKey && e.key === "y") {
        e.preventDefault();
        redo();
      } else if (e.ctrlKey && e.key === "s") {
        e.preventDefault();
        handleSave();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [playing, currentTime, duration, undo, redo]);

  // --- Loading states ---
  if (jobLoading || loadingSubtitles) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (error || !job) {
    return (
      <div className="space-y-4">
        <div className="rounded-lg border border-danger/30 bg-danger/10 p-4 text-sm text-danger">
          {error || "Job not found"}
        </div>
        <Link href="/" className="text-sm text-primary hover:underline">
          Back to Dashboard
        </Link>
      </div>
    );
  }

  const selectedSeg = selectedIndex !== null ? segments[selectedIndex] : null;

  return (
    <div className="flex h-[calc(100vh-4rem)] flex-col">
      {/* Header toolbar */}
      <div className="flex items-center justify-between border-b border-border bg-card px-4 py-2">
        <div className="flex items-center gap-3">
          <Link
            href={`/jobs/${jobId}`}
            className="rounded-lg p-1.5 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
          >
            <ArrowLeft className="h-4 w-4" />
          </Link>
          <div>
            <h1 className="text-sm font-semibold text-foreground">
              {job.input_filename}
            </h1>
            <p className="text-[10px] text-muted-foreground">
              {segments.length} đoạn
              {hasChanges && " (thay đổi chưa lưu)"}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-1">
          <button
            onClick={undo}
            disabled={historyIndex <= 0}
            className="rounded p-1.5 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground disabled:opacity-30"
            title="Hoàn tác (Ctrl+Z)"
          >
            <Undo2 className="h-4 w-4" />
          </button>
          <button
            onClick={redo}
            disabled={historyIndex >= history.length - 1}
            className="rounded p-1.5 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground disabled:opacity-30"
            title="Làm lại (Ctrl+Y)"
          >
            <Redo2 className="h-4 w-4" />
          </button>

          <div className="mx-2 h-4 w-px bg-border" />

          <button
            onClick={splitSegment}
            disabled={selectedIndex === null}
            className="flex items-center gap-1 rounded px-2 py-1.5 text-xs text-muted-foreground transition-colors hover:bg-muted hover:text-foreground disabled:opacity-30"
            title="Tách đoạn tại vị trí phát"
          >
            <Scissors className="h-3.5 w-3.5" />
            Tách
          </button>
          <button
            onClick={mergeWithNext}
            disabled={selectedIndex === null || selectedIndex >= segments.length - 1}
            className="flex items-center gap-1 rounded px-2 py-1.5 text-xs text-muted-foreground transition-colors hover:bg-muted hover:text-foreground disabled:opacity-30"
            title="Gộp với đoạn kế tiếp"
          >
            <Merge className="h-3.5 w-3.5" />
            Gộp
          </button>
          <button
            onClick={addSegment}
            className="flex items-center gap-1 rounded px-2 py-1.5 text-xs text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
            title="Thêm đoạn mới"
          >
            <Plus className="h-3.5 w-3.5" />
            Thêm
          </button>
          <button
            onClick={deleteSegment}
            disabled={selectedIndex === null}
            className="flex items-center gap-1 rounded px-2 py-1.5 text-xs text-danger transition-colors hover:bg-danger/10 disabled:opacity-30"
            title="Xóa đoạn"
          >
            <Trash2 className="h-3.5 w-3.5" />
          </button>

          <div className="mx-2 h-4 w-px bg-border" />

          <button
            onClick={loadVersions}
            className="flex items-center gap-1 rounded px-2 py-1.5 text-xs text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
          >
            <History className="h-3.5 w-3.5" />
            Phiên bản
          </button>
          <button
            onClick={handleSave}
            disabled={saving || !hasChanges}
            className="flex items-center gap-1.5 rounded-lg bg-primary px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-primary/90 disabled:opacity-50"
          >
            {saving ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Save className="h-3.5 w-3.5" />}
            Lưu
          </button>
        </div>
      </div>

      {/* Main content: video + segment list */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left: Video player + waveform + timeline */}
        <div className="flex w-1/2 flex-col border-r border-border">
          {/* Video */}
          <div className="relative bg-black">
            <video
              ref={videoRef}
              className="aspect-video w-full"
              src={`${API_BASE}/files/video/stream?path=${encodeURIComponent(job.input_path)}`}
              preload="metadata"
            />
            {/* Subtitle overlay */}
            {selectedSeg && currentTime >= selectedSeg.start && currentTime <= selectedSeg.end && (
              <div className="absolute bottom-8 left-1/2 -translate-x-1/2 rounded bg-black/80 px-3 py-1 text-center text-sm text-white">
                {selectedSeg.speaker && (
                  <span className="text-primary">[{selectedSeg.speaker}] </span>
                )}
                {selectedSeg.text}
              </div>
            )}
          </div>

          {/* Playback controls */}
          <div className="flex items-center gap-2 border-b border-border bg-card px-3 py-1.5">
            <button
              onClick={() => skip(-5)}
              className="rounded p-1 text-muted-foreground hover:text-foreground"
            >
              <SkipBack className="h-4 w-4" />
            </button>
            <button
              onClick={togglePlay}
              className="rounded-full bg-primary p-1.5 text-white hover:bg-primary/90"
            >
              {playing ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
            </button>
            <button
              onClick={() => skip(5)}
              className="rounded p-1 text-muted-foreground hover:text-foreground"
            >
              <SkipForward className="h-4 w-4" />
            </button>
            <span className="ml-2 font-mono text-xs text-muted-foreground">
              {formatTimeFull(currentTime)} / {formatTimeFull(duration)}
            </span>
          </div>

          {/* Waveform */}
          <WaveformDisplay
            audioUrl={`${API_BASE}/jobs/${jobId}/audio`}
            currentTime={currentTime}
            duration={duration}
            onSeek={seekTo}
            segments={segments}
            selectedSegmentIndex={selectedIndex}
            height={60}
          />

          {/* Timeline */}
          <SubtitleTimeline
            segments={segments}
            duration={duration}
            currentTime={currentTime}
            selectedIndex={selectedIndex}
            onSelect={setSelectedIndex}
            onSeek={seekTo}
            onSegmentTimeChange={(idx, start, end) => {
              handleSegmentTimeChange(idx, start, end);
            }}
          />
        </div>

        {/* Right: Segment list / editor */}
        <div className="flex w-1/2 flex-col">
          {/* Segment list */}
          <div className="flex-1 overflow-y-auto">
            {segments.map((seg, i) => (
              <div
                key={i}
                id={`seg-${i}`}
                className={`border-b border-border px-3 py-2 transition-colors cursor-pointer ${
                  i === selectedIndex
                    ? "bg-primary/10 border-l-2 border-l-primary"
                    : "hover:bg-muted/50"
                }`}
                onClick={() => {
                  setSelectedIndex(i);
                  seekTo(seg.start);
                }}
              >
                <div className="mb-1 flex items-center gap-2 text-[10px] text-muted-foreground">
                  <span className="font-mono">#{seg.index}</span>
                  <span className="font-mono">
                    {formatTimeFull(seg.start)} → {formatTimeFull(seg.end)}
                  </span>
                  <span className="text-muted-foreground/60">
                    ({(seg.end - seg.start).toFixed(1)}s)
                  </span>
                  {seg.speaker && (
                    <span className="rounded bg-primary/20 px-1.5 py-0.5 text-primary">
                      {seg.speaker}
                    </span>
                  )}
                  <span className="ml-auto text-muted-foreground/50">
                    {seg.text.length} chars
                  </span>
                </div>

                {i === selectedIndex ? (
                  <div className="space-y-1.5">
                    <textarea
                      value={seg.text}
                      onChange={(e) => updateSegment(i, { text: e.target.value })}
                      onBlur={() => commitSegmentEdit("Edit text")}
                      className="w-full resize-none rounded border border-border bg-background px-2 py-1 text-sm text-foreground focus:border-primary focus:outline-none"
                      rows={2}
                    />
                    <div className="flex items-center gap-2">
                      <label className="text-[10px] text-muted-foreground">Bắt đầu:</label>
                      <input
                        type="number"
                        step="0.1"
                        value={seg.start}
                        onChange={(e) => updateSegment(i, { start: parseFloat(e.target.value) || 0 })}
                        onBlur={() => commitSegmentEdit("Edit timing")}
                        className="w-20 rounded border border-border bg-background px-1.5 py-0.5 text-xs text-foreground"
                      />
                      <label className="text-[10px] text-muted-foreground">Kết thúc:</label>
                      <input
                        type="number"
                        step="0.1"
                        value={seg.end}
                        onChange={(e) => updateSegment(i, { end: parseFloat(e.target.value) || 0 })}
                        onBlur={() => commitSegmentEdit("Edit timing")}
                        className="w-20 rounded border border-border bg-background px-1.5 py-0.5 text-xs text-foreground"
                      />
                      <label className="text-[10px] text-muted-foreground">Người nói:</label>
                      <input
                        type="text"
                        value={seg.speaker || ""}
                        onChange={(e) => updateSegment(i, { speaker: e.target.value || null })}
                        onBlur={() => commitSegmentEdit("Edit speaker")}
                        className="w-24 rounded border border-border bg-background px-1.5 py-0.5 text-xs text-foreground"
                        placeholder="Không có"
                      />
                    </div>
                  </div>
                ) : (
                  <p className="text-sm text-foreground">{seg.text}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Version history panel */}
      {showVersions && (
        <div className="absolute right-0 top-0 z-30 flex h-full w-80 flex-col border-l border-border bg-card shadow-xl">
          <div className="flex items-center justify-between border-b border-border px-4 py-3">
            <h3 className="text-sm font-semibold text-foreground">Lịch sử phiên bản</h3>
            <button
              onClick={() => setShowVersions(false)}
              className="rounded p-1 text-muted-foreground hover:text-foreground"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
          <div className="flex-1 overflow-y-auto">
            {versions.length === 0 ? (
              <p className="p-4 text-center text-sm text-muted-foreground">
                Chưa có phiên bản nào
              </p>
            ) : (
              versions.map((v) => (
                <div
                  key={v.id}
                  className="border-b border-border px-4 py-3 hover:bg-muted/50"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-foreground">
                      v{v.version}
                    </span>
                    <button
                      onClick={() => restoreVersion(v.id)}
                      className="flex items-center gap-1 rounded px-2 py-1 text-xs text-primary hover:bg-primary/10"
                    >
                      <RotateCcw className="h-3 w-3" />
                      Khôi phục
                    </button>
                  </div>
                  <p className="text-xs text-muted-foreground">{v.description}</p>
                  {v.created_at && (
                    <p className="text-[10px] text-muted-foreground/60">
                      {new Date(v.created_at).toLocaleString()}
                    </p>
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function formatTimeFull(seconds: number): string {
  if (!seconds || isNaN(seconds)) return "0:00.000";
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  const ms = Math.floor((seconds % 1) * 1000);
  return `${m}:${s.toString().padStart(2, "0")}.${ms.toString().padStart(3, "0")}`;
}
