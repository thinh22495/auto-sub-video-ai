"use client";

import { useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api-client";
import type { Preset, SubtitleStyle } from "@/lib/types";
import { SubtitleStyler } from "@/components/SubtitleStyler";
import { SubtitlePreview } from "@/components/SubtitlePreview";
import {
  Palette,
  Plus,
  Copy,
  Trash2,
  Save,
  X,
  CheckCircle2,
  Loader2,
  Lock,
  Pencil,
} from "lucide-react";
import { cn } from "@/lib/utils";

const DEFAULT_STYLE: SubtitleStyle = {
  font_name: "Arial",
  font_size: 24,
  primary_color: "#FFFFFF",
  secondary_color: "#FFFF00",
  outline_color: "#000000",
  shadow_color: "#000000",
  outline_width: 2.0,
  shadow_depth: 1.0,
  alignment: 2,
  margin_left: 10,
  margin_right: 10,
  margin_vertical: 30,
  bold: false,
  italic: false,
  max_line_length: 42,
  max_lines: 2,
};

export default function PresetsPage() {
  const [presets, setPresets] = useState<Preset[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [editingStyle, setEditingStyle] = useState<SubtitleStyle>(DEFAULT_STYLE);
  const [editingName, setEditingName] = useState("");
  const [editingDesc, setEditingDesc] = useState("");
  const [isCreating, setIsCreating] = useState(false);
  const [saving, setSaving] = useState(false);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const fetchPresets = useCallback(async () => {
    try {
      const data = await api.get<Preset[]>("/presets");
      setPresets(data);
    } catch (err) {
      console.error("Failed to fetch presets:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPresets();
  }, [fetchPresets]);

  const selectedPreset = presets.find((p) => p.id === selectedId);

  const handleSelect = (preset: Preset) => {
    setSelectedId(preset.id);
    setEditingStyle({ ...DEFAULT_STYLE, ...preset.subtitle_style });
    setEditingName(preset.name);
    setEditingDesc(preset.description || "");
    setIsCreating(false);
  };

  const handleNewPreset = () => {
    setSelectedId(null);
    setEditingStyle({ ...DEFAULT_STYLE });
    setEditingName("Mẫu của tôi");
    setEditingDesc("");
    setIsCreating(true);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      if (isCreating) {
        await api.post("/presets", {
          name: editingName,
          description: editingDesc || null,
          subtitle_style: editingStyle,
        });
      } else if (selectedId && !selectedId.startsWith("builtin_")) {
        await api.put(`/presets/${selectedId}`, {
          name: editingName,
          description: editingDesc || null,
          subtitle_style: editingStyle,
        });
      }
      await fetchPresets();
      setIsCreating(false);
    } catch (err: any) {
      alert(`Lưu thất bại: ${err.message}`);
    } finally {
      setSaving(false);
    }
  };

  const handleDuplicate = async (presetId: string) => {
    setActionLoading(presetId);
    try {
      const newPreset = await api.post<Preset>(
        `/presets/${presetId}/duplicate`,
        {}
      );
      await fetchPresets();
      handleSelect(newPreset);
    } catch (err: any) {
      alert(`Nhân bản thất bại: ${err.message}`);
    } finally {
      setActionLoading(null);
    }
  };

  const handleDelete = async (presetId: string) => {
    if (!confirm("Xóa mẫu này?")) return;
    setActionLoading(presetId);
    try {
      await api.delete(`/presets/${presetId}`);
      if (selectedId === presetId) {
        setSelectedId(null);
        setIsCreating(false);
      }
      await fetchPresets();
    } catch (err: any) {
      alert(`Xóa thất bại: ${err.message}`);
    } finally {
      setActionLoading(null);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  const builtinPresets = presets.filter((p) => p.is_builtin);
  const userPresets = presets.filter((p) => !p.is_builtin);
  const isEditable =
    isCreating || (selectedId && !selectedId.startsWith("builtin_"));

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Mẫu phụ đề</h1>
          <p className="text-sm text-muted-foreground">
            Quản lý kiểu dáng phụ đề và các mẫu mã hóa video
          </p>
        </div>
        <button
          onClick={handleNewPreset}
          className="flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
        >
          <Plus className="h-4 w-4" />
          Tạo mới
        </button>
      </div>

      <div className="grid grid-cols-12 gap-6">
        {/* Preset List (left sidebar) */}
        <div className="col-span-4 space-y-4">
          {/* Built-in Presets */}
          <div>
            <h3 className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              <Lock className="h-3 w-3" />
              Có sẵn
            </h3>
            <div className="space-y-1.5">
              {builtinPresets.map((preset) => (
                <PresetCard
                  key={preset.id}
                  preset={preset}
                  selected={selectedId === preset.id}
                  loading={actionLoading === preset.id}
                  onSelect={() => handleSelect(preset)}
                  onDuplicate={() => handleDuplicate(preset.id)}
                />
              ))}
            </div>
          </div>

          {/* User Presets */}
          <div>
            <h3 className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              <Pencil className="h-3 w-3" />
              Tùy chỉnh ({userPresets.length})
            </h3>
            {userPresets.length === 0 ? (
              <p className="py-3 text-center text-xs text-muted-foreground">
                Chưa có mẫu tùy chỉnh. Nhấn &quot;Tạo mới&quot; hoặc nhân bản
                từ mẫu có sẵn.
              </p>
            ) : (
              <div className="space-y-1.5">
                {userPresets.map((preset) => (
                  <PresetCard
                    key={preset.id}
                    preset={preset}
                    selected={selectedId === preset.id}
                    loading={actionLoading === preset.id}
                    onSelect={() => handleSelect(preset)}
                    onDuplicate={() => handleDuplicate(preset.id)}
                    onDelete={() => handleDelete(preset.id)}
                  />
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Editor + Preview (right) */}
        <div className="col-span-8">
          {!selectedId && !isCreating ? (
            <div className="flex flex-col items-center justify-center rounded-xl border border-border bg-card py-20 text-muted-foreground">
              <Palette className="mb-3 h-8 w-8" />
              <p className="text-sm">Chọn một mẫu hoặc tạo mẫu mới</p>
            </div>
          ) : (
            <div className="space-y-4">
              {/* Preview */}
              <div className="rounded-xl border border-border bg-card p-4">
                <h3 className="mb-3 text-sm font-semibold text-foreground">
                  Xem trước trực tiếp
                </h3>
                <div className="flex justify-center">
                  <SubtitlePreview style={editingStyle} />
                </div>
              </div>

              {/* Name & Description (editable only for custom presets) */}
              {isEditable && (
                <div className="rounded-xl border border-border bg-card p-4">
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="mb-1 block text-xs text-muted-foreground">
                        Tên
                      </label>
                      <input
                        type="text"
                        value={editingName}
                        onChange={(e) => setEditingName(e.target.value)}
                        className="w-full rounded-lg border border-border bg-muted px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none"
                      />
                    </div>
                    <div>
                      <label className="mb-1 block text-xs text-muted-foreground">
                        Mô tả
                      </label>
                      <input
                        type="text"
                        value={editingDesc}
                        onChange={(e) => setEditingDesc(e.target.value)}
                        placeholder="Mô tả (tùy chọn)"
                        className="w-full rounded-lg border border-border bg-muted px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none"
                      />
                    </div>
                  </div>
                </div>
              )}

              {/* Style Editor */}
              <div className="rounded-xl border border-border bg-card p-4">
                <h3 className="mb-4 text-sm font-semibold text-foreground">
                  Cài đặt kiểu dáng
                  {!isEditable && (
                    <span className="ml-2 text-xs font-normal text-muted-foreground">
                      (chỉ đọc — nhân bản để tùy chỉnh)
                    </span>
                  )}
                </h3>
                <div className={cn(!isEditable && "pointer-events-none opacity-60")}>
                  <SubtitleStyler
                    style={editingStyle}
                    onChange={setEditingStyle}
                  />
                </div>
              </div>

              {/* Action buttons */}
              {isEditable && (
                <div className="flex gap-2">
                  <button
                    onClick={handleSave}
                    disabled={saving || !editingName.trim()}
                    className="flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90 disabled:opacity-50"
                  >
                    {saving ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Save className="h-4 w-4" />
                    )}
                    {isCreating ? "Tạo mẫu" : "Lưu thay đổi"}
                  </button>
                  <button
                    onClick={() => {
                      setSelectedId(null);
                      setIsCreating(false);
                    }}
                    className="flex items-center gap-2 rounded-lg border border-border px-4 py-2 text-sm text-foreground transition-colors hover:bg-muted"
                  >
                    <X className="h-4 w-4" />
                    Hủy
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function PresetCard({
  preset,
  selected,
  loading,
  onSelect,
  onDuplicate,
  onDelete,
}: {
  preset: Preset;
  selected: boolean;
  loading: boolean;
  onSelect: () => void;
  onDuplicate: () => void;
  onDelete?: () => void;
}) {
  return (
    <div
      onClick={onSelect}
      className={cn(
        "cursor-pointer rounded-lg border p-3 transition-colors",
        selected
          ? "border-primary bg-primary/5"
          : "border-border bg-card hover:border-foreground/20"
      )}
    >
      <div className="flex items-start justify-between">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-1.5">
            <span className="truncate text-sm font-medium text-foreground">
              {preset.name}
            </span>
            {preset.is_builtin && (
              <Lock className="h-3 w-3 flex-shrink-0 text-muted-foreground" />
            )}
          </div>
          {preset.description && (
            <p className="mt-0.5 truncate text-xs text-muted-foreground">
              {preset.description}
            </p>
          )}
        </div>

        {loading ? (
          <Loader2 className="h-4 w-4 flex-shrink-0 animate-spin text-primary" />
        ) : (
          <div className="flex flex-shrink-0 gap-1" onClick={(e) => e.stopPropagation()}>
            <button
              onClick={onDuplicate}
              title="Nhân bản"
              className="rounded p-1 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
            >
              <Copy className="h-3.5 w-3.5" />
            </button>
            {onDelete && (
              <button
                onClick={onDelete}
                title="Xóa"
                className="rounded p-1 text-muted-foreground transition-colors hover:bg-danger/10 hover:text-danger"
              >
                <Trash2 className="h-3.5 w-3.5" />
              </button>
            )}
          </div>
        )}
      </div>

      {/* Mini style preview */}
      <div className="mt-2 flex gap-2">
        <div
          className="h-4 w-4 rounded-sm border border-white/10"
          style={{ backgroundColor: preset.subtitle_style.primary_color }}
          title="Màu chính"
        />
        <span className="text-[10px] text-muted-foreground">
          {preset.subtitle_style.font_name} {preset.subtitle_style.font_size}px
        </span>
      </div>
    </div>
  );
}
