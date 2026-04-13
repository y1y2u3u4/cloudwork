"use client";

import { FileText, ArrowRight } from "lucide-react";

export function FileRefCard({
  name,
  filePath,
  preview,
  onClick,
}: {
  name: string;
  filePath: string;
  preview?: string;
  onClick?: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className="my-1 flex w-full max-w-xs items-start gap-2 rounded-lg border border-border bg-sidebar/50 px-3 py-2 text-left transition-colors hover:bg-sidebar-hover"
    >
      <FileText className="mt-0.5 size-4 shrink-0 text-accent" />
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-1.5">
          <span className="truncate text-xs font-medium">{name}</span>
          <ArrowRight className="size-3 shrink-0 text-muted" />
        </div>
        <p className="truncate text-xs text-muted">{filePath}</p>
        {preview && (
          <p className="mt-1 line-clamp-2 font-mono text-xs text-muted/70">
            {preview}
          </p>
        )}
      </div>
    </button>
  );
}
