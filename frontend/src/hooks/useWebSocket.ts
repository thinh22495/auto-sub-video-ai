"use client";

import { useEffect, useRef, useState } from "react";
import { JobWebSocket } from "@/lib/websocket";
import type { JobProgressEvent } from "@/lib/types";

export function useJobProgress(jobId: string | null) {
  const [progress, setProgress] = useState<JobProgressEvent | null>(null);
  const wsRef = useRef<JobWebSocket | null>(null);

  useEffect(() => {
    if (!jobId) return;

    const ws = new JobWebSocket(jobId, (event) => {
      setProgress(event);
    });
    ws.connect();
    wsRef.current = ws;

    return () => {
      ws.close();
      wsRef.current = null;
    };
  }, [jobId]);

  return progress;
}
