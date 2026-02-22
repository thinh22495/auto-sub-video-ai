"use client";

import { useState, useEffect, useCallback } from "react";
import { api } from "@/lib/api-client";

export interface AppSetting {
  type: "text" | "number" | "float" | "select";
  label: string;
  description: string;
  default: string;
  value: string;
  options?: string[];
  min?: number;
  max?: number;
  category: string;
}

export type SettingsMap = Record<string, AppSetting>;

export function useSettings() {
  const [settings, setSettings] = useState<SettingsMap>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchSettings = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.get<SettingsMap>("/settings");
      setSettings(data);
    } catch (err: any) {
      setError(err.message || "Không thể tải cài đặt");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSettings();
  }, [fetchSettings]);

  const updateSetting = useCallback(
    async (key: string, value: string) => {
      setSaving(true);
      try {
        await api.put(`/settings/${key}`, { key, value });
        setSettings((prev) => ({
          ...prev,
          [key]: { ...prev[key], value },
        }));
      } catch (err: any) {
        setError(err.message || "Không thể lưu cài đặt");
        throw err;
      } finally {
        setSaving(false);
      }
    },
    []
  );

  const updateBulk = useCallback(
    async (updates: Record<string, string>) => {
      setSaving(true);
      try {
        await api.put("/settings", { settings: updates });
        setSettings((prev) => {
          const next = { ...prev };
          for (const [key, value] of Object.entries(updates)) {
            if (next[key]) {
              next[key] = { ...next[key], value };
            }
          }
          return next;
        });
      } catch (err: any) {
        setError(err.message || "Không thể lưu cài đặt");
        throw err;
      } finally {
        setSaving(false);
      }
    },
    []
  );

  const resetToDefaults = useCallback(async () => {
    const defaults: Record<string, string> = {};
    for (const [key, setting] of Object.entries(settings)) {
      defaults[key] = setting.default;
    }
    await updateBulk(defaults);
  }, [settings, updateBulk]);

  return {
    settings,
    loading,
    saving,
    error,
    fetchSettings,
    updateSetting,
    updateBulk,
    resetToDefaults,
  };
}
