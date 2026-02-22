"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api-client";
import type { Job } from "@/lib/types";

export function useJob(jobId: string | null) {
  const [job, setJob] = useState<Job | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchJob = useCallback(async () => {
    if (!jobId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await api.get<Job>(`/jobs/${jobId}`);
      setJob(data);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [jobId]);

  useEffect(() => {
    fetchJob();
  }, [fetchJob]);

  return { job, loading, error, refetch: fetchJob };
}

interface JobsListResponse {
  jobs: Job[];
  total: number;
  skip: number;
  limit: number;
}

interface UseJobsOptions {
  skip?: number;
  limit?: number;
  status?: string | null;
}

export function useJobs(options: UseJobsOptions = {}) {
  const { skip = 0, limit = 50, status = null } = options;
  const [jobs, setJobs] = useState<Job[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);

  const fetchJobs = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, string> = {
        skip: String(skip),
        limit: String(limit),
      };
      if (status) params.status = status;
      const data = await api.get<JobsListResponse | Job[]>("/jobs", { params });
      if (Array.isArray(data)) {
        setJobs(data);
        setTotal(data.length);
      } else {
        setJobs(data.jobs);
        setTotal(data.total);
      }
    } catch (err) {
      console.error("Failed to fetch jobs:", err);
    } finally {
      setLoading(false);
    }
  }, [skip, limit, status]);

  useEffect(() => {
    fetchJobs();
  }, [fetchJobs]);

  return { jobs, total, loading, refetch: fetchJobs };
}
