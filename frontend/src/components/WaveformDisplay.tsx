"use client";

import { useEffect, useRef, useCallback, useState } from "react";

interface WaveformDisplayProps {
  audioUrl: string | null;
  currentTime: number;
  duration: number;
  onSeek: (time: number) => void;
  segments?: { start: number; end: number; speaker: string | null }[];
  selectedSegmentIndex?: number | null;
  height?: number;
}

const SPEAKER_COLORS = [
  "#60a5fa", // blue
  "#f472b6", // pink
  "#34d399", // green
  "#fbbf24", // yellow
  "#a78bfa", // purple
  "#fb923c", // orange
  "#22d3ee", // cyan
  "#f87171", // red
];

function getSpeakerColor(speaker: string | null, speakerMap: Map<string, number>): string {
  if (!speaker) return "#60a5fa";
  if (!speakerMap.has(speaker)) {
    speakerMap.set(speaker, speakerMap.size);
  }
  return SPEAKER_COLORS[speakerMap.get(speaker)! % SPEAKER_COLORS.length];
}

export default function WaveformDisplay({
  audioUrl,
  currentTime,
  duration,
  onSeek,
  segments = [],
  selectedSegmentIndex = null,
  height = 80,
}: WaveformDisplayProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const audioDataRef = useRef<Float32Array | null>(null);
  const [loading, setLoading] = useState(false);
  const speakerMapRef = useRef(new Map<string, number>());

  // Load and decode audio data
  useEffect(() => {
    if (!audioUrl) return;

    let cancelled = false;
    setLoading(true);

    const loadAudio = async () => {
      try {
        const response = await fetch(audioUrl);
        const arrayBuffer = await response.arrayBuffer();
        const audioContext = new AudioContext();
        const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);

        if (cancelled) return;

        // Downsample to reasonable resolution
        const rawData = audioBuffer.getChannelData(0);
        const samples = Math.min(rawData.length, 4000);
        const blockSize = Math.floor(rawData.length / samples);
        const filteredData = new Float32Array(samples);

        for (let i = 0; i < samples; i++) {
          let sum = 0;
          for (let j = 0; j < blockSize; j++) {
            sum += Math.abs(rawData[i * blockSize + j]);
          }
          filteredData[i] = sum / blockSize;
        }

        audioDataRef.current = filteredData;
        audioContext.close();
      } catch (err) {
        console.error("Failed to load audio for waveform:", err);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    loadAudio();
    return () => { cancelled = true; };
  }, [audioUrl]);

  // Draw waveform
  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    const data = audioDataRef.current;
    if (!canvas || !data) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    const w = canvas.clientWidth;
    const h = canvas.clientHeight;
    canvas.width = w * dpr;
    canvas.height = h * dpr;
    ctx.scale(dpr, dpr);

    // Background
    ctx.fillStyle = "#0f172a";
    ctx.fillRect(0, 0, w, h);

    // Draw segment backgrounds
    const speakerMap = speakerMapRef.current;
    if (segments.length > 0 && duration > 0) {
      for (let i = 0; i < segments.length; i++) {
        const seg = segments[i];
        const x1 = (seg.start / duration) * w;
        const x2 = (seg.end / duration) * w;
        const color = getSpeakerColor(seg.speaker, speakerMap);

        ctx.fillStyle = i === selectedSegmentIndex
          ? color + "40"  // highlighted
          : color + "18"; // subtle
        ctx.fillRect(x1, 0, x2 - x1, h);

        // Segment border
        if (i === selectedSegmentIndex) {
          ctx.strokeStyle = color + "80";
          ctx.lineWidth = 1;
          ctx.strokeRect(x1, 0, x2 - x1, h);
        }
      }
    }

    // Draw waveform bars
    const barWidth = Math.max(1, w / data.length);
    const maxAmp = Math.max(...data) || 1;
    const mid = h / 2;

    for (let i = 0; i < data.length; i++) {
      const x = (i / data.length) * w;
      const amplitude = (data[i] / maxAmp) * mid * 0.9;
      const time = (i / data.length) * duration;

      // Color based on segment speaker at this time
      let barColor = "#475569"; // default gray
      if (segments.length > 0) {
        for (const seg of segments) {
          if (time >= seg.start && time <= seg.end) {
            barColor = getSpeakerColor(seg.speaker, speakerMap);
            break;
          }
        }
      }

      // Dim past waveform, brighten current
      if (time < currentTime) {
        ctx.fillStyle = barColor + "90";
      } else {
        ctx.fillStyle = barColor + "60";
      }

      ctx.fillRect(x, mid - amplitude, barWidth, amplitude * 2);
    }

    // Playhead
    if (duration > 0) {
      const playheadX = (currentTime / duration) * w;
      ctx.strokeStyle = "#ffffff";
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(playheadX, 0);
      ctx.lineTo(playheadX, h);
      ctx.stroke();

      // Time indicator
      ctx.fillStyle = "#ffffff";
      ctx.font = "10px monospace";
      const timeStr = formatTime(currentTime);
      const textWidth = ctx.measureText(timeStr).width;
      const textX = Math.min(playheadX + 4, w - textWidth - 4);
      ctx.fillText(timeStr, textX, 12);
    }
  }, [currentTime, duration, segments, selectedSegmentIndex]);

  useEffect(() => {
    draw();
  }, [draw, loading]);

  // Also redraw on resize
  useEffect(() => {
    const observer = new ResizeObserver(() => draw());
    if (containerRef.current) observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, [draw]);

  const handleClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas || duration <= 0) return;

    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const time = (x / rect.width) * duration;
    onSeek(Math.max(0, Math.min(duration, time)));
  };

  return (
    <div ref={containerRef} className="relative w-full" style={{ height }}>
      {loading && (
        <div className="absolute inset-0 flex items-center justify-center bg-card/80 text-xs text-muted-foreground">
          Đang tải sóng âm...
        </div>
      )}
      <canvas
        ref={canvasRef}
        className="h-full w-full cursor-crosshair rounded-lg"
        onClick={handleClick}
      />
    </div>
  );
}

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  const ms = Math.floor((seconds % 1) * 100);
  return `${m}:${s.toString().padStart(2, "0")}.${ms.toString().padStart(2, "0")}`;
}
