"use client";

import { useRef, useCallback, useState } from "react";
import type { SubtitleSegment } from "@/lib/types";

interface SubtitleTimelineProps {
  segments: SubtitleSegment[];
  duration: number;
  currentTime: number;
  selectedIndex: number | null;
  onSelect: (index: number) => void;
  onSeek: (time: number) => void;
  onSegmentTimeChange: (index: number, start: number, end: number) => void;
}

const SPEAKER_COLORS = [
  "#60a5fa", "#f472b6", "#34d399", "#fbbf24",
  "#a78bfa", "#fb923c", "#22d3ee", "#f87171",
];

const TRACK_HEIGHT = 36;
const MIN_SEGMENT_DURATION = 0.1; // seconds

export default function SubtitleTimeline({
  segments,
  duration,
  currentTime,
  selectedIndex,
  onSelect,
  onSeek,
  onSegmentTimeChange,
}: SubtitleTimelineProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [dragging, setDragging] = useState<{
    segIndex: number;
    edge: "start" | "end" | "move";
    startX: number;
    origStart: number;
    origEnd: number;
  } | null>(null);

  const speakerMap = useRef(new Map<string, number>());

  function getSpeakerColor(speaker: string | null): string {
    if (!speaker) return SPEAKER_COLORS[0];
    if (!speakerMap.current.has(speaker)) {
      speakerMap.current.set(speaker, speakerMap.current.size);
    }
    return SPEAKER_COLORS[speakerMap.current.get(speaker)! % SPEAKER_COLORS.length];
  }

  const timeToX = useCallback(
    (time: number) => {
      if (!containerRef.current || duration <= 0) return 0;
      return (time / duration) * containerRef.current.clientWidth;
    },
    [duration]
  );

  const xToTime = useCallback(
    (x: number) => {
      if (!containerRef.current || duration <= 0) return 0;
      return (x / containerRef.current.clientWidth) * duration;
    },
    [duration]
  );

  const handleMouseDown = (
    e: React.MouseEvent,
    segIndex: number,
    edge: "start" | "end" | "move"
  ) => {
    e.stopPropagation();
    e.preventDefault();
    const seg = segments[segIndex];
    setDragging({
      segIndex,
      edge,
      startX: e.clientX,
      origStart: seg.start,
      origEnd: seg.end,
    });
    onSelect(segIndex);
  };

  const handleMouseMove = useCallback(
    (e: React.MouseEvent) => {
      if (!dragging || !containerRef.current) return;

      const dx = e.clientX - dragging.startX;
      const dt = xToTime(dx) - xToTime(0);
      const seg = segments[dragging.segIndex];

      let newStart = dragging.origStart;
      let newEnd = dragging.origEnd;

      if (dragging.edge === "start") {
        newStart = Math.max(0, dragging.origStart + dt);
        newStart = Math.min(newStart, newEnd - MIN_SEGMENT_DURATION);
      } else if (dragging.edge === "end") {
        newEnd = Math.min(duration, dragging.origEnd + dt);
        newEnd = Math.max(newEnd, newStart + MIN_SEGMENT_DURATION);
      } else {
        // Move entire segment
        const segDur = dragging.origEnd - dragging.origStart;
        newStart = Math.max(0, dragging.origStart + dt);
        newEnd = newStart + segDur;
        if (newEnd > duration) {
          newEnd = duration;
          newStart = newEnd - segDur;
        }
      }

      onSegmentTimeChange(
        dragging.segIndex,
        Math.round(newStart * 1000) / 1000,
        Math.round(newEnd * 1000) / 1000
      );
    },
    [dragging, duration, segments, xToTime, onSegmentTimeChange]
  );

  const handleMouseUp = () => {
    setDragging(null);
  };

  const handleTrackClick = (e: React.MouseEvent) => {
    if (dragging) return;
    const rect = containerRef.current?.getBoundingClientRect();
    if (!rect) return;
    const x = e.clientX - rect.left;
    onSeek(xToTime(x));
  };

  // Generate time markers
  const markers: number[] = [];
  if (duration > 0) {
    const interval = duration <= 60 ? 5 : duration <= 300 ? 15 : 30;
    for (let t = 0; t <= duration; t += interval) {
      markers.push(t);
    }
  }

  return (
    <div
      className="relative select-none"
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
    >
      {/* Time ruler */}
      <div className="relative h-5 border-b border-border bg-card text-[10px] text-muted-foreground">
        {markers.map((t) => (
          <div
            key={t}
            className="absolute top-0 flex h-full flex-col justify-end"
            style={{ left: `${(t / duration) * 100}%` }}
          >
            <span className="translate-x-[-50%] px-0.5">{formatTimeShort(t)}</span>
            <div className="mx-auto h-1 w-px bg-border" />
          </div>
        ))}
      </div>

      {/* Segment track */}
      <div
        ref={containerRef}
        className="relative cursor-crosshair bg-muted/30"
        style={{ height: TRACK_HEIGHT }}
        onClick={handleTrackClick}
      >
        {segments.map((seg, i) => {
          const left = duration > 0 ? (seg.start / duration) * 100 : 0;
          const width = duration > 0 ? ((seg.end - seg.start) / duration) * 100 : 0;
          const color = getSpeakerColor(seg.speaker);
          const isSelected = i === selectedIndex;

          return (
            <div
              key={i}
              className="absolute top-1 flex items-center overflow-hidden rounded-sm text-[9px] text-white"
              style={{
                left: `${left}%`,
                width: `${Math.max(width, 0.2)}%`,
                height: TRACK_HEIGHT - 8,
                backgroundColor: color + (isSelected ? "cc" : "88"),
                border: isSelected ? `1px solid ${color}` : "1px solid transparent",
                zIndex: isSelected ? 10 : 1,
              }}
              onClick={(e) => {
                e.stopPropagation();
                onSelect(i);
              }}
              onMouseDown={(e) => handleMouseDown(e, i, "move")}
            >
              {/* Left drag handle */}
              <div
                className="absolute left-0 top-0 h-full w-1.5 cursor-col-resize hover:bg-white/30"
                onMouseDown={(e) => handleMouseDown(e, i, "start")}
              />
              {/* Segment label */}
              <span className="truncate px-1.5 leading-none">
                {seg.text.slice(0, 30)}
              </span>
              {/* Right drag handle */}
              <div
                className="absolute right-0 top-0 h-full w-1.5 cursor-col-resize hover:bg-white/30"
                onMouseDown={(e) => handleMouseDown(e, i, "end")}
              />
            </div>
          );
        })}

        {/* Playhead */}
        {duration > 0 && (
          <div
            className="absolute top-0 z-20 h-full w-0.5 bg-white"
            style={{ left: `${(currentTime / duration) * 100}%` }}
          />
        )}
      </div>
    </div>
  );
}

function formatTimeShort(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}
