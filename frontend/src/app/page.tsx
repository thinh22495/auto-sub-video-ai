"use client";

import { useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api-client";
import type { Batch, HealthStatus, Job } from "@/lib/types";
import {
  Activity,
  Cpu,
  HardDrive,
  MonitorSpeaker,
  PlusCircle,
  CheckCircle2,
  XCircle,
  Loader2,
  Clock,
  Layers,
} from "lucide-react";
import Link from "next/link";

export default function DashboardPage() {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [batches, setBatches] = useState<Batch[]>([]);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(() => {
    api
      .get<HealthStatus>("/health")
      .then(setHealth)
      .catch((err) => setError(err.message));
    api
      .get<Job[]>("/jobs", { params: { limit: "15" } })
      .then(setJobs)
      .catch(() => {});
    api
      .get<Batch[]>("/batch", { params: { limit: "5" } })
      .then(setBatches)
      .catch(() => {});
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Auto-refresh when active jobs exist
  useEffect(() => {
    const hasActive = jobs.some((j) =>
      ["QUEUED", "PROCESSING"].includes(j.status)
    );
    if (!hasActive) return;

    const interval = setInterval(fetchData, 8000);
    return () => clearInterval(interval);
  }, [jobs, fetchData]);

  // Quick stats
  const activeJobs = jobs.filter((j) => j.status === "PROCESSING").length;
  const queuedJobs = jobs.filter((j) => j.status === "QUEUED").length;
  const completedJobs = jobs.filter((j) => j.status === "COMPLETED").length;
  const failedJobs = jobs.filter((j) => j.status === "FAILED").length;

  return (
    <div className="space-y-6">
      {/* Tiêu đề */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Trang chủ</h1>
          <p className="text-sm text-muted-foreground">
            AutoSubAI - Tạo phụ đề video tự động offline
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Link
            href="/batch/"
            className="flex items-center gap-2 rounded-lg border border-border px-4 py-2.5 text-sm font-medium text-foreground transition-colors hover:bg-muted"
          >
            <Layers className="h-4 w-4" />
            Hàng loạt
          </Link>
          <Link
            href="/jobs/new/"
            className="flex items-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
          >
            <PlusCircle className="h-4 w-4" />
            Tạo mới
          </Link>
        </div>
      </div>

      {/* Thống kê nhanh */}
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <QuickStat
          label="Đang xử lý"
          value={activeJobs}
          icon={<Loader2 className={`h-4 w-4 ${activeJobs > 0 ? "animate-spin" : ""}`} />}
          color="text-primary"
        />
        <QuickStat
          label="Chờ xử lý"
          value={queuedJobs}
          icon={<Clock className="h-4 w-4" />}
          color="text-warning"
        />
        <QuickStat
          label="Hoàn thành"
          value={completedJobs}
          icon={<CheckCircle2 className="h-4 w-4" />}
          color="text-success"
        />
        <QuickStat
          label="Thất bại"
          value={failedJobs}
          icon={<XCircle className="h-4 w-4" />}
          color="text-danger"
        />
      </div>

      {/* Trạng thái hệ thống */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatusCard
          title="Máy chủ API"
          value={health?.services.api === "up" ? "Trực tuyến" : "Ngoại tuyến"}
          status={health?.services.api === "up" ? "success" : "danger"}
          icon={<Activity className="h-5 w-5" />}
        />
        <StatusCard
          title="Redis"
          value={health?.services.redis === "up" ? "Đã kết nối" : "Mất kết nối"}
          status={health?.services.redis === "up" ? "success" : "danger"}
          icon={<MonitorSpeaker className="h-5 w-5" />}
        />
        <StatusCard
          title="Ollama"
          value={health?.services.ollama === "up" ? "Đang chạy" : "Đã dừng"}
          status={health?.services.ollama === "up" ? "success" : "warning"}
          icon={<Cpu className="h-5 w-5" />}
        />
        <StatusCard
          title="GPU"
          value={
            health?.services.gpu.available
              ? health.services.gpu.name || "Khả dụng"
              : "Chỉ CPU"
          }
          status={health?.services.gpu.available ? "success" : "warning"}
          icon={<HardDrive className="h-5 w-5" />}
          subtitle={
            health?.services.gpu.available
              ? `${health.services.gpu.vram_free_mb}MB trống / ${health.services.gpu.vram_total_mb}MB`
              : undefined
          }
        />
      </div>

      {/* Dung lượng ổ đĩa */}
      {health && (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <DiskCard title="Lưu trữ video" usage={health.disk.videos} />
          <DiskCard title="Lưu trữ mô hình" usage={health.disk.models} />
        </div>
      )}

      {/* Batch gần đây */}
      {batches.length > 0 && (
        <div className="rounded-xl border border-border bg-card p-6">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-foreground">
              Batch gần đây
            </h2>
            <Link
              href="/batch/"
              className="text-xs font-medium text-primary hover:underline"
            >
              Xem tất cả
            </Link>
          </div>
          <div className="space-y-2">
            {batches.map((batch) => {
              const isActive = ["QUEUED", "PROCESSING"].includes(batch.status);
              const percent =
                batch.total_jobs > 0
                  ? (batch.completed_jobs / batch.total_jobs) * 100
                  : 0;

              return (
                <Link
                  key={batch.id}
                  href="/batch/"
                  className="flex items-center gap-3 rounded-lg border border-border p-3 transition-colors hover:bg-muted"
                >
                  <BatchStatusIcon status={batch.status} />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-foreground">
                      {batch.name || `Batch ${batch.id.slice(0, 8)}`}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {batch.completed_jobs}/{batch.total_jobs} hoàn thành
                      {batch.failed_jobs > 0 && (
                        <span className="text-danger">
                          {" "}
                          &middot; {batch.failed_jobs} thất bại
                        </span>
                      )}
                    </p>
                  </div>
                  {isActive && (
                    <div className="w-24">
                      <div className="h-1.5 rounded-full bg-muted">
                        <div
                          className="h-1.5 rounded-full bg-primary transition-all"
                          style={{ width: `${percent}%` }}
                        />
                      </div>
                    </div>
                  )}
                </Link>
              );
            })}
          </div>
        </div>
      )}

      {/* Công việc gần đây */}
      <div className="rounded-xl border border-border bg-card p-6">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-foreground">Công việc gần đây</h2>
          {jobs.length > 0 && (
            <span className="text-xs text-muted-foreground">
              Hiển thị {jobs.length}
            </span>
          )}
        </div>
        {jobs.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
            <Activity className="mb-3 h-8 w-8" />
            <p className="text-sm">
              Chưa có công việc nào. Hãy tạo phụ đề đầu tiên!
            </p>
            <Link
              href="/jobs/new/"
              className="mt-3 text-sm font-medium text-primary hover:underline"
            >
              Bắt đầu ngay
            </Link>
          </div>
        ) : (
          <div className="space-y-2">
            {jobs.map((job) => (
              <Link
                key={job.id}
                href={`/jobs/${job.id}/`}
                className="flex items-center gap-4 rounded-lg border border-border p-4 transition-colors hover:bg-muted"
              >
                <JobStatusIcon status={job.status} />
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-foreground">
                    {job.input_filename}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {job.current_step || job.status} &middot;{" "}
                    {new Date(job.created_at).toLocaleString()}
                  </p>
                </div>
                {job.status === "PROCESSING" && (
                  <div className="w-24">
                    <div className="h-1.5 rounded-full bg-muted">
                      <div
                        className="h-1.5 rounded-full bg-primary transition-all"
                        style={{ width: `${job.progress_percent}%` }}
                      />
                    </div>
                    <p className="mt-1 text-right text-xs text-muted-foreground">
                      {job.progress_percent.toFixed(0)}%
                    </p>
                  </div>
                )}
                {job.status === "COMPLETED" && (
                  <div className="flex gap-1">
                    {job.output_formats.map((fmt) => (
                      <span
                        key={fmt}
                        className="rounded bg-muted px-1.5 py-0.5 text-xs uppercase text-muted-foreground"
                      >
                        {fmt}
                      </span>
                    ))}
                  </div>
                )}
              </Link>
            ))}
          </div>
        )}
      </div>

      {error && (
        <div className="rounded-lg border border-danger/30 bg-danger/10 p-4 text-sm text-danger">
          Không thể kết nối API: {error}
        </div>
      )}
    </div>
  );
}

function QuickStat({
  label,
  value,
  icon,
  color,
}: {
  label: string;
  value: number;
  icon: React.ReactNode;
  color: string;
}) {
  return (
    <div className="rounded-xl border border-border bg-card p-3">
      <div className="flex items-center justify-between">
        <span className="text-xs text-muted-foreground">{label}</span>
        <span className={color}>{icon}</span>
      </div>
      <p className={`mt-1 text-2xl font-bold ${color}`}>{value}</p>
    </div>
  );
}

function StatusCard({
  title,
  value,
  status,
  icon,
  subtitle,
}: {
  title: string;
  value: string;
  status: "success" | "warning" | "danger";
  icon: React.ReactNode;
  subtitle?: string;
}) {
  const colors = {
    success: "text-success",
    warning: "text-warning",
    danger: "text-danger",
  };

  return (
    <div className="rounded-xl border border-border bg-card p-4">
      <div className="flex items-center justify-between">
        <span className="text-sm text-muted-foreground">{title}</span>
        <span className={colors[status]}>{icon}</span>
      </div>
      <p className={`mt-2 text-lg font-semibold ${colors[status]}`}>{value}</p>
      {subtitle && (
        <p className="mt-1 text-xs text-muted-foreground">{subtitle}</p>
      )}
    </div>
  );
}

function JobStatusIcon({ status }: { status: string }) {
  switch (status) {
    case "COMPLETED":
      return <CheckCircle2 className="h-5 w-5 text-success" />;
    case "FAILED":
      return <XCircle className="h-5 w-5 text-danger" />;
    case "PROCESSING":
      return <Loader2 className="h-5 w-5 animate-spin text-primary" />;
    case "QUEUED":
      return <Clock className="h-5 w-5 text-warning" />;
    default:
      return <Activity className="h-5 w-5 text-muted-foreground" />;
  }
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

function DiskCard({
  title,
  usage,
}: {
  title: string;
  usage: { total_gb: number; free_gb: number; used_percent: number };
}) {
  return (
    <div className="rounded-xl border border-border bg-card p-4">
      <h3 className="text-sm font-medium text-muted-foreground">{title}</h3>
      <div className="mt-3">
        <div className="mb-1 flex justify-between text-xs text-muted-foreground">
          <span>
            Đã dùng {(usage.total_gb - usage.free_gb).toFixed(1)}GB
          </span>
          <span>Còn trống {usage.free_gb.toFixed(1)}GB</span>
        </div>
        <div className="h-2 rounded-full bg-muted">
          <div
            className="h-2 rounded-full bg-primary transition-all"
            style={{ width: `${Math.min(usage.used_percent, 100)}%` }}
          />
        </div>
      </div>
    </div>
  );
}
