"use client";

import { useState, useEffect, useCallback } from "react";
import { useJobs } from "@/hooks/useJob";
import { api } from "@/lib/api-client";
import type { Job, JobStatus } from "@/lib/types";
import Link from "next/link";
import {
  PlusCircle,
  CheckCircle2,
  XCircle,
  Loader2,
  Clock,
  Activity,
  Eye,
  Pencil,
  Trash2,
  ChevronLeft,
  ChevronRight,
  Ban,
} from "lucide-react";
import { cn } from "@/lib/utils";

const PER_PAGE = 20;

const STATUS_TABS: { label: string; value: string | null }[] = [
  { label: "Tất cả", value: null },
  { label: "Đang xử lý", value: "PROCESSING" },
  { label: "Chờ xử lý", value: "QUEUED" },
  { label: "Hoàn thành", value: "COMPLETED" },
  { label: "Thất bại", value: "FAILED" },
  { label: "Đã hủy", value: "CANCELLED" },
];

export default function JobsListPage() {
  const [page, setPage] = useState(0);
  const [statusFilter, setStatusFilter] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);

  const { jobs, total, loading, refetch } = useJobs({
    skip: page * PER_PAGE,
    limit: PER_PAGE,
    status: statusFilter,
  });

  const totalPages = Math.ceil(total / PER_PAGE);

  // Reset page when filter changes
  useEffect(() => {
    setPage(0);
  }, [statusFilter]);

  // Auto-refresh when active jobs exist
  useEffect(() => {
    const hasActive = jobs.some((j) =>
      ["QUEUED", "PROCESSING"].includes(j.status)
    );
    if (!hasActive) return;

    const interval = setInterval(refetch, 8000);
    return () => clearInterval(interval);
  }, [jobs, refetch]);

  const handleDelete = async (jobId: string) => {
    setDeletingId(jobId);
    try {
      await api.delete(`/jobs/${jobId}`);
      setConfirmDeleteId(null);
      refetch();
    } catch (err: any) {
      console.error("Failed to delete job:", err);
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Danh sách Jobs</h1>
          <p className="text-sm text-muted-foreground">
            Quản lý toàn bộ công việc tạo phụ đề
          </p>
        </div>
        <Link
          href="/jobs/new/"
          className="flex items-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
        >
          <PlusCircle className="h-4 w-4" />
          Tạo mới
        </Link>
      </div>

      {/* Status filter tabs */}
      <div className="flex flex-wrap gap-2">
        {STATUS_TABS.map((tab) => (
          <button
            key={tab.value ?? "all"}
            onClick={() => setStatusFilter(tab.value)}
            className={cn(
              "rounded-lg px-3 py-1.5 text-sm font-medium transition-colors",
              statusFilter === tab.value
                ? "bg-primary text-primary-foreground"
                : "border border-border text-muted-foreground hover:bg-muted hover:text-foreground"
            )}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Jobs table */}
      <div className="rounded-xl border border-border bg-card">
        {loading && jobs.length === 0 ? (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
          </div>
        ) : jobs.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-muted-foreground">
            <Activity className="mb-3 h-8 w-8" />
            <p className="text-sm">Không tìm thấy công việc nào</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-border text-left text-xs text-muted-foreground">
                  <th className="px-4 py-3 font-medium">Trạng thái</th>
                  <th className="px-4 py-3 font-medium">Tên file</th>
                  <th className="hidden px-4 py-3 font-medium md:table-cell">Ngôn ngữ</th>
                  <th className="hidden px-4 py-3 font-medium lg:table-cell">Model</th>
                  <th className="hidden px-4 py-3 font-medium md:table-cell">Tiến độ</th>
                  <th className="px-4 py-3 font-medium">Thời gian</th>
                  <th className="px-4 py-3 text-right font-medium">Thao tác</th>
                </tr>
              </thead>
              <tbody>
                {jobs.map((job) => (
                  <tr
                    key={job.id}
                    className="border-b border-border last:border-b-0 transition-colors hover:bg-muted/50"
                  >
                    {/* Status */}
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <JobStatusIcon status={job.status} />
                        <span className={cn("text-xs font-medium", statusColor(job.status))}>
                          {statusLabel(job.status)}
                        </span>
                      </div>
                    </td>

                    {/* Filename */}
                    <td className="px-4 py-3">
                      <Link
                        href={`/jobs/${job.id}/`}
                        className="text-sm font-medium text-foreground hover:text-primary hover:underline"
                      >
                        {job.input_filename}
                      </Link>
                      {job.current_step && job.status === "PROCESSING" && (
                        <p className="text-xs text-muted-foreground">{job.current_step}</p>
                      )}
                      {job.error_message && job.status === "FAILED" && (
                        <p className="max-w-xs truncate text-xs text-danger">{job.error_message}</p>
                      )}
                    </td>

                    {/* Language */}
                    <td className="hidden px-4 py-3 md:table-cell">
                      <span className="text-xs text-muted-foreground">
                        {job.detected_language || job.source_language || "—"}
                        {job.target_language && ` → ${job.target_language}`}
                      </span>
                    </td>

                    {/* Model */}
                    <td className="hidden px-4 py-3 lg:table-cell">
                      <span className="rounded bg-muted px-1.5 py-0.5 text-xs text-muted-foreground">
                        {job.whisper_model}
                      </span>
                    </td>

                    {/* Progress */}
                    <td className="hidden px-4 py-3 md:table-cell">
                      {job.status === "PROCESSING" ? (
                        <div className="w-24">
                          <div className="h-1.5 rounded-full bg-muted">
                            <div
                              className="h-1.5 rounded-full bg-primary transition-all"
                              style={{ width: `${job.progress_percent}%` }}
                            />
                          </div>
                          <p className="mt-0.5 text-right text-[10px] text-muted-foreground">
                            {job.progress_percent.toFixed(0)}%
                          </p>
                        </div>
                      ) : job.status === "COMPLETED" ? (
                        <div className="flex gap-1">
                          {job.output_formats.map((fmt) => (
                            <span
                              key={fmt}
                              className="rounded bg-success/10 px-1.5 py-0.5 text-[10px] uppercase text-success"
                            >
                              {fmt}
                            </span>
                          ))}
                        </div>
                      ) : (
                        <span className="text-xs text-muted-foreground">—</span>
                      )}
                    </td>

                    {/* Time */}
                    <td className="px-4 py-3">
                      <span className="text-xs text-muted-foreground">
                        {new Date(job.created_at).toLocaleDateString("vi-VN")}
                      </span>
                      <br />
                      <span className="text-[10px] text-muted-foreground/60">
                        {new Date(job.created_at).toLocaleTimeString("vi-VN")}
                      </span>
                    </td>

                    {/* Actions */}
                    <td className="px-4 py-3">
                      <div className="flex items-center justify-end gap-1">
                        {/* View */}
                        <Link
                          href={`/jobs/${job.id}/`}
                          className="rounded p-1.5 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
                          title="Xem chi tiết"
                        >
                          <Eye className="h-4 w-4" />
                        </Link>

                        {/* Edit subtitles - only for completed jobs */}
                        {job.status === "COMPLETED" && (
                          <Link
                            href={`/jobs/${job.id}/edit`}
                            className="rounded p-1.5 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
                            title="Sửa phụ đề"
                          >
                            <Pencil className="h-4 w-4" />
                          </Link>
                        )}

                        {/* Delete */}
                        {confirmDeleteId === job.id ? (
                          <div className="flex items-center gap-1">
                            <button
                              onClick={() => handleDelete(job.id)}
                              disabled={deletingId === job.id}
                              className="rounded bg-danger px-2 py-1 text-xs text-white hover:bg-danger/90 disabled:opacity-50"
                            >
                              {deletingId === job.id ? (
                                <Loader2 className="h-3 w-3 animate-spin" />
                              ) : (
                                "Xóa"
                              )}
                            </button>
                            <button
                              onClick={() => setConfirmDeleteId(null)}
                              className="rounded px-2 py-1 text-xs text-muted-foreground hover:bg-muted"
                            >
                              Hủy
                            </button>
                          </div>
                        ) : (
                          <button
                            onClick={() => setConfirmDeleteId(job.id)}
                            className="rounded p-1.5 text-muted-foreground transition-colors hover:bg-danger/10 hover:text-danger"
                            title="Xóa"
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between border-t border-border px-4 py-3">
            <span className="text-xs text-muted-foreground">
              Hiển thị {page * PER_PAGE + 1}–{Math.min((page + 1) * PER_PAGE, total)} / {total} kết quả
            </span>
            <div className="flex items-center gap-1">
              <button
                onClick={() => setPage((p) => Math.max(0, p - 1))}
                disabled={page === 0}
                className="rounded p-1.5 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground disabled:opacity-30"
              >
                <ChevronLeft className="h-4 w-4" />
              </button>
              {Array.from({ length: Math.min(totalPages, 7) }, (_, i) => {
                let pageNum: number;
                if (totalPages <= 7) {
                  pageNum = i;
                } else if (page < 3) {
                  pageNum = i;
                } else if (page > totalPages - 4) {
                  pageNum = totalPages - 7 + i;
                } else {
                  pageNum = page - 3 + i;
                }
                return (
                  <button
                    key={pageNum}
                    onClick={() => setPage(pageNum)}
                    className={cn(
                      "min-w-[32px] rounded px-2 py-1 text-xs font-medium transition-colors",
                      page === pageNum
                        ? "bg-primary text-primary-foreground"
                        : "text-muted-foreground hover:bg-muted hover:text-foreground"
                    )}
                  >
                    {pageNum + 1}
                  </button>
                );
              })}
              <button
                onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
                disabled={page >= totalPages - 1}
                className="rounded p-1.5 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground disabled:opacity-30"
              >
                <ChevronRight className="h-4 w-4" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
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
      return <Ban className="h-4 w-4 text-muted-foreground" />;
    default:
      return <Activity className="h-4 w-4 text-muted-foreground" />;
  }
}

function statusLabel(status: string): string {
  const labels: Record<string, string> = {
    PROCESSING: "Đang xử lý",
    QUEUED: "Chờ xử lý",
    COMPLETED: "Hoàn thành",
    FAILED: "Thất bại",
    CANCELLED: "Đã hủy",
  };
  return labels[status] || status;
}

function statusColor(status: string): string {
  const colors: Record<string, string> = {
    PROCESSING: "text-primary",
    QUEUED: "text-warning",
    COMPLETED: "text-success",
    FAILED: "text-danger",
    CANCELLED: "text-muted-foreground",
  };
  return colors[status] || "text-muted-foreground";
}
