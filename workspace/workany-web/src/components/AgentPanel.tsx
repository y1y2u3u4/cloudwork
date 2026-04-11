"use client";

import { useState } from "react";
import { Bot, Plus, Trash2, Edit3, Check, X, FolderOpen } from "lucide-react";
import type { Agent } from "@/lib/agents";

interface AgentPanelProps {
  agents: Agent[];
  onAgentsChange: () => void;
  workspaceDirs: string[];
}

function AgentEditor({
  agent,
  workspaceDirs,
  onSave,
  onCancel,
}: {
  agent?: Agent;
  workspaceDirs: string[];
  onSave: (data: Partial<Agent>) => void;
  onCancel: () => void;
}) {
  const [name, setName] = useState(agent?.name || "");
  const [icon, setIcon] = useState(agent?.icon || "🤖");
  const [projectPath, setProjectPath] = useState(agent?.project_path || "");
  const [model, setModel] = useState(agent?.model || "sonnet");
  const [systemPrompt, setSystemPrompt] = useState(agent?.system_prompt || "");

  return (
    <div className="space-y-3 rounded-lg border border-border bg-background p-3">
      <div className="flex gap-2">
        <input
          value={icon}
          onChange={(e) => setIcon(e.target.value)}
          className="w-10 rounded border border-border bg-sidebar px-1 py-1 text-center text-lg"
          maxLength={2}
        />
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Agent name"
          className="flex-1 rounded border border-border bg-sidebar px-2 py-1 text-sm"
          autoFocus
        />
      </div>

      <div>
        <label className="mb-1 block text-xs text-muted">Project directory</label>
        <select
          value={projectPath}
          onChange={(e) => setProjectPath(e.target.value)}
          className="w-full rounded border border-border bg-sidebar px-2 py-1.5 text-sm"
        >
          <option value="">-- Select --</option>
          {workspaceDirs.map((d) => (
            <option key={d} value={d}>{d}</option>
          ))}
        </select>
      </div>

      <div>
        <label className="mb-1 block text-xs text-muted">Model</label>
        <select
          value={model}
          onChange={(e) => setModel(e.target.value)}
          className="w-full rounded border border-border bg-sidebar px-2 py-1.5 text-sm"
        >
          <option value="sonnet">Sonnet</option>
          <option value="opus">Opus</option>
          <option value="haiku">Haiku</option>
        </select>
      </div>

      <div>
        <label className="mb-1 block text-xs text-muted">System prompt</label>
        <textarea
          value={systemPrompt}
          onChange={(e) => setSystemPrompt(e.target.value)}
          rows={3}
          placeholder="Optional system prompt..."
          className="w-full rounded border border-border bg-sidebar px-2 py-1.5 text-sm resize-none"
        />
      </div>

      <div className="flex justify-end gap-2">
        <button
          onClick={onCancel}
          className="flex items-center gap-1 rounded px-2.5 py-1 text-xs text-muted hover:bg-sidebar-hover"
        >
          <X className="size-3" /> Cancel
        </button>
        <button
          onClick={() => onSave({ name, icon, project_path: projectPath, model, system_prompt: systemPrompt })}
          disabled={!name.trim()}
          className="flex items-center gap-1 rounded bg-accent px-2.5 py-1 text-xs text-white hover:bg-accent/90 disabled:opacity-40"
        >
          <Check className="size-3" /> Save
        </button>
      </div>
    </div>
  );
}

export function AgentPanel({ agents, onAgentsChange, workspaceDirs }: AgentPanelProps) {
  const [creating, setCreating] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);

  const handleCreate = async (data: Partial<Agent>) => {
    await fetch("/api/agents", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "create", ...data }),
    });
    setCreating(false);
    onAgentsChange();
  };

  const handleUpdate = async (id: string, data: Partial<Agent>) => {
    await fetch("/api/agents", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "update", id, data }),
    });
    setEditingId(null);
    onAgentsChange();
  };

  const handleDelete = async (id: string) => {
    await fetch("/api/agents", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "delete", id }),
    });
    onAgentsChange();
  };

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between px-2">
        <span className="text-xs font-semibold tracking-wide text-muted uppercase">Agents</span>
        <button
          onClick={() => setCreating(true)}
          className="rounded p-1 text-muted hover:bg-sidebar-hover hover:text-foreground"
          title="Create agent"
        >
          <Plus className="size-3.5" />
        </button>
      </div>

      {creating && (
        <AgentEditor
          workspaceDirs={workspaceDirs}
          onSave={handleCreate}
          onCancel={() => setCreating(false)}
        />
      )}

      {agents.map((agent) =>
        editingId === agent.id ? (
          <AgentEditor
            key={agent.id}
            agent={agent}
            workspaceDirs={workspaceDirs}
            onSave={(data) => handleUpdate(agent.id, data)}
            onCancel={() => setEditingId(null)}
          />
        ) : (
          <div
            key={agent.id}
            className="group flex items-center gap-2 rounded-md px-2 py-1.5 hover:bg-sidebar-hover"
          >
            <span className="text-base">{agent.icon}</span>
            <div className="min-w-0 flex-1">
              <div className="truncate text-sm font-medium">{agent.name}</div>
              {agent.project_path && (
                <div className="flex items-center gap-1 text-xs text-muted">
                  <FolderOpen className="size-3" />
                  <span className="truncate">{agent.project_path}</span>
                </div>
              )}
            </div>
            <div className="hidden shrink-0 gap-0.5 group-hover:flex">
              <button
                onClick={() => setEditingId(agent.id)}
                className="rounded p-1 text-muted hover:text-foreground"
              >
                <Edit3 className="size-3" />
              </button>
              <button
                onClick={() => handleDelete(agent.id)}
                className="rounded p-1 text-muted hover:text-red-500"
              >
                <Trash2 className="size-3" />
              </button>
            </div>
          </div>
        )
      )}

      {agents.length === 0 && !creating && (
        <div className="px-2 py-4 text-center text-xs text-muted">
          <Bot className="mx-auto mb-1 size-5" />
          No agents yet
        </div>
      )}
    </div>
  );
}
