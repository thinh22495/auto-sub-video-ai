"use client";

import { useCallback } from "react";
import type { SubtitleStyle } from "@/lib/types";
import {
  Type,
  Palette,
  AlignHorizontalJustifyCenter,
  Bold,
  Italic,
  Move,
} from "lucide-react";

interface SubtitleStylerProps {
  style: SubtitleStyle;
  onChange: (style: SubtitleStyle) => void;
}

const FONT_OPTIONS = [
  "Arial",
  "Roboto",
  "Trebuchet MS",
  "Verdana",
  "Tahoma",
  "Georgia",
  "Times New Roman",
  "Courier New",
  "Impact",
  "Comic Sans MS",
];

const ALIGNMENT_OPTIONS = [
  { value: 7, label: "↖" },
  { value: 8, label: "↑" },
  { value: 9, label: "↗" },
  { value: 4, label: "←" },
  { value: 5, label: "·" },
  { value: 6, label: "→" },
  { value: 1, label: "↙" },
  { value: 2, label: "↓" },
  { value: 3, label: "↘" },
];

export function SubtitleStyler({ style, onChange }: SubtitleStylerProps) {
  const update = useCallback(
    <K extends keyof SubtitleStyle>(key: K, value: SubtitleStyle[K]) => {
      onChange({ ...style, [key]: value });
    },
    [style, onChange]
  );

  return (
    <div className="space-y-6">
      {/* Font Settings */}
      <StyleSection icon={<Type className="h-4 w-4" />} title="Font">
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="mb-1 block text-xs text-muted-foreground">
              Font Family
            </label>
            <select
              value={style.font_name}
              onChange={(e) => update("font_name", e.target.value)}
              className="w-full rounded-lg border border-border bg-muted px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none"
            >
              {FONT_OPTIONS.map((f) => (
                <option key={f} value={f}>
                  {f}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-xs text-muted-foreground">
              Font Size
            </label>
            <input
              type="number"
              min={8}
              max={72}
              value={style.font_size}
              onChange={(e) => update("font_size", Number(e.target.value))}
              className="w-full rounded-lg border border-border bg-muted px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none"
            />
          </div>
        </div>

        <div className="mt-3 flex gap-2">
          <button
            type="button"
            onClick={() => update("bold", !style.bold)}
            className={`flex h-9 w-9 items-center justify-center rounded-lg border text-sm transition-colors ${
              style.bold
                ? "border-primary bg-primary/10 text-primary"
                : "border-border bg-muted text-muted-foreground hover:border-foreground/30"
            }`}
          >
            <Bold className="h-4 w-4" />
          </button>
          <button
            type="button"
            onClick={() => update("italic", !style.italic)}
            className={`flex h-9 w-9 items-center justify-center rounded-lg border text-sm transition-colors ${
              style.italic
                ? "border-primary bg-primary/10 text-primary"
                : "border-border bg-muted text-muted-foreground hover:border-foreground/30"
            }`}
          >
            <Italic className="h-4 w-4" />
          </button>
        </div>
      </StyleSection>

      {/* Colors */}
      <StyleSection icon={<Palette className="h-4 w-4" />} title="Colors">
        <div className="grid grid-cols-2 gap-3">
          <ColorInput
            label="Primary"
            value={style.primary_color}
            onChange={(v) => update("primary_color", v)}
          />
          <ColorInput
            label="Secondary"
            value={style.secondary_color}
            onChange={(v) => update("secondary_color", v)}
          />
          <ColorInput
            label="Outline"
            value={style.outline_color}
            onChange={(v) => update("outline_color", v)}
          />
          <ColorInput
            label="Shadow"
            value={style.shadow_color}
            onChange={(v) => update("shadow_color", v)}
          />
        </div>
      </StyleSection>

      {/* Outline & Shadow */}
      <StyleSection
        icon={<Type className="h-4 w-4" />}
        title="Outline & Shadow"
      >
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="mb-1 block text-xs text-muted-foreground">
              Outline Width
            </label>
            <input
              type="range"
              min={0}
              max={6}
              step={0.5}
              value={style.outline_width}
              onChange={(e) => update("outline_width", Number(e.target.value))}
              className="w-full accent-primary"
            />
            <span className="text-xs text-muted-foreground">
              {style.outline_width}px
            </span>
          </div>
          <div>
            <label className="mb-1 block text-xs text-muted-foreground">
              Shadow Depth
            </label>
            <input
              type="range"
              min={0}
              max={6}
              step={0.5}
              value={style.shadow_depth}
              onChange={(e) => update("shadow_depth", Number(e.target.value))}
              className="w-full accent-primary"
            />
            <span className="text-xs text-muted-foreground">
              {style.shadow_depth}px
            </span>
          </div>
        </div>
      </StyleSection>

      {/* Alignment */}
      <StyleSection
        icon={<AlignHorizontalJustifyCenter className="h-4 w-4" />}
        title="Alignment"
      >
        <div className="inline-grid grid-cols-3 gap-1">
          {ALIGNMENT_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              type="button"
              onClick={() => update("alignment", opt.value)}
              className={`flex h-8 w-8 items-center justify-center rounded text-xs transition-colors ${
                style.alignment === opt.value
                  ? "bg-primary text-primary-foreground"
                  : "bg-muted text-muted-foreground hover:bg-muted/80"
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </StyleSection>

      {/* Margins */}
      <StyleSection icon={<Move className="h-4 w-4" />} title="Margins">
        <div className="grid grid-cols-3 gap-3">
          <div>
            <label className="mb-1 block text-xs text-muted-foreground">
              Left
            </label>
            <input
              type="number"
              min={0}
              max={200}
              value={style.margin_left}
              onChange={(e) => update("margin_left", Number(e.target.value))}
              className="w-full rounded-lg border border-border bg-muted px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs text-muted-foreground">
              Right
            </label>
            <input
              type="number"
              min={0}
              max={200}
              value={style.margin_right}
              onChange={(e) => update("margin_right", Number(e.target.value))}
              className="w-full rounded-lg border border-border bg-muted px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs text-muted-foreground">
              Vertical
            </label>
            <input
              type="number"
              min={0}
              max={200}
              value={style.margin_vertical}
              onChange={(e) =>
                update("margin_vertical", Number(e.target.value))
              }
              className="w-full rounded-lg border border-border bg-muted px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none"
            />
          </div>
        </div>
      </StyleSection>

      {/* Text Constraints */}
      <StyleSection
        icon={<Type className="h-4 w-4" />}
        title="Text Constraints"
      >
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="mb-1 block text-xs text-muted-foreground">
              Max Line Length
            </label>
            <input
              type="number"
              min={20}
              max={80}
              value={style.max_line_length}
              onChange={(e) =>
                update("max_line_length", Number(e.target.value))
              }
              className="w-full rounded-lg border border-border bg-muted px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs text-muted-foreground">
              Max Lines
            </label>
            <input
              type="number"
              min={1}
              max={4}
              value={style.max_lines}
              onChange={(e) => update("max_lines", Number(e.target.value))}
              className="w-full rounded-lg border border-border bg-muted px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none"
            />
          </div>
        </div>
      </StyleSection>
    </div>
  );
}

function StyleSection({
  icon,
  title,
  children,
}: {
  icon: React.ReactNode;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <div className="mb-2 flex items-center gap-1.5 text-sm font-medium text-foreground">
        <span className="text-primary">{icon}</span>
        {title}
      </div>
      {children}
    </div>
  );
}

function ColorInput({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <div>
      <label className="mb-1 block text-xs text-muted-foreground">
        {label}
      </label>
      <div className="flex items-center gap-2">
        <input
          type="color"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="h-8 w-8 cursor-pointer rounded border border-border bg-transparent"
        />
        <input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="flex-1 rounded-lg border border-border bg-muted px-3 py-1.5 text-xs font-mono text-foreground focus:border-primary focus:outline-none"
        />
      </div>
    </div>
  );
}
