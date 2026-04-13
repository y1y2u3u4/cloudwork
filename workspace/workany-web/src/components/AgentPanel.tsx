"use client";

import { useState, useEffect, useCallback } from "react";
import { Bot, Plus, Trash2, Edit3, Check, X, Sparkles, Zap, Loader2 } from "lucide-react";
import type { Agent } from "@/lib/agents";

interface Skill {
  id: string;
  name: string;
  description: string;
  source: string;
}

interface AgentPanelProps {
  agents: Agent[];
  onAgentsChange: () => void;
  workspaceDirs: string[];
}

// Shared AI Creator component for both Agent and Skill
function AICreator({
  type,
  onDone,
  onCancel,
}: {
  type: "agent" | "skill";
  onDone: () => void;
  onCancel: () => void;
}) {
  const [description, setDescription] = useState("");
  const [generating, setGenerating] = useState(false);
  const [preview, setPreview] = useState("");
  const [resultName, setResultName] = useState<string | null>(null);

  const handleGenerate = async () => {
    if (!description.trim() || generating) return;
    setGenerating(true);
    setPreview("");
    setResultName(null);

    const endpoint = type === "agent" ? "/api/agents/create-with-ai" : "/api/skills/create-with-ai";

    try {
      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ description }),
      });

      const reader = res.body?.getReader();
      const decoder = new TextDecoder();
      if (reader) {
        let buffer = "";
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";
          for (const line of lines) {
            if (!line.startsWith("data: ")) continue;
            try {
              const event = JSON.parse(line.slice(6));
              if (event.type === "text") setPreview(prev => prev + event.content);
              if (event.type === "done") setResultName(event.agentName || event.skillName || "created");
            } catch { /* skip */ }
          }
        }
      }
    } catch (e: unknown) {
      setPreview(prev => prev + `\nError: ${e instanceof Error ? e.message : "Unknown"}`);
    }

    setGenerating(false);
  };

  if (resultName) {
    return (
      <div className="space-y-2 rounded-lg border border-green-200 bg-green-50 p-3">
        <p className="text-xs font-medium text-green-700">
          {type === "agent" ? "Agent" : "Skill"} &quot;{resultName}&quot; created!
        </p>
        <button onClick={onDone} className="rounded bg-accent px-2.5 py-1 text-xs text-white hover:bg-accent/90">
          Done
        </button>
      </div>
    );
  }

  const placeholder = type === "agent"
    ? "Describe the agent... e.g. 'A SaaS pricing expert that analyzes competitor pricing'"
    : "Describe the skill... e.g. 'A 12-dimension teardown framework for analyzing AI SaaS products'";

  return (
    <div className="space-y-2 rounded-lg border border-border bg-background p-3">
      <div className="flex items-center gap-1.5 text-xs font-medium text-accent">
        <Sparkles className="size-3.5" />
        AI {type === "agent" ? "Agent" : "Skill"} Creator
      </div>
      <textarea
        value={description}
        onChange={e => setDescription(e.target.value)}
        placeholder={placeholder}
        rows={3}
        className="w-full rounded border border-border bg-sidebar px-2 py-1.5 text-xs resize-none"
        autoFocus
      />
      {preview && (
        <div className="max-h-32 overflow-auto rounded border border-border bg-sidebar p-2">
          <pre className="whitespace-pre-wrap text-xs text-muted">{preview.slice(0, 500)}{preview.length > 500 ? "..." : ""}</pre>
        </div>
      )}
      <div className="flex justify-end gap-2">
        <button onClick={onCancel} className="flex items-center gap-1 rounded px-2.5 py-1 text-xs text-muted hover:bg-sidebar-hover">
          <X className="size-3" /> Cancel
        </button>
        <button
          onClick={handleGenerate}
          disabled={!description.trim() || generating}
          className="flex items-center gap-1 rounded bg-accent px-2.5 py-1 text-xs text-white hover:bg-accent/90 disabled:opacity-40"
        >
          {generating ? <Loader2 className="size-3 animate-spin" /> : <Sparkles className="size-3" />}
          {generating ? "Creating..." : "Create"}
        </button>
      </div>
    </div>
  );
}

