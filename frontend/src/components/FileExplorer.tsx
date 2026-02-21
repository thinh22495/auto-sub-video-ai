"use client";

import { useState, useEffect, useCallback } from "react";
import { api } from "@/lib/api-client";
import {
  Folder,
  FolderOpen,
  FileVideo,
  FileText,
  File,
  ChevronRight,
  ArrowUp,
  Home,
  Loader2,
  Music,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface FileItem {
  name: string;
  path: string;
  is_dir: boolean;
  size_bytes: number;
  modified: number;
  type: "directory" | "video" | "subtitle" | "audio" | "other";
}

interface BrowseResult {
  path: string;
  parent: string | null;
  items: FileItem[];
}

interface RootDir {
  name: string;
  path: string;
  description: string;
  exists: boolean;
  file_count: number;
}

interface FileExplorerProps {
  onSelect?: (path: string) => void;
  filterType?: "video" | "subtitle" | "audio" | null;
  initialPath?: string;
  className?: string;
}

export function FileExplorer({
  onSelect,
  filterType = null,
  initialPath,
  className = "",
}: FileExplorerProps) {
  const [roots, setRoots] = useState<RootDir[]>([]);
  const [currentPath, setCurrentPath] = useState<string | null>(
    initialPath || null
  );
  const [items, setItems] = useState<FileItem[]>([]);
  const [parentPath, setParentPath] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedPath, setSelectedPath] = useState<string | null>(null);

  // Fetch root directories
  useEffect(() => {
    api
      .get<RootDir[]>("/files/roots")
      .then(setRoots)
      .catch(() => {});
  }, []);

  const browse = useCallback(
    async (path: string | null) => {
      setLoading(true);
      setError(null);
      try {
        const params: Record<string, string> = {};
        if (path) params.path = path;

        const result = await api.get<BrowseResult>("/files/browse", {
          params,
        });
        setCurrentPath(result.path);
        setParentPath(result.parent);

        let filteredItems = result.items;
        if (filterType) {
          filteredItems = result.items.filter(
            (item) => item.is_dir || item.type === filterType
          );
        }
        setItems(filteredItems);
      } catch (err: any) {
        setError(err.message || "Failed to browse directory");
        setItems([]);
      } finally {
        setLoading(false);
      }
    },
    [filterType]
  );

  useEffect(() => {
    if (initialPath || currentPath) {
      browse(initialPath || currentPath);
    } else {
      // Show roots view
      setLoading(false);
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const handleItemClick = (item: FileItem) => {
    if (item.is_dir) {
      browse(item.path);
    } else {
      setSelectedPath(item.path);
      onSelect?.(item.path);
    }
  };

  const handleGoUp = () => {
    if (parentPath) {
      // Check if parent is still within allowed roots
      const isInRoot = roots.some(
        (r) => parentPath.startsWith(r.path) || r.path.startsWith(parentPath)
      );
      if (isInRoot) {
        browse(parentPath);
      } else {
        // Go back to roots view
        setCurrentPath(null);
        setItems([]);
        setParentPath(null);
      }
    } else {
      setCurrentPath(null);
      setItems([]);
    }
  };

  const formatSize = (bytes: number) => {
    if (bytes === 0) return "";
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    if (bytes < 1024 * 1024 * 1024)
      return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
  };

  const getIcon = (item: FileItem) => {
    if (item.is_dir) return <Folder className="h-4 w-4 text-accent" />;
    switch (item.type) {
      case "video":
        return <FileVideo className="h-4 w-4 text-primary" />;
      case "subtitle":
        return <FileText className="h-4 w-4 text-success" />;
      case "audio":
        return <Music className="h-4 w-4 text-warning" />;
      default:
        return <File className="h-4 w-4 text-muted-foreground" />;
    }
  };

  // Roots view
  if (!currentPath && !loading) {
    return (
      <div className={`space-y-2 ${className}`}>
        <div className="mb-2 flex items-center gap-2 text-xs text-muted-foreground">
          <Home className="h-3.5 w-3.5" />
          Duyệt thư mục
        </div>
        {roots.map((root) => (
          <button
            key={root.path}
            onClick={() => browse(root.path)}
            className="flex w-full items-center gap-3 rounded-lg border border-border bg-card p-3 text-left transition-colors hover:border-primary/30 hover:bg-primary/5"
          >
            <FolderOpen className="h-5 w-5 text-accent" />
            <div className="min-w-0 flex-1">
              <div className="text-sm font-medium text-foreground">
                {root.name}
              </div>
              <div className="truncate text-xs text-muted-foreground">
                {root.path}
                {root.file_count > 0 && ` · ${root.file_count} tệp`}
              </div>
            </div>
            <ChevronRight className="h-4 w-4 text-muted-foreground" />
          </button>
        ))}
      </div>
    );
  }

  return (
    <div className={`space-y-2 ${className}`}>
      {/* Breadcrumb / Navigation bar */}
      <div className="flex items-center gap-2 text-xs">
        <button
          onClick={() => {
            setCurrentPath(null);
            setItems([]);
            setParentPath(null);
          }}
          className="text-muted-foreground transition-colors hover:text-foreground"
        >
          <Home className="h-3.5 w-3.5" />
        </button>
        {parentPath && (
          <button
            onClick={handleGoUp}
            className="flex items-center gap-1 text-muted-foreground transition-colors hover:text-foreground"
          >
            <ArrowUp className="h-3.5 w-3.5" />
            Lên
          </button>
        )}
        <span className="flex-1 truncate text-muted-foreground">
          {currentPath}
        </span>
      </div>

      {/* File list */}
      {loading ? (
        <div className="flex items-center justify-center py-8">
          <Loader2 className="h-5 w-5 animate-spin text-primary" />
        </div>
      ) : error ? (
        <div className="rounded-lg border border-danger/30 bg-danger/10 p-3 text-xs text-danger">
          {error}
        </div>
      ) : items.length === 0 ? (
        <div className="py-8 text-center text-xs text-muted-foreground">
          Thư mục trống
        </div>
      ) : (
        <div className="max-h-64 space-y-0.5 overflow-y-auto rounded-lg border border-border">
          {items.map((item) => (
            <button
              key={item.path}
              onClick={() => handleItemClick(item)}
              className={cn(
                "flex w-full items-center gap-2.5 px-3 py-2 text-left text-sm transition-colors hover:bg-muted",
                selectedPath === item.path && "bg-primary/10"
              )}
            >
              {getIcon(item)}
              <span className="min-w-0 flex-1 truncate text-foreground">
                {item.name}
              </span>
              {!item.is_dir && (
                <span className="flex-shrink-0 text-xs text-muted-foreground">
                  {formatSize(item.size_bytes)}
                </span>
              )}
              {item.is_dir && (
                <ChevronRight className="h-3.5 w-3.5 flex-shrink-0 text-muted-foreground" />
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
