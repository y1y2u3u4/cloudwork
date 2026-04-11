"use client";

import { useState } from "react";
import { Plus, Trash2, X, Save } from "lucide-react";

interface Agent {
  id: string;
  name: string;
  icon: string;
  project_path: string;
  model: string;
  system_prompt: string;
  claude_md: string;
  created_at: string;
}

export function AgentManager({
  agents,
  onRefresh,
  open,
  onClose,
}: {
  agents: Agent[];
  onRefresh: () => void;
  open: boolean;
  onClose: () => void;
}) {
  const [editing, setEditing] = useState<Agent | null>(null);
  const [form, setForm] = useState({
    name: "",
    icon: "🤖",
    project_path: "",
    model: "sonnet",
    system_prompt: "",
    claude_md: "",
  });

  if (!open) return null;

  const startCreate = () => {
    setEditing(null);
    setForm({
      name: "",
      icon: "🤖",
      project_path: "",
      model: "sonnet",
      system_prompt: "",
      claude_md: "",
    });
  };

  const startEdit = (agent: Agent) => {
    setEditing(agent);
    setForm({
      name: agent.name,
      icon: agent.icon,
      project_path: agent.project_path,
      model: agent.model,
      system_prompt: agent.system_prompt,
      claude_md: agent.claude_md,
    });
  };

  const handleSave = async () => {
    if (!form.name.trim()) return;

    if (editing) {
      await fetch("/api/agents", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "update", id: editing.id, data: form }),
      });
    } else {
      await fetch("/api/agents", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "create", ...form }),
      });
    }
    setEditing(null);
    onRefresh();
  };

  const handleDelete = async (id: string) => {
    await fetch("/api/agents", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "delete", id }),
    });
    onRefresh();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
      <div className="mx-4 flex max-h-[85vh] w-full max-w-2xl flex-col rounded-xl bg-background shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-border px-5 py-3.5">
          <h2 className="text-base font-semibold">Agents</h2>
          <div className="flex items-center gap-2">
            <button
              onClick={startCreate}
              className="flex items-center gap-1.5 rounded-lg bg-accent px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-accent/90"
            >
              <Plus className="size-3.5" />
              New
            </button>
            <button
              onClick={onClose}
              className="rounded-lg p-1.5 text-muted transition-colors hover:bg-sidebar-hover"
            >
              <X className="size-4" />
            </button>
          </div>
        </div>

        <div className="flex min-h-0 flex-1">
          {/* Agent list */}
          <div className="w-48 shrink-0 overflow-auto border-r border-border p-2">
            {agents.map((agent) => (
              <button
                key={agent.id}
                onClick={() => startEdit(agent)}
                className={`flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm transition-colors hover:bg-sidebar-hover ${
                  editing?.id === agent.id ? "bg-accent-light text-accent" : ""
                }`}
              >
                <span>{agent.icon}</span>
                <span className="truncate">{agent.name}</span>
              </button>
            ))}
            {agents.length === 0 && (
              <p className="px-3 py-4 text-center text-xs text-muted">
                No agents yet
              </p>
            )}
          </div>

          {/* Edit form */}
          <div className="flex-1 overflow-auto p-4">
            <div className="space-y-3">
              <div className="flex gap-3">
                <div className="w-16">
                  <label className="mb-1 block text-xs text-muted">Icon</label>
                  <input
                    value={form.icon}
                    onChange={(e) =>
                      setForm({ ...form, icon: e.target.value })
                    }
                    className="w-full rounded-lg border border-border bg-background px-2.5 py-1.5 text-center text-lg"
                  />
                </div>
                <div className="flex-1">
                  <label className="mb-1 block text-xs text-muted">Name</label>
                  <input
                    value={form.name}
                    onChange={(e) =>
                      setForm({ ...form, name: e.target.value })
                    }
                    placeholder="Agent name"
                    className="w-full rounded-lg border border-border bg-background px-3 py-1.5 text-sm"
                  />
                </div>
              </div>

              <div className="flex gap-3">
                <div className="flex-1">
                  <label className="mb-1 block text-xs text-muted">
                    Project Path
                  </label>
                  <input
                    value={form.project_path}
                    onChange={(e) =>
                      setForm({ ...form, project_path: e.target.value })
                    }
                    placeholder="e.g. autoresearch"
                    className="w-full rounded-lg border border-border bg-background px-3 py-1.5 text-sm font-mono"
                  />
                </div>
                <div className="w-32">
                  <label className="mb-1 block text-xs text-muted">Model</label>
                  <select
                    value={form.model}
                    onChange={(e) =>
                      setForm({ ...form, model: e.target.value })
                    }
                    className="w-full rounded-lg border border-border bg-background px-3 py-1.5 text-sm"
                  >
                    <option value="sonnet">Sonnet</option>
                    <option value="opus">Opus</option>
                    <option value="haiku">Haiku</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="mb-1 block text-xs text-muted">
                  System Prompt
                </label>
                <textarea
                  value={form.system_prompt}
                  onChange={(e) =>
                    setForm({ ...form, system_prompt: e.target.value })
                  }
                  placeholder="Custom persona or instructions..."
                  rows={3}
                  className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                />
              </div>

              <div>
                <label className="mb-1 block text-xs text-muted">
                  CLAUDE.md
                </label>
                <textarea
                  value={form.claude_md}
                  onChange={(e) =>
                    setForm({ ...form, claude_md: e.target.value })
                  }
                  placeholder="Project instructions for Claude..."
                  rows={4}
                  className="w-full rounded-lg border border-border bg-background px-3 py-2 font-mono text-xs"
                />
              </div>

              <div className="flex items-center justify-between pt-1">
                {editing && (
                  <button
                    onClick={() => handleDelete(editing.id)}
                    className="flex items-center gap-1 rounded-lg px-3 py-1.5 text-xs text-red-500 transition-colors hover:bg-red-50"
                  >
                    <Trash2 className="size-3.5" />
                    Delete
                  </button>
                )}
                <div className="ml-auto">
                  <button
                    onClick={handleSave}
                    disabled={!form.name.trim()}
                    className="flex items-center gap-1.5 rounded-lg bg-accent px-4 py-1.5 text-xs font-medium text-white transition-colors hover:bg-accent/90 disabled:opacity-40"
                  >
                    <Save className="size-3.5" />
                    {editing ? "Update" : "Create"}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