// Manual Skill Editor
function ManualSkillEditor({
  onSave,
  onCancel,
}: {
  onSave: (data: { name: string; description: string; content: string }) => void;
  onCancel: () => void;
}) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [content, setContent] = useState("");

  return (
    <div className="space-y-3 rounded-lg border border-border bg-background p-3">
      <input
        value={name}
        onChange={e => setName(e.target.value.toLowerCase().replace(/\s+/g, "-").replace(/[^a-z0-9-]/g, ""))}
        placeholder="skill-name (lowercase, hyphens)"
        className="w-full rounded border border-border bg-sidebar px-2 py-1 text-sm"
        autoFocus
      />
      <input
        value={description}
        onChange={e => setDescription(e.target.value)}
        placeholder="One-line description..."
        className="w-full rounded border border-border bg-sidebar px-2 py-1 text-xs"
      />
      <textarea
        value={content}
        onChange={e => setContent(e.target.value)}
        rows={4}
        placeholder="Skill instructions (what should Claude do when this command is invoked)..."
        className="w-full rounded border border-border bg-sidebar px-2 py-1.5 text-sm resize-none"
      />
      <div className="flex justify-end gap-2">
        <button onClick={onCancel} className="flex items-center gap-1 rounded px-2.5 py-1 text-xs text-muted hover:bg-sidebar-hover"><X className="size-3" /> Cancel</button>
        <button onClick={() => onSave({ name, description, content })} disabled={!name.trim()} className="flex items-center gap-1 rounded bg-accent px-2.5 py-1 text-xs text-white hover:bg-accent/90 disabled:opacity-40"><Check className="size-3" /> Save</button>
      </div>
    </div>
  );
}

// Manual Agent Editor
function ManualAgentEditor({
  agent,
  onSave,
  onCancel,
}: {
  agent?: Agent;
  onSave: (data: Partial<Agent>) => void;
  onCancel: () => void;
}) {
  const [name, setName] = useState(agent?.name || "");
  const [icon, setIcon] = useState(agent?.icon || "🤖");
  const [model, setModel] = useState(agent?.model || "sonnet");
  const [description, setDescription] = useState(agent?.description || "");
  const [systemPrompt, setSystemPrompt] = useState(agent?.system_prompt || "");

  return (
    <div className="space-y-3 rounded-lg border border-border bg-background p-3">
      <div className="flex gap-2">
        <input value={icon} onChange={e => setIcon(e.target.value)} className="w-10 rounded border border-border bg-sidebar px-1 py-1 text-center text-lg" maxLength={2} />
        <input value={name} onChange={e => setName(e.target.value)} placeholder="agent-name" className="flex-1 rounded border border-border bg-sidebar px-2 py-1 text-sm" autoFocus />
      </div>
      <input value={description} onChange={e => setDescription(e.target.value)} placeholder="One-line description..." className="w-full rounded border border-border bg-sidebar px-2 py-1 text-xs" />
      <select value={model} onChange={e => setModel(e.target.value)} className="w-full rounded border border-border bg-sidebar px-2 py-1.5 text-sm">
        <option value="sonnet">Sonnet</option>
        <option value="opus">Opus</option>
        <option value="haiku">Haiku</option>
      </select>
      <textarea value={systemPrompt} onChange={e => setSystemPrompt(e.target.value)} rows={3} placeholder="System prompt..." className="w-full rounded border border-border bg-sidebar px-2 py-1.5 text-sm resize-none" />
      <div className="flex justify-end gap-2">
        <button onClick={onCancel} className="flex items-center gap-1 rounded px-2.5 py-1 text-xs text-muted hover:bg-sidebar-hover"><X className="size-3" /> Cancel</button>
        <button onClick={() => onSave({ name, icon, description, model, system_prompt: systemPrompt })} disabled={!name.trim()} className="flex items-center gap-1 rounded bg-accent px-2.5 py-1 text-xs text-white hover:bg-accent/90 disabled:opacity-40"><Check className="size-3" /> Save</button>
      </div>
    </div>
  );
}

type CreateMode = "agent-ai" | "agent-manual" | "skill-ai" | "skill-manual" | null;

