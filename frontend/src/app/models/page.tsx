"use client";

import { Cpu } from "lucide-react";

export default function ModelsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground">Model Management</h1>
        <p className="text-sm text-muted-foreground">
          Download and manage Whisper and Ollama models
        </p>
      </div>

      <div className="rounded-xl border border-border bg-card p-8">
        <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
          <Cpu className="mb-3 h-8 w-8" />
          <p className="text-sm">Model management coming in Phase 3</p>
        </div>
      </div>
    </div>
  );
}
