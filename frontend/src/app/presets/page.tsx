"use client";

import { Palette } from "lucide-react";

export default function PresetsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground">Export Presets</h1>
        <p className="text-sm text-muted-foreground">
          Manage subtitle styling and video encoding presets
        </p>
      </div>

      <div className="rounded-xl border border-border bg-card p-8">
        <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
          <Palette className="mb-3 h-8 w-8" />
          <p className="text-sm">Presets management coming in Phase 4</p>
        </div>
      </div>
    </div>
  );
}
