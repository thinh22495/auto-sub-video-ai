"use client";

import { useState, useEffect, useCallback } from "react";
import { api } from "@/lib/api-client";
import type { Batch, BatchJobSummary } from "@/lib/types";
import BatchUploader from "@/components/BatchUploader";
import Link from "next/link";
import {
  Layers,
  Plus,
  Loader2,
  CheckCircle2,
  XCircle,
  Clock,
  Trash2,
  RotateCcw,
  StopCircle,
  FileText,
  Activity,
  ChevronDown,
  ChevronRight,
} from "lucide-react";

export default function BatchPage() {
  const [batches, setBatches] = useState<Batch[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [expandedBatch, setExpandedBatch] = useState<string | null>(null);
  const [batchDetails, setBatchDetails] = useState<Record<string, Batch>>({});

  const fetchBatches = useCallback(async () => {
    try {
      const data = await api.get<Batch[]>("/batch");
      setBatches(data);
    } catch (err) {
      console.error("Failed to load batches:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchBatches();
  }, [fetchBatches]);

  // Poll for active batch progress
  useEffect(() => {
    const activeBatches = batches.filter((b) =>
      ["QUEUED", "PROCESSING"].includes(b.status)
    );
    if (activeBatches.length === 0) return;

    const interval = setInterval(() => {
      fetchBatches();
      if (expandedBatch) {
        loadBatchDetail(expandedBatch);
      }
    }, 5000);

    return () => clearInterval(interval);
  }, [batches, expandedBatch, fetchBatches]);

  const loadBatchDetail = async (batchId: string) => {
    try {
      const data = await api.get<Batch>(`/batch/${batchId}`);
      setBatchDetails((prev) => ({ ...prev, [batchId]: data }));
    } catch (err) {
      console.error("Failed to load batch detail:", err);
    }
  };

  const toggleExpand = (batchId: string) => {
    if (expandedBatch === batchId) {
      setExpandedBatch(null);
    } else {
      setExpandedBatch(batchId);
      loadBatchDetail(batchId);
    }
  };

  const handleBatchCreated = (batch: Batch) => {
    setBatches((prev) => [batch, ...prev]);
    setShowCreate(false);
    setExpandedBatch(batch.id);
    setBatchDetails((prev) => ({ ...prev, [batch.id]: batch }));
  };

  const handleCancel = async (batchId: string) => {
    try {
      await api.post(`/batch/${batchId}/cancel`);
      fetchBatches();
      loadBatchDetail(batchId);
    } catch (err) {
      console.error("Cancel failed:", err);
    }
  };

  const handleRetry = async (batchId: string) => {
    try {
      await api.post(`/batch/${batchId}/retry`);
      fetchBatches();
      loadBatchDetail(batchId);
    } catch (err) {
      console.error("Retry failed:", err);
    }
  };

  const handleDelete = async (batchId: string) => {
    if (!confirm("Delete this batch and all its jobs?")) return;
    try {
      await api.delete(`/batch/${batchId}`);
      setBatches((prev) => prev.filter((b) => b.id !== batchId));
      if (expandedBatch === batchId) setExpandedBatch(null);
    } catch (err) {
      console.error("Delete failed:", err);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Batch Processing</h1>
          <p className="text-sm text-muted-foreground">
            Process multiple videos at once
          </p>
        </div>
        <button
          onClick={() => setShowCreate(!showCreate)}
          className="flex items-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-primary/90"
        >
          <Plus className="h-4 w-4" />
          New Batch
        </button>
      </div>

      {/* Create batch panel */}
      {showCreate && (
        <div className="rounded-xl border border-border bg-card p-6">
          <h2 className="mb-4 text-lg font-semibold text-foreground">
            Create New Batch
          </h2>
          <BatchUploader onBatchCreated={handleBatchCreated} />
        </div>
      )}

      {/* Batch list */}
      {loading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-6 w-6 animate-spin text-primary" />
        </div>
      ) : batches.length === 0 && !showCreate ? (
        <div className="rounded-xl border border-border bg-card p-8">
          <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
            <Layers className="mb-3 h-8 w-8" />
            <p className="text-sm">No batches yet. Create your first batch!</p>
          </div>
        </div>
      ) : (
        <div className="space-y-3">
          {batches.map((batch) => {
            const detail = batchDetails[batch.id];
            const isExpanded = expandedBatch === batch.id;
            const isActive = ["QUEUED", "PROCESSING"].includes(batch.status);
            const overallPercent =
              batch.total_jobs > 0
                ? (batch.completed_jobs / batch.total_jobs) * 100
                : 0;

            return (
              <div
                key={batch.id}
                className="overflow-hidden rounded-xl border border-border bg-card"
              >
                {/* Batch header */}
                <div
                  className="flex cursor-pointer items-center gap-3 px-4 py-3 hover:bg-muted/50"
                  onClick={() => toggleExpand(batch.id)}
                >
                  {isExpanded ? (
                    <ChevronDown className="h-4 w-4 text-muted-foreground" />
                  ) : (
                    <ChevronRight className="h-4 w-4 text-muted-foreground" />
                  )}

                  <BatchStatusIcon status={batch.status} />

                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-foreground">
                      {batch.name || `Batch ${batch.id.slice(0, 8)}`}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {batch.total_jobs} files &middot; {batch.completed_jobs}{" "}
                      done
                      {batch.failed_jobs > 0 && (
                        <span className="text-danger">
                          {" "}
                          &middot; {batch.failed_jobs} failed
                        </span>
                      )}{" "}
                      &middot; {new Date(batch.created_at).toLocaleString()}
                    </p>
                  </div>

                  {/* Progress bar */}
                  {isActive && (
                    <div className="w-32">
                      <div className="h-1.5 rounded-full bg-muted">
                        <div
                          className="h-1.5 rounded-full bg-primary transition-all"
                          style={{ width: `${overallPercent}%` }}
                        />
                      </div>
                      <p className="mt-0.5 text-right text-[10px] text-muted-foreground">
                        {batch.completed_jobs}/{batch.total_jobs}
                      </p>
                    </div>
                  )}

                  {/* Actions */}
                  <div
                    className="flex items-center gap-1"
                    onClick={(e) => e.stopPropagation()}
                  >
                    {isActive && (
                      <button
                        onClick={() => handleCancel(batch.id)}
                        className="rounded p-1.5 text-muted-foreground hover:bg-muted hover:text-warning"
                        title="Cancel all"
                      >
                        <StopCircle className="h-4 w-4" />
                      </button>
                    )}
                    {batch.failed_jobs > 0 && (
                      <button
                        onClick={() => handleRetry(batch.id)}
                        className="rounded p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground"
                        title="Retry failed"
                      >
                        <RotateCcw className="h-4 w-4" />
                      </button>
                    )}
                    {!isActive && (
                      <button
                        onClick={() => handleDelete(batch.id)}
                        className="rounded p-1.5 text-muted-foreground hover:bg-danger/10 hover:text-danger"
                        title="Delete batch"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    )}
                  </div>
                </div>

                {/* Expanded: Job list */}
                {isExpanded && (
                  <div className="border-t border-border">
                    {!detail?.jobs || detail.jobs.length === 0 ? (
                      <div className="flex items-center justify-center py-6">
                        <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                      </div>
                    ) : (
                      <div className="divide-y divide-border">
                        {detail.jobs.map((job) => (
                          <BatchJobRow key={job.id} job={job} />
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function BatchJobRow({ job }: { job: BatchJobSummary }) {
  const apiBase =
    process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

  return (
    <div className="flex items-center gap-3 px-4 py-2.5 text-sm">
      <JobStatusIcon status={job.status} />
      <Link
        href={`/jobs/${job.id}/`}
        className="min-w-0 flex-1 truncate text-foreground hover:text-primary"
      >
        {job.input_filename}
      </Link>

      {job.status === "PROCESSING" && (
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground">
            {job.current_step}
          </span>
          <div className="w-20">
            <div className="h-1 rounded-full bg-muted">
              <div
                className="h-1 rounded-full bg-primary transition-all"
                style={{ width: `${job.progress_percent}%` }}
              />
            </div>
          </div>
          <span className="text-xs text-muted-foreground">
            {job.progress_percent.toFixed(0)}%
          </span>
        </div>
      )}

      {job.status === "FAILED" && job.error_message && (
        <span
          className="max-w-xs truncate text-xs text-danger"
          title={job.error_message}
        >
          {job.error_message}
        </span>
      )}

      {job.status === "COMPLETED" && job.output_subtitle_paths && (
        <div className="flex gap-1">
          {job.output_subtitle_paths.map((p, i) => {
            const ext = p.split(".").pop() || "";
            return (
              <a
                key={i}
                href={`${apiBase}/jobs/${job.id}/download?type=subtitle&format=${ext}`}
                className="rounded bg-muted px-1.5 py-0.5 text-[10px] uppercase text-muted-foreground hover:bg-primary/10 hover:text-primary"
              >
                {ext}
              </a>
            );
          })}
        </div>
      )}

      {job.status === "COMPLETED" && (
        <Link
          href={`/jobs/${job.id}/edit`}
          className="rounded p-1 text-muted-foreground hover:text-primary"
          title="Edit subtitles"
        >
          <FileText className="h-3.5 w-3.5" />
        </Link>
      )}
    </div>
  );
}

function BatchStatusIcon({ status }: { status: string }) {
  switch (status) {
    case "COMPLETED":
      return <CheckCircle2 className="h-5 w-5 text-success" />;
    case "PARTIAL":
      return <XCircle className="h-5 w-5 text-warning" />;
    case "PROCESSING":
      return <Loader2 className="h-5 w-5 animate-spin text-primary" />;
    case "QUEUED":
      return <Clock className="h-5 w-5 text-warning" />;
    default:
      return <Layers className="h-5 w-5 text-muted-foreground" />;
  }
}

function JobStatusIcon({ status }: { status: string }) {
  switch (status) {
    case "COMPLETED":
      return <CheckCircle2 className="h-4 w-4 text-success" />;
    case "FAILED":
      return <XCircle className="h-4 w-4 text-danger" />;
    case "PROCESSING":
      return <Loader2 className="h-4 w-4 animate-spin text-primary" />;
    case "QUEUED":
      return <Clock className="h-4 w-4 text-warning" />;
    case "CANCELLED":
      return <StopCircle className="h-4 w-4 text-muted-foreground" />;
    default:
      return <Activity className="h-4 w-4 text-muted-foreground" />;
  }
}
