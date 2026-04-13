"use client";

import { useState } from "react";
import {
  ChevronRight,
  ChevronDown,
  Folder,
  FileText,
  File,
  FolderOpen,
} from "lucide-react";

interface FileEntry {
  name: string;
  path: string;
  isDirectory: boolean;
  extension?: string;
  children?: FileEntry[];
}

function getFileIcon(ext?: string) {
  if (!ext) return File;
  const mdExts = ["md", "mdx", "txt"];
  if (mdExts.includes(ext)) return FileText;
  return File;
}

function TreeNode({
  entry,
  depth,
  selectedPath,
  onSelect,
}: {
  entry: FileEntry;
  depth: number;
  selectedPath: string;
  onSelect: (path: string, isDir: boolean) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const [children, setChildren] = useState<FileEntry[] | null>(
    entry.children || null
  );
  const [loading, setLoading] = useState(false);
  const isSelected = selectedPath === entry.path;

  const handleClick = async () => {
    if (entry.isDirectory) {
      if (!expanded && !children) {
        setLoading(true);
        try {
          const res = await fetch(
            `/api/workspace?action=tree&path=${encodeURIComponent(entry.path)}&depth=1`
          );
          const data = await res.json();
          setChildren(data.entries || []);
        } catch {
          setChildren([]);
        }
        setLoading(false);
      }
      setExpanded(!expanded);
      onSelect(entry.path, true);
    } else {
      onSelect(entry.path, false);
    }
  };

  const Icon = entry.isDirectory
    ? expanded
      ? FolderOpen
      : Folder
    : getFileIcon(entry.extension);

  const handleDragStart = (e: React.DragEvent) => {
    if (entry.isDirectory) return;
    e.dataTransfer.setData(
      "application/workspace-file",
      JSON.stringify({ path: entry.path, name: entry.name })
    );
    e.dataTransfer.effectAllowed = "copy";
    (e.target as HTMLElement).style.opacity = "0.5";
  };

  const handleDragEnd = (e: React.DragEvent) => {
    (e.target as HTMLElement).style.opacity = "1";
  };

  return (
    <div>
      <button
        onClick={handleClick}
        draggable={!entry.isDirectory}
        onDragStart={handleDragStart}
        onDragEnd={handleDragEnd}
        className={`flex w-full items-center gap-1.5 rounded-md px-2 py-1 text-left text-sm transition-colors hover:bg-sidebar-hover ${
          isSelected ? "bg-accent-light text-accent font-medium" : "text-foreground/80"
        } ${!entry.isDirectory ? "cursor-grab active:cursor-grabbing" : ""}`}
        style={{ paddingLeft: `${depth * 16 + 8}px` }}
      >
        {entry.isDirectory ? (
          expanded ? (
            <ChevronDown className="size-3.5 shrink-0 text-muted" />
          ) : (
            <ChevronRight className="size-3.5 shrink-0 text-muted" />
          )
        ) : (
          <span className="size-3.5 shrink-0" />
        )}
        <Icon
          className={`size-4 shrink-0 ${
            entry.isDirectory ? "text-accent" : "text-muted"
          }`}
        />
        <span className="truncate">{entry.name}</span>
        {loading && (
          <span className="ml-auto text-xs text-muted">...</span>
        )}
      </button>
      {expanded && children && (
        <div>
          {children.map((child) => (
            <TreeNode
              key={child.path}
              entry={child}
              depth={depth + 1}
              selectedPath={selectedPath}
              onSelect={onSelect}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export function FileTree({
  entries,
  selectedPath,
  onSelect,
}: {
  entries: FileEntry[];
  selectedPath: string;
  onSelect: (path: string, isDir: boolean) => void;
}) {
  return (
    <div className="space-y-0.5 py-1">
      {entries.map((entry) => (
        <TreeNode
          key={entry.path}
          entry={entry}
          depth={0}
          selectedPath={selectedPath}
          onSelect={onSelect}
        />
      ))}
    </div>
  );
}
