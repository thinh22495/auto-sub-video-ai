"use client";

import { useRef, useEffect } from "react";
import type { SubtitleStyle } from "@/lib/types";

interface SubtitlePreviewProps {
  style: SubtitleStyle;
  sampleText?: string;
  width?: number;
  height?: number;
}

const DEFAULT_SAMPLE = "Đây là phụ đề mẫu\nvới hai dòng văn bản";

export function SubtitlePreview({
  style,
  sampleText = DEFAULT_SAMPLE,
  width = 640,
  height = 360,
}: SubtitlePreviewProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    // Set canvas resolution for crisp rendering
    const dpr = window.devicePixelRatio || 1;
    canvas.width = width * dpr;
    canvas.height = height * dpr;
    ctx.scale(dpr, dpr);

    // Draw video-like background
    const gradient = ctx.createLinearGradient(0, 0, 0, height);
    gradient.addColorStop(0, "#1a1a2e");
    gradient.addColorStop(0.5, "#16213e");
    gradient.addColorStop(1, "#0f3460");
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, width, height);

    // Draw subtle grid pattern
    ctx.strokeStyle = "rgba(255, 255, 255, 0.03)";
    ctx.lineWidth = 1;
    for (let x = 0; x < width; x += 40) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, height);
      ctx.stroke();
    }
    for (let y = 0; y < height; y += 40) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(width, y);
      ctx.stroke();
    }

    // Scale factors (ASS uses PlayRes 1920x1080, we scale to canvas)
    const scaleX = width / 1920;
    const scaleY = height / 1080;
    const fontSize = style.font_size * Math.min(scaleX, scaleY) * 2.5;

    // Build font string
    const fontWeight = style.bold ? "bold" : "normal";
    const fontStyle = style.italic ? "italic" : "normal";
    ctx.font = `${fontStyle} ${fontWeight} ${fontSize}px "${style.font_name}", Arial, sans-serif`;
    ctx.textBaseline = "alphabetic";

    // Calculate text position based on alignment (SSA numpad)
    const lines = sampleText.split("\n");
    const lineHeight = fontSize * 1.3;
    const textMetrics = lines.map((line) => ctx.measureText(line));
    const maxWidth = Math.max(...textMetrics.map((m) => m.width));
    const totalHeight = lines.length * lineHeight;

    // Margins scaled
    const marginL = style.margin_left * scaleX;
    const marginR = style.margin_right * scaleX;
    const marginV = style.margin_vertical * scaleY;

    // Horizontal alignment: 1,4,7=left  2,5,8=center  3,6,9=right
    let textX: number;
    const alignCol = ((style.alignment - 1) % 3); // 0=left, 1=center, 2=right
    if (alignCol === 0) {
      ctx.textAlign = "left";
      textX = marginL;
    } else if (alignCol === 1) {
      ctx.textAlign = "center";
      textX = width / 2;
    } else {
      ctx.textAlign = "right";
      textX = width - marginR;
    }

    // Vertical alignment: 1-3=bottom  4-6=middle  7-9=top
    let baseY: number;
    const alignRow = Math.floor((style.alignment - 1) / 3); // 0=bottom, 1=middle, 2=top
    if (alignRow === 0) {
      baseY = height - marginV - (lines.length - 1) * lineHeight;
    } else if (alignRow === 1) {
      baseY = (height - totalHeight) / 2 + fontSize;
    } else {
      baseY = marginV + fontSize;
    }

    // Draw each line with outline/shadow
    lines.forEach((line, i) => {
      const y = baseY + i * lineHeight;

      // Shadow
      if (style.shadow_depth > 0) {
        const shadowOffset = style.shadow_depth * scaleX * 1.5;
        ctx.fillStyle = style.shadow_color;
        ctx.globalAlpha = 0.7;
        ctx.fillText(line, textX + shadowOffset, y + shadowOffset);
        ctx.globalAlpha = 1;
      }

      // Outline (drawn by stroking text)
      if (style.outline_width > 0) {
        ctx.strokeStyle = style.outline_color;
        ctx.lineWidth = style.outline_width * scaleX * 2;
        ctx.lineJoin = "round";
        ctx.strokeText(line, textX, y);
      }

      // Primary text
      ctx.fillStyle = style.primary_color;
      ctx.fillText(line, textX, y);
    });

    // Draw safe area indicator
    ctx.strokeStyle = "rgba(255, 255, 255, 0.1)";
    ctx.lineWidth = 1;
    ctx.setLineDash([4, 4]);
    ctx.strokeRect(marginL, marginV, width - marginL - marginR, height - marginV * 2);
    ctx.setLineDash([]);
  }, [style, sampleText, width, height]);

  return (
    <div className="overflow-hidden rounded-lg border border-border">
      <canvas
        ref={canvasRef}
        style={{ width, height }}
        className="block"
      />
    </div>
  );
}
