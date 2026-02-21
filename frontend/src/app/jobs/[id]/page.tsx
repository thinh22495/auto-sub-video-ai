"use client";

import { useParams, useRouter } from "next/navigation";
import { useJob } from "@/hooks/useJob";
import { useJobProgress } from "@/hooks/useWebSocket";
import { JobProgress } from "@/components/JobProgress";
import {
  ArrowLeft,
  Download,
  RefreshCw,
  Trash2,
  FileText,
  Video,
  Clock,
  Globe,
  Cpu,
  Loader2,
  Edit3,
} from "lucide-react";
import { api } from "@/lib/api-client";
import { useState } from "react";
import Link from "next/link";

export default function JobDetailPage() {
  const params = useParams();
  const router = useRouter();
  const jobId = params.id as string;
  const { job, loading, error, refetch } = useJob(jobId);
  const progress = useJobProgress(
    job && ["QUEUED", "PROCESSING"].includes(job.status) ? jobId : null
  );
  const [actionLoading, setActionLoading] = useState(false);

  if (loading) {
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

  const handleRetry = async () => {
    setActionLoading(true);
    try {
      await api.post(`/jobs/${jobId}/retry`);
      refetch();
    } catch (err) {
      console.error("Retry failed:", err);
    } finally {
      setActionLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!confirm("Are you sure you want to delete this job?")) return;
    setActionLoading(true);
    try {
      await api.delete(`/jobs/${jobId}`);
      router.push("/");
    } catch (err) {
      console.error("Delete failed:", err);
    } finally {
      setActionLoading(false);
    }
  };

  const isTerminal = ["COMPLETED", "FAILED", "CANCELLED"].includes(job.status);
  const apiBase =
    process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link
            href="/"
            className="rounded-lg p-2 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
          >
            <ArrowLeft className="h-5 w-5" />
          </Link>
          <div>
            <h1 className="text-2xl font-bold text-foreground">
              {job.input_filename}
            </h1>
            <p className="text-xs text-muted-foreground">Job ID: {job.id}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {job.status === "FAILED" && (
            <button
              onClick={handleRetry}
              disabled={actionLoading}
              className="flex items-center gap-1.5 rounded-lg border border-border px-3 py-2 text-sm text-foreground transition-colors hover:bg-muted"
            >
              <RefreshCw className="h-4 w-4" />
              Retry
            </button>
          )}
          {isTerminal && (
            <button
              onClick={handleDelete}
              disabled={actionLoading}
              className="flex items-center gap-1.5 rounded-lg border border-danger/30 px-3 py-2 text-sm text-danger transition-colors hover:bg-danger/10"
            >
              <Trash2 className="h-4 w-4" />
              Delete
            </button>
          )}
        </div>
      </div>

      {/* Progress */}
      {!isTerminal && <JobProgress progress={progress} />}

      {/* Completed result */}
      {job.status === "COMPLETED" && (
        <div className="rounded-xl border border-success/30 bg-success/5 p-6">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-success">
              Phiên âm hoàn tất
            </h2>
            <Link
              href={`/jobs/${jobId}/edit`}
              className="flex items-center gap-1.5 rounded-lg border border-primary/30 bg-primary/10 px-3 py-2 text-sm font-medium text-primary transition-colors hover:bg-primary/20"
            >
              <Edit3 className="h-4 w-4" />
              Chỉnh sửa phụ đề
            </Link>
          </div>
          <div className="space-y-3">
            {job.output_subtitle_paths?.map((path, i) => {
              const filename = path.split("/").pop() || path;
              const ext = filename.split(".").pop() || "";
              return (
                <a
                  key={i}
                  href={`${apiBase}/jobs/${jobId}/download?type=subtitle&format=${ext}`}
                  className="flex items-center gap-3 rounded-lg border border-border bg-card p-4 transition-colors hover:bg-muted"
                >
                  <FileText className="h-5 w-5 text-primary" />
                  <span className="flex-1 text-sm font-medium text-foreground">
                    {filename}
                  </span>
                  <Download className="h-4 w-4 text-muted-foreground" />
                </a>
              );
            })}
            {job.output_video_path && (
              <a
                href={`${apiBase}/jobs/${jobId}/download?type=video`}
                className="flex items-center gap-3 rounded-lg border border-border bg-card p-4 transition-colors hover:bg-muted"
              >
                <Video className="h-5 w-5 text-accent" />
                <span className="flex-1 text-sm font-medium text-foreground">
                  {job.output_video_path.split("/").pop()}
                </span>
                <Download className="h-4 w-4 text-muted-foreground" />
              </a>
            )}
          </div>
        </div>
      )}

      {/* Failed error */}
      {job.status === "FAILED" && job.error_message && (
        <div className="rounded-xl border border-danger/30 bg-danger/5 p-6">
          <h2 className="mb-2 text-lg font-semibold text-danger">Lỗi</h2>
          <pre className="whitespace-pre-wrap text-sm text-danger/80">
            {job.error_message}
          </pre>
        </div>
      )}

      {/* Job info cards */}
      <div className="grid grid-cols-2 gap-4">
        <InfoCard icon={<Globe className="h-4 w-4" />} label="Ngôn ngữ nguồn">
          {job.detected_language || job.source_language || "Auto-detect"}
        </InfoCard>
        <InfoCard icon={<Globe className="h-4 w-4" />} label="Ngôn ngữ đích">
          {job.target_language || "Không (không dịch)"}
        </InfoCard>
        <InfoCard icon={<Cpu className="h-4 w-4" />} label="Mô hình Whisper">
          {job.whisper_model}
        </InfoCard>
        <InfoCard icon={<Clock className="h-4 w-4" />} label="Ngày tạo">
          {new Date(job.created_at).toLocaleString()}
        </InfoCard>
        <InfoCard icon={<FileText className="h-4 w-4" />} label="Định dạng đầu ra">
          {job.output_formats.map((f) => `.${f}`).join(", ")}
        </InfoCard>
        <InfoCard icon={<Video className="h-4 w-4" />} label="Burn-in">
          {job.burn_in ? "Có" : "Không"}
        </InfoCard>
      </div>
    </div>
  );
}

function InfoCard({
  icon,
  label,
  children,
}: {
  icon: React.ReactNode;
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-xl border border-border bg-card p-4">
      <div className="mb-1 flex items-center gap-2 text-muted-foreground">
        {icon}
        <span className="text-xs">{label}</span>
      </div>
      <p className="text-sm font-medium text-foreground">{children}</p>
    </div>
  );
}