export function AgentPanel({ agents, onAgentsChange, workspaceDirs }: AgentPanelProps) {
  const [createMode, setCreateMode] = useState<CreateMode>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [skills, setSkills] = useState<Skill[]>([]);
  const [showSkills, setShowSkills] = useState(false);

  const loadSkills = useCallback(() => {
    fetch("/api/skills").then(r => r.json()).then(d => setSkills(d.skills || [])).catch(() => {});
  }, []);

  useEffect(() => { loadSkills(); }, [loadSkills]);

  const handleCreateAgent = async (data: Partial<Agent>) => {
    await fetch("/api/agents", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "create", ...data }),
    });
    setCreateMode(null);
    onAgentsChange();
  };

  const handleUpdateAgent = async (id: string, data: Partial<Agent>) => {
    await fetch("/api/agents", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "update", id, data }),
    });
    setEditingId(null);
    onAgentsChange();
  };

  const handleDeleteAgent = async (id: string) => {
    await fetch("/api/agents", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "delete", id }),
    });
    onAgentsChange();
  };

  const handleCreateSkill = async (data: { name: string; description: string; content: string }) => {
    await fetch("/api/skills", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "create", ...data }),
    });
    setCreateMode(null);
    loadSkills();
  };

  const handleDeleteSkill = async (name: string) => {
    await fetch("/api/skills", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "delete", name }),
    });
    loadSkills();
  };

  // Suppress unused var warning
  void workspaceDirs;

  return (
    <div className="space-y-2">
      {/* Agents section */}
      <div className="flex items-center justify-between px-2">
        <span className="text-xs font-semibold tracking-wide text-muted uppercase">Agents</span>
        <div className="flex gap-0.5">
          <button onClick={() => setCreateMode("agent-ai")} className="rounded p-1 text-muted hover:bg-sidebar-hover hover:text-accent" title="Create agent with AI">
            <Sparkles className="size-3.5" />
          </button>
          <button onClick={() => setCreateMode("agent-manual")} className="rounded p-1 text-muted hover:bg-sidebar-hover hover:text-foreground" title="Create agent manually">
            <Plus className="size-3.5" />
          </button>
        </div>
      </div>

      {createMode === "agent-ai" && (
        <AICreator type="agent" onDone={() => { setCreateMode(null); onAgentsChange(); }} onCancel={() => setCreateMode(null)} />
      )}
      {createMode === "agent-manual" && (
        <ManualAgentEditor onSave={handleCreateAgent} onCancel={() => setCreateMode(null)} />
      )}

      {agents.map(agent =>
        editingId === agent.id ? (
          <ManualAgentEditor key={agent.id} agent={agent} onSave={data => handleUpdateAgent(agent.id, data)} onCancel={() => setEditingId(null)} />
        ) : (
          <div key={agent.id} className="group flex items-center gap-2 rounded-md px-2 py-1.5 hover:bg-sidebar-hover">
            <span className="text-base">{agent.icon}</span>
            <div className="min-w-0 flex-1">
              <div className="truncate text-sm font-medium">{agent.name}</div>
              {agent.description && <div className="truncate text-xs text-muted">{agent.description.slice(0, 40)}</div>}
            </div>
            <div className="hidden shrink-0 gap-0.5 group-hover:flex">
              <button onClick={() => setEditingId(agent.id)} className="rounded p-1 text-muted hover:text-foreground"><Edit3 className="size-3" /></button>
              <button onClick={() => handleDeleteAgent(agent.id)} className="rounded p-1 text-muted hover:text-red-500"><Trash2 className="size-3" /></button>
            </div>
          </div>
        )
      )}

      {agents.length === 0 && !createMode?.startsWith("agent") && (
        <div className="px-2 py-3 text-center text-xs text-muted">
          <Bot className="mx-auto mb-1 size-5" />
          No agents yet
        </div>
      )}

      {/* Skills section */}
      <div className="flex items-center justify-between px-2 pt-1">
        <button
          onClick={() => setShowSkills(!showSkills)}
          className="flex items-center gap-1 text-xs font-semibold tracking-wide text-muted uppercase hover:text-foreground"
        >
          <Zap className="size-3" />
          Skills ({skills.length})
        </button>
        <div className="flex gap-0.5">
          <button onClick={() => { setShowSkills(true); setCreateMode("skill-ai"); }} className="rounded p-1 text-muted hover:bg-sidebar-hover hover:text-amber-500" title="Create skill with AI">
            <Sparkles className="size-3.5" />
          </button>
          <button onClick={() => { setShowSkills(true); setCreateMode("skill-manual"); }} className="rounded p-1 text-muted hover:bg-sidebar-hover hover:text-foreground" title="Create skill manually">
            <Plus className="size-3.5" />
          </button>
        </div>
      </div>

      {createMode === "skill-ai" && (
        <AICreator type="skill" onDone={() => { setCreateMode(null); loadSkills(); }} onCancel={() => setCreateMode(null)} />
      )}
      {createMode === "skill-manual" && (
        <ManualSkillEditor onSave={handleCreateSkill} onCancel={() => setCreateMode(null)} />
      )}

      {showSkills && (
        <div className="space-y-0.5">
          {skills.map(skill => (
            <div key={skill.id} className="group flex items-center gap-2 rounded-md px-2 py-1 hover:bg-sidebar-hover">
              <Zap className="size-3 shrink-0 text-amber-500" />
              <div className="min-w-0 flex-1">
                <div className="truncate text-xs font-medium">/{skill.name}</div>
                <div className="truncate text-xs text-muted">{skill.description.slice(0, 50)}</div>
              </div>
              <span className="shrink-0 rounded bg-sidebar px-1.5 py-0.5 text-[10px] text-muted">{skill.source}</span>
              <button
                onClick={() => handleDeleteSkill(skill.name)}
                className="hidden shrink-0 rounded p-0.5 text-muted hover:text-red-500 group-hover:block"
              >
                <Trash2 className="size-3" />
              </button>
            </div>
          ))}
          {skills.length === 0 && !createMode?.startsWith("skill") && (
            <p className="px-2 py-2 text-center text-xs text-muted">No skills</p>
          )}
        </div>
      )}
    </div>
  );
}
