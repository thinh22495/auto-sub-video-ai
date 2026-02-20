"use client";

import { Layers } from "lucide-react";

export default function BatchPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground">Batch Processing</h1>
        <p className="text-sm text-muted-foreground">
          Process multiple videos at once
        </p>
      </div>

      <div className="rounded-xl border border-border bg-card p-8">
        <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
          <Layers className="mb-3 h-8 w-8" />
          <p className="text-sm">Batch processing coming in Phase 7</p>
        </div>
      </div>
    </div>
  );
}
