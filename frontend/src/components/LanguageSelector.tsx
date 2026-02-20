"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api-client";
import { Globe } from "lucide-react";

interface Language {
  code: string;
  name: string;
}

interface LanguageSelectorProps {
  value: string;
  onChange: (value: string) => void;
  label: string;
  allowAuto?: boolean;
  allowNone?: boolean;
  noneLabel?: string;
}

// Cache languages to avoid refetching
let cachedLanguages: Language[] | null = null;

export function LanguageSelector({
  value,
  onChange,
  label,
  allowAuto = false,
  allowNone = false,
  noneLabel = "No translation",
}: LanguageSelectorProps) {
  const [languages, setLanguages] = useState<Language[]>(cachedLanguages || []);

  useEffect(() => {
    if (cachedLanguages) return;
    api
      .get<Language[]>("/languages")
      .then((data) => {
        cachedLanguages = data;
        setLanguages(data);
      })
      .catch(() => {});
  }, []);

  // Group languages by first letter for easier navigation
  const popular = ["en", "vi", "ja", "ko", "zh", "es", "fr", "de", "pt", "ru", "ar", "hi", "th", "id"];

  const popularLangs = languages.filter((l) => popular.includes(l.code));
  const otherLangs = languages.filter((l) => !popular.includes(l.code));

  return (
    <div>
      <label className="mb-1 flex items-center gap-1.5 text-sm font-medium text-muted-foreground">
        <Globe className="h-3.5 w-3.5" />
        {label}
      </label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full rounded-lg border border-border bg-muted px-4 py-2.5 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
      >
        {allowAuto && <option value="auto">Auto-detect</option>}
        {allowNone && <option value="">{noneLabel}</option>}

        {popularLangs.length > 0 && (
          <optgroup label="Popular">
            {popularLangs.map((lang) => (
              <option key={lang.code} value={lang.code}>
                {lang.name} ({lang.code})
              </option>
            ))}
          </optgroup>
        )}

        {otherLangs.length > 0 && (
          <optgroup label="All Languages">
            {otherLangs.map((lang) => (
              <option key={lang.code} value={lang.code}>
                {lang.name} ({lang.code})
              </option>
            ))}
          </optgroup>
        )}
      </select>
    </div>
  );
}
