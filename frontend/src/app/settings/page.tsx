"use client";

import { Settings } from "lucide-react";

export default function SettingsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground">Settings</h1>
        <p className="text-sm text-muted-foreground">
          Configure output directories, defaults, and application settings
        </p>
      </div>

      <div className="rounded-xl border border-border bg-card p-8">
        <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
          <Settings className="mb-3 h-8 w-8" />
          <p className="text-sm">Settings page coming in Phase 5</p>
        </div>
      </div>
    </div>
  );
}
