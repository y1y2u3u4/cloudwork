"use client";

import { useState, useRef, useEffect } from "react";
import { Send, X, Minimize2, Loader2, Bot } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Task, CreateTaskParams } from "@/lib/taskTypes";

interface Agent {
  id: string;
  name: string;
  icon: string;
}

interface InlineChatProps {
  selectedText: string;
  filePath: string;
  agents: Agent[];
  position: { top: number; left: number };
  onClose: () => void;
  onMinimize: (taskId: string) => void;
  createTask: (params: CreateTaskParams) => Task;
  // For viewing a completed task result
  viewingTask?: Task | null;
}

export function InlineChat({
  selectedText,
  filePath,
  agents,
  position,
  onClose,
  onMinimize,
  createTask,
  viewingTask,
}: InlineChatProps) {
  const [input, setInput] = useState("");
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null);
  const [showAgentPicker, setShowAgentPicker] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!viewingTask) inputRef.current?.focus();
  }, [viewingTask]);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [onClose]);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        onClose();
      }
    };
    const timer = setTimeout(() => document.addEventListener("mousedown", handler), 100);
    return () => { clearTimeout(timer); document.removeEventListener("mousedown", handler); };
  }, [onClose]);

  const handleInputChange = (value: string) => {
    setInput(value);
    setShowAgentPicker(value.endsWith("@") || (value.includes("@") && !value.includes(" ")));
  };

  const pickAgent = (agent: Agent) => {
    const before = input.lastIndexOf("@");
    const prefix = before >= 0 ? input.slice(0, before) : input;
    setInput(`${prefix}@${agent.name} `);
    setSelectedAgent(agent);
    setShowAgentPicker(false);
    inputRef.current?.focus();
  };

  const clearAgent = () => {
    setSelectedAgent(null);
    setInput((prev) => prev.replace(/@\S+\s*/, ""));
  };

  const handleSubmit = () => {
    const text = input.trim();
    if (!text || submitted) return;

    let agentId = selectedAgent?.id || "";
    let agentName = selectedAgent?.name || "";
    let prompt = text;

    const mentionMatch = text.match(/^@(\S+)\s+([\s\S]+)/);
    if (mentionMatch) {
      const agent = agents.find((a) => a.name.toLowerCase() === mentionMatch[1].toLowerCase());
      if (agent) {
        agentId = agent.id;
        agentName = agent.name;
        prompt = mentionMatch[2];
      }
    }

    const contextPrompt = `[Context from ${filePath}]\n${selectedText}\n\n${prompt}`;

    const task = createTask({
      type: "inline",
      title: prompt.slice(0, 60),
      prompt: contextPrompt,
      agentId,
      agentName,
      source: { kind: "inline", filePath, selectedText },
    });

    setSubmitted(true);

    // Auto-minimize after a short delay so user sees confirmation
    setTimeout(() => onMinimize(task.id), 800);
  };

  // Viewing a completed task result
  if (viewingTask) {
    return (
      <div
        ref={panelRef}
        className="fixed z-50 w-[480px] max-h-[420px] flex flex-col rounded-xl border border-border bg-background shadow-2xl"
        style={{
          top: `${Math.min(position.top, window.innerHeight - 440)}px`,
          left: `${Math.min(Math.max(position.left - 240, 10), window.innerWidth - 500)}px`,
        }}
      >
        <div className="flex items-center justify-between border-b border-border px-3 py-2">
          <div className="flex items-center gap-1.5 text-xs font-medium">
            <span>💬</span>
            {viewingTask.agentName && <span className="text-accent">{viewingTask.agentName}</span>}
            <span className="text-muted">·</span>
            <span className="max-w-[240px] truncate text-muted">{filePath}</span>
          </div>
          <button onClick={onClose} className="rounded p-0.5 text-muted hover:text-foreground">
            <X className="size-3.5" />
          </button>
        </div>
        <div className="border-b border-border bg-sidebar/50 px-3 py-2">
          <p className="line-clamp-2 font-mono text-xs text-muted">{viewingTask.source.kind === "inline" ? viewingTask.source.selectedText : ""}</p>
        </div>
        <div className="flex-1 overflow-auto px-3 py-3 max-h-[300px]">
          <div className="markdown-body text-xs">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{viewingTask.result || "No result"}</ReactMarkdown>
          </div>
        </div>
      </div>
    );
  }

  // Task submitted, waiting for minimize
  if (submitted) {
    return (
      <div
        ref={panelRef}
        className="fixed z-50 w-[480px] flex flex-col rounded-xl border border-border bg-background shadow-2xl"
        style={{
          top: `${Math.min(position.top, window.innerHeight - 200)}px`,
          left: `${Math.min(Math.max(position.left - 240, 10), window.innerWidth - 500)}px`,
        }}
      >
        <div className="flex items-center justify-between border-b border-border px-3 py-2">
          <div className="flex items-center gap-1.5 text-xs font-medium text-accent">
            <Loader2 className="size-3.5 animate-spin" />
            Task submitted — running in background
          </div>
          <button onClick={onClose} className="rounded p-0.5 text-muted hover:text-foreground">
            <X className="size-3.5" />
          </button>
        </div>
        <div className="px-3 py-2 text-xs text-muted">
          You can close this and continue working. You&apos;ll be notified when done.
        </div>
      </div>
    );
  }

  // Normal input mode
  return (
    <div
      ref={panelRef}
      className="fixed z-50 w-[480px] max-h-[420px] flex flex-col rounded-xl border border-border bg-background shadow-2xl"
      style={{
        top: `${Math.min(position.top, window.innerHeight - 440)}px`,
        left: `${Math.min(Math.max(position.left - 240, 10), window.innerWidth - 500)}px`,
      }}
    >
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border px-3 py-2">
        <div className="flex items-center gap-1.5 text-xs font-medium">
          <span>💬</span>
          {selectedAgent && (
            <>
              <span className="text-accent">{selectedAgent.icon} {selectedAgent.name}</span>
              <span className="text-muted">·</span>
            </>
          )}
          <span className="max-w-[240px] truncate text-muted">{filePath}</span>
        </div>
        <div className="flex gap-0.5">
          <button onClick={onClose} className="rounded p-0.5 text-muted hover:text-foreground">
            <X className="size-3.5" />
          </button>
        </div>
      </div>

      {/* Quote */}
      <div className="border-b border-border bg-sidebar/50 px-3 py-2">
        <p className="line-clamp-2 font-mono text-xs text-muted">{selectedText}</p>
      </div>

      {/* Input */}
      <div className="relative border-t border-border px-3 py-2">
        {showAgentPicker && agents.length > 0 && inputRef.current && (() => {
          const rect = inputRef.current.getBoundingClientRect();
          return (
            <div
              className="fixed z-[60] rounded-lg border border-border bg-background p-1 shadow-lg"
              style={{ bottom: `${window.innerHeight - rect.top + 4}px`, left: `${rect.left}px` }}
            >
              {agents.map((a) => (
                <button
                  key={a.id}
                  onClick={() => pickAgent(a)}
                  className="flex w-full items-center gap-2 rounded-md px-3 py-1.5 text-xs transition-colors hover:bg-sidebar-hover"
                >
                  <span>{a.icon}</span>
                  <span className="font-medium">{a.name}</span>
                </button>
              ))}
            </div>
          );
        })()}

        {selectedAgent && (
          <div className="mb-1.5 flex items-center">
            <span className="flex items-center gap-1 rounded-full bg-accent-light px-2 py-0.5 text-xs text-accent">
              {selectedAgent.icon} {selectedAgent.name}
              <button onClick={clearAgent} className="ml-0.5 text-accent/50 hover:text-accent">×</button>
            </span>
          </div>
        )}

        <div className="flex items-end gap-2 rounded-lg border border-border bg-background px-2.5 py-1.5 focus-within:border-accent/50">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => handleInputChange(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSubmit(); } }}
            placeholder="Ask about this... (use @ to pick agent)"
            rows={1}
            className="max-h-16 min-h-[20px] flex-1 resize-none bg-transparent text-xs outline-none"
          />
          <button
            onClick={handleSubmit}
            disabled={!input.trim()}
            className="flex size-6 shrink-0 items-center justify-center rounded-md bg-accent text-white disabled:opacity-30"
          >
            <Send className="size-3" />
          </button>
        </div>
      </div>
    </div>
  );
}
