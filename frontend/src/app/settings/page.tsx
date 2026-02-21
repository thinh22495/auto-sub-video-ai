"use client";

import { useState, useEffect } from "react";
import { api } from "@/lib/api-client";
import { useSettings, type AppSetting } from "@/hooks/useSettings";
import {
  Settings,
  Save,
  RotateCcw,
  Loader2,
  Cpu,
  Subtitles,
  Cog,
  Trash2,
  FolderOpen,
  HardDrive,
  CheckCircle2,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface DirectoryInfo {
  video_input_dir: string;
  subtitle_output_dir: string;
  video_output_dir: string;
  model_dir: string;
  temp_dir: string;
  db_path: string;
}

interface DiskInfo {
  total_gb: number;
  free_gb: number;
  used_gb: number;
  used_percent: number;
}

const CATEGORY_META: Record<string, { icon: React.ReactNode; label: string }> =
  {
    models: { icon: <Cpu className="h-4 w-4" />, label: "AI Models" },
    subtitles: {
      icon: <Subtitles className="h-4 w-4" />,
      label: "Subtitle Defaults",
    },
    processing: { icon: <Cog className="h-4 w-4" />, label: "Processing" },
    cleanup: { icon: <Trash2 className="h-4 w-4" />, label: "Cleanup" },
  };

export default function SettingsPage() {
  const {
    settings: appSettings,
    loading,
    saving,
    updateBulk,
    resetToDefaults,
  } = useSettings();

  const [dirInfo, setDirInfo] = useState<DirectoryInfo | null>(null);
  const [diskUsage, setDiskUsage] = useState<Record<string, DiskInfo> | null>(
    null
  );
  const [localValues, setLocalValues] = useState<Record<string, string>>({});
  const [dirty, setDirty] = useState(false);
  const [saved, setSaved] = useState(false);

  // Initialize local values from fetched settings
  useEffect(() => {
    const vals: Record<string, string> = {};
    for (const [key, setting] of Object.entries(appSettings)) {
      vals[key] = setting.value;
    }
    setLocalValues(vals);
    setDirty(false);
  }, [appSettings]);

  // Fetch directory info and disk usage
  useEffect(() => {
    api
      .get<DirectoryInfo>("/settings/directories/info")
      .then(setDirInfo)
      .catch(() => {});
    api
      .get<Record<string, DiskInfo>>("/files/disk")
      .then(setDiskUsage)
      .catch(() => {});
  }, []);

  const handleChange = (key: string, value: string) => {
    setLocalValues((prev) => ({ ...prev, [key]: value }));
    setDirty(true);
    setSaved(false);
  };

  const handleSave = async () => {
    try {
      // Only send changed values
      const changes: Record<string, string> = {};
      for (const [key, value] of Object.entries(localValues)) {
        if (appSettings[key] && appSettings[key].value !== value) {
          changes[key] = value;
        }
      }
      if (Object.keys(changes).length > 0) {
        await updateBulk(changes);
      }
      setDirty(false);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch {
      // error is handled in hook
    }
  };

  const handleReset = async () => {
    if (!confirm("Reset all settings to their default values?")) return;
    await resetToDefaults();
    setDirty(false);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  // Group settings by category
  const categories: Record<string, [string, AppSetting][]> = {};
  for (const [key, setting] of Object.entries(appSettings)) {
    const cat = setting.category || "other";
    if (!categories[cat]) categories[cat] = [];
    categories[cat].push([key, setting]);
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Settings</h1>
          <p className="text-sm text-muted-foreground">
            Configure output directories, defaults, and application settings
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={handleReset}
            className="flex items-center gap-2 rounded-lg border border-border px-3 py-2 text-sm text-foreground transition-colors hover:bg-muted"
          >
            <RotateCcw className="h-4 w-4" />
            Reset
          </button>
          <button
            onClick={handleSave}
            disabled={!dirty || saving}
            className={cn(
              "flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-colors disabled:opacity-50",
              saved
                ? "bg-success text-success-foreground"
                : "bg-primary text-primary-foreground hover:bg-primary/90"
            )}
          >
            {saving ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : saved ? (
              <CheckCircle2 className="h-4 w-4" />
            ) : (
              <Save className="h-4 w-4" />
            )}
            {saved ? "Saved" : "Save Changes"}
          </button>
        </div>
      </div>

      {/* Settings categories */}
      {Object.entries(categories).map(([category, entries]) => {
        const meta = CATEGORY_META[category] || {
          icon: <Settings className="h-4 w-4" />,
          label: category,
        };
        return (
          <section
            key={category}
            className="rounded-xl border border-border bg-card p-6"
          >
            <h2 className="mb-4 flex items-center gap-2 text-base font-semibold text-foreground">
              <span className="text-primary">{meta.icon}</span>
              {meta.label}
            </h2>
            <div className="space-y-4">
              {entries.map(([key, setting]) => (
                <SettingField
                  key={key}
                  settingKey={key}
                  setting={setting}
                  value={localValues[key] ?? setting.value}
                  onChange={(val) => handleChange(key, val)}
                />
              ))}
            </div>
          </section>
        );
      })}

      {/* Directories (read-only, from .env) */}
      <section className="rounded-xl border border-border bg-card p-6">
        <h2 className="mb-4 flex items-center gap-2 text-base font-semibold text-foreground">
          <span className="text-primary">
            <FolderOpen className="h-4 w-4" />
          </span>
          Directories
          <span className="text-xs font-normal text-muted-foreground">
            (configured via .env — read only)
          </span>
        </h2>
        {dirInfo && (
          <div className="space-y-3">
            {[
              {
                label: "Video Input",
                path: dirInfo.video_input_dir,
                disk: diskUsage?.videos,
              },
              {
                label: "Subtitle Output",
                path: dirInfo.subtitle_output_dir,
                disk: diskUsage?.subtitles,
              },
              {
                label: "Video Output",
                path: dirInfo.video_output_dir,
                disk: diskUsage?.output,
              },
              {
                label: "Models",
                path: dirInfo.model_dir,
                disk: diskUsage?.models,
              },
              { label: "Temp", path: dirInfo.temp_dir },
              { label: "Database", path: dirInfo.db_path },
            ].map((dir) => (
              <div key={dir.label} className="flex items-center gap-3">
                <span className="w-28 text-xs font-medium text-muted-foreground">
                  {dir.label}
                </span>
                <code className="flex-1 rounded bg-muted px-3 py-1.5 text-xs text-foreground">
                  {dir.path}
                </code>
                {dir.disk && (
                  <div className="flex items-center gap-2">
                    <div className="h-1.5 w-20 overflow-hidden rounded-full bg-muted">
                      <div
                        className={cn(
                          "h-full rounded-full transition-all",
                          dir.disk.used_percent > 90
                            ? "bg-danger"
                            : dir.disk.used_percent > 70
                              ? "bg-warning"
                              : "bg-primary"
                        )}
                        style={{ width: `${dir.disk.used_percent}%` }}
                      />
                    </div>
                    <span className="text-[10px] text-muted-foreground">
                      {dir.disk.free_gb}GB free
                    </span>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </section>

      {/* System info */}
      <section className="rounded-xl border border-border bg-card p-6">
        <h2 className="mb-4 flex items-center gap-2 text-base font-semibold text-foreground">
          <span className="text-primary">
            <HardDrive className="h-4 w-4" />
          </span>
          System
        </h2>
        <div className="grid grid-cols-2 gap-3 text-xs">
          <div className="rounded-lg border border-border bg-muted p-3">
            <div className="text-muted-foreground">Version</div>
            <div className="mt-0.5 font-medium text-foreground">
              AutoSubAI v0.1.0
            </div>
          </div>
          <div className="rounded-lg border border-border bg-muted p-3">
            <div className="text-muted-foreground">Container</div>
            <div className="mt-0.5 font-medium text-foreground">Docker</div>
          </div>
        </div>
      </section>
    </div>
  );
}

function SettingField({
  settingKey,
  setting,
  value,
  onChange,
}: {
  settingKey: string;
  setting: AppSetting;
  value: string;
  onChange: (value: string) => void;
}) {
  const isChanged = value !== setting.value;

  return (
    <div className="flex items-start gap-4">
      <div className="min-w-0 flex-1">
        <label className="flex items-center gap-2 text-sm font-medium text-foreground">
          {setting.label}
          {isChanged && (
            <span className="rounded bg-warning/10 px-1.5 py-0.5 text-[10px] text-warning">
              modified
            </span>
          )}
        </label>
        <p className="mt-0.5 text-xs text-muted-foreground">
          {setting.description}
        </p>
      </div>
      <div className="w-48 flex-shrink-0">
        {setting.type === "select" && setting.options ? (
          <select
            value={value}
            onChange={(e) => onChange(e.target.value)}
            className="w-full rounded-lg border border-border bg-muted px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none"
          >
            {setting.options.map((opt) => (
              <option key={opt} value={opt}>
                {opt}
              </option>
            ))}
          </select>
        ) : setting.type === "number" ? (
          <input
            type="number"
            value={value}
            min={setting.min}
            max={setting.max}
            onChange={(e) => onChange(e.target.value)}
            className="w-full rounded-lg border border-border bg-muted px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none"
          />
        ) : (
          <input
            type="text"
            value={value}
            onChange={(e) => onChange(e.target.value)}
            className="w-full rounded-lg border border-border bg-muted px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none"
          />
        )}
      </div>
    </div>
  );
}
