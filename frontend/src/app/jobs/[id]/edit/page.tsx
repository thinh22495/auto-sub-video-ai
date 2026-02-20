"use client";

import { Edit3 } from "lucide-react";

export default function SubtitleEditorPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground">Subtitle Editor</h1>
        <p className="text-sm text-muted-foreground">
          Edit subtitle timing and text
        </p>
      </div>

      <div className="rounded-xl border border-border bg-card p-8">
        <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
          <Edit3 className="mb-3 h-8 w-8" />
          <p className="text-sm">Subtitle editor coming in Phase 6</p>
        </div>
      </div>
    </div>
  );
}
