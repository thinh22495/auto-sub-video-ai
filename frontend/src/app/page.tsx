"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api-client";
import type { HealthStatus, Job } from "@/lib/types";
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
} from "lucide-react";
import Link from "next/link";

export default function DashboardPage() {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .get<HealthStatus>("/health")
      .then(setHealth)
      .catch((err) => setError(err.message));
    api
      .get<Job[]>("/jobs", { params: { limit: "10" } })
      .then(setJobs)
      .catch(() => {});
  }, []);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Dashboard</h1>
          <p className="text-sm text-muted-foreground">
            AutoSubAI - Offline video subtitle generation
          </p>
        </div>
        <Link
          href="/jobs/new/"
          className="flex items-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
        >
          <PlusCircle className="h-4 w-4" />
          New Job
        </Link>
      </div>

      {/* Status Cards */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatusCard
          title="API Server"
          value={health?.services.api === "up" ? "Online" : "Offline"}
          status={health?.services.api === "up" ? "success" : "danger"}
          icon={<Activity className="h-5 w-5" />}
        />
        <StatusCard
          title="Redis"
          value={health?.services.redis === "up" ? "Connected" : "Disconnected"}
          status={health?.services.redis === "up" ? "success" : "danger"}
          icon={<MonitorSpeaker className="h-5 w-5" />}
        />
        <StatusCard
          title="Ollama"
          value={health?.services.ollama === "up" ? "Running" : "Stopped"}
          status={health?.services.ollama === "up" ? "success" : "warning"}
          icon={<Cpu className="h-5 w-5" />}
        />
        <StatusCard
          title="GPU"
          value={
            health?.services.gpu.available
              ? health.services.gpu.name || "Available"
              : "CPU Only"
          }
          status={health?.services.gpu.available ? "success" : "warning"}
          icon={<HardDrive className="h-5 w-5" />}
          subtitle={
            health?.services.gpu.available
              ? `${health.services.gpu.vram_free_mb}MB free / ${health.services.gpu.vram_total_mb}MB`
              : undefined
          }
        />
      </div>

      {/* Disk Usage */}
      {health && (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <DiskCard title="Videos Storage" usage={health.disk.videos} />
          <DiskCard title="Models Storage" usage={health.disk.models} />
        </div>
      )}

      {/* Recent Jobs */}
      <div className="rounded-xl border border-border bg-card p-6">
        <h2 className="mb-4 text-lg font-semibold text-foreground">
          Recent Jobs
        </h2>
        {jobs.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
            <Activity className="mb-3 h-8 w-8" />
            <p className="text-sm">No jobs yet. Create your first subtitle job!</p>
            <Link
              href="/jobs/new/"
              className="mt-3 text-sm font-medium text-primary hover:underline"
            >
              Get started
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
                <div className="flex-1 min-w-0">
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
                {job.output_formats && (
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
          Failed to connect to API: {error}
        </div>
      )}
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
            {(usage.total_gb - usage.free_gb).toFixed(1)}GB used
          </span>
          <span>{usage.free_gb.toFixed(1)}GB free</span>
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
