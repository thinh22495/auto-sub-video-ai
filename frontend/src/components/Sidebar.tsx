"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  Home,
  PlusCircle,
  Layers,
  Settings,
  Cpu,
  Palette,
  FolderOpen,
} from "lucide-react";

const navigation = [
  { name: "Dashboard", href: "/", icon: Home },
  { name: "New Job", href: "/jobs/new/", icon: PlusCircle },
  { name: "Batch", href: "/batch/", icon: Layers },
  { name: "Presets", href: "/presets/", icon: Palette },
  { name: "Models", href: "/models/", icon: Cpu },
  { name: "Settings", href: "/settings/", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="flex w-64 flex-col border-r border-border bg-card">
      {/* Logo */}
      <div className="flex h-16 items-center gap-3 border-b border-border px-6">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary">
          <FolderOpen className="h-4 w-4 text-primary-foreground" />
        </div>
        <div>
          <h1 className="text-lg font-bold text-foreground">AutoSubAI</h1>
          <p className="text-xs text-muted-foreground">v0.1.0</p>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-1 p-3">
        {navigation.map((item) => {
          const isActive =
            item.href === "/"
              ? pathname === "/" || pathname === ""
              : pathname.startsWith(item.href.replace(/\/$/, ""));

          return (
            <Link
              key={item.name}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                isActive
                  ? "bg-primary/10 text-primary"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground"
              )}
            >
              <item.icon className="h-4 w-4" />
              {item.name}
            </Link>
          );
        })}
      </nav>

      {/* Status Footer */}
      <div className="border-t border-border p-4">
        <StatusIndicator />
      </div>
    </aside>
  );
}

function StatusIndicator() {
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-xs">
        <span className="text-muted-foreground">API</span>
        <span className="flex items-center gap-1.5">
          <span className="h-2 w-2 rounded-full bg-success" />
          <span className="text-success">Online</span>
        </span>
      </div>
      <div className="flex items-center justify-between text-xs">
        <span className="text-muted-foreground">GPU</span>
        <span className="flex items-center gap-1.5">
          <span className="h-2 w-2 rounded-full bg-muted-foreground" />
          <span className="text-muted-foreground">Checking...</span>
        </span>
      </div>
    </div>
  );
}
