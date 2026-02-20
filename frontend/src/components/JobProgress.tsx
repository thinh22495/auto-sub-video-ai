"use client";

import type { JobProgressEvent } from "@/lib/types";
import { cn } from "@/lib/utils";
import { CheckCircle2, XCircle, Loader2, Clock } from "lucide-react";

interface JobProgressProps {
  progress: JobProgressEvent | null;
  className?: string;
}

export function JobProgress({ progress, className }: JobProgressProps) {
  if (!progress) {
    return (
      <div className={cn("rounded-xl border border-border bg-card p-6", className)}>
        <div className="flex items-center gap-3 text-muted-foreground">
          <Clock className="h-5 w-5" />
          <span className="text-sm">Waiting for progress updates...</span>
        </div>
      </div>
    );
  }

  const isCompleted = progress.status === "COMPLETED";
  const isFailed = progress.status === "FAILED";
  const isProcessing = progress.status === "PROCESSING";

  return (
    <div className={cn("rounded-xl border border-border bg-card p-6", className)}>
      {/* Status header */}
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          {isCompleted && <CheckCircle2 className="h-5 w-5 text-success" />}
          {isFailed && <XCircle className="h-5 w-5 text-danger" />}
          {isProcessing && <Loader2 className="h-5 w-5 animate-spin text-primary" />}
          <span
            className={cn(
              "text-sm font-semibold",
              isCompleted && "text-success",
              isFailed && "text-danger",
              isProcessing && "text-primary"
            )}
          >
            {progress.status}
          </span>
        </div>
        {progress.eta_seconds != null && progress.eta_seconds > 0 && (
          <span className="text-xs text-muted-foreground">
            ETA: {formatEta(progress.eta_seconds)}
          </span>
        )}
      </div>

      {/* Progress bar */}
      <div className="mb-3">
        <div className="mb-1 flex justify-between text-xs text-muted-foreground">
          <span>
            Step {progress.step_number} / {progress.total_steps}: {progress.step}
          </span>
          <span>{progress.progress_percent.toFixed(1)}%</span>
        </div>
        <div className="h-3 rounded-full bg-muted">
          <div
            className={cn(
              "h-3 rounded-full transition-all duration-300",
              isCompleted && "bg-success",
              isFailed && "bg-danger",
              isProcessing && "bg-primary"
            )}
            style={{ width: `${Math.min(progress.progress_percent, 100)}%` }}
          />
        </div>
      </div>

      {/* Message */}
      <p className="text-sm text-muted-foreground">{progress.message}</p>
    </div>
  );
}

function formatEta(seconds: number): string {
  if (seconds < 60) return `${Math.round(seconds)}s`;
  if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
  return `${Math.round(seconds / 3600)}h ${Math.round((seconds % 3600) / 60)}m`;
}
