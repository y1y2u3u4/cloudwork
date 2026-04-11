"use client";

import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import { Pencil, Eye, Save, X } from "lucide-react";

export function MarkdownViewer({
  content,
  filePath,
  onSave,
}: {
  content: string;
  filePath: string;
  onSave?: (content: string) => void;
}) {
  const fileName = filePath.split("/").pop() || filePath;
  const [editing, setEditing] = useState(false);
  const [editContent, setEditContent] = useState(content);
  const [saving, setSaving] = useState(false);

  const handleStartEdit = () => {
    setEditContent(content);
    setEditing(true);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const res = await fetch("/api/workspace", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "write", path: filePath, content: editContent }),
      });
      if (res.ok) {
        onSave?.(editContent);
        setEditing(false);
      }
    } catch (err) {
      console.error("Save failed:", err);
    }
    setSaving(false);
  };

  const handleCancel = () => {
    setEditing(false);
    setEditContent(content);
  };

  return (
    <div className="flex h-full flex-col">
      {/* Header bar */}
      <div className="flex shrink-0 items-center gap-2 border-b border-border px-4 py-2.5">
        <span className="text-sm font-medium text-foreground">{fileName}</span>
        <span className="text-xs text-muted">{filePath}</span>
        <div className="ml-auto flex items-center gap-1">
          {editing ? (
            <>
              <button
                onClick={handleCancel}
                className="flex items-center gap-1 rounded-md px-2 py-1 text-xs text-muted hover:bg-sidebar-hover"
              >
                <X className="size-3" />
                Cancel
              </button>
              <button
                onClick={handleSave}
                disabled={saving}
                className="flex items-center gap-1 rounded-md bg-accent px-2.5 py-1 text-xs text-white hover:bg-accent/90 disabled:opacity-50"
              >
                <Save className="size-3" />
                {saving ? "Saving..." : "Save"}
              </button>
            </>
          ) : (
            <button
              onClick={handleStartEdit}
              className="flex items-center gap-1 rounded-md px-2 py-1 text-xs text-muted hover:bg-sidebar-hover hover:text-foreground"
            >
              <Pencil className="size-3" />
              Edit
            </button>
          )}
        </div>
      </div>

      {/* Content */}
      {editing ? (
        <textarea
          value={editContent}
          onChange={(e) => setEditContent(e.target.value)}
          className="flex-1 resize-none bg-background px-8 py-6 font-mono text-sm leading-relaxed outline-none"
          autoFocus
        />
      ) : (
        <div className="flex-1 overflow-auto px-8 py-6">
          <div className="mx-auto max-w-3xl">
            <div className="markdown-body">
              <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeHighlight]}>
                {content}
              </ReactMarkdown>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
