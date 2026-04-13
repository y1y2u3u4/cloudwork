"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { Loader2, Bot, Square, X, MessageSquare } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import type { CreateTaskParams, Task } from "@/lib/taskTypes";

interface Agent {
  id: string;
  name: string;
  icon: string;
}

interface CommentMessage {
  role: "user" | "assistant";
  content: string;
}

export interface CommentThread {
  id: string;
  selectedText: string;
  filePath: string;
  messages: CommentMessage[];
  sessionId: string;
  agentId?: string;
  agentName?: string;
  taskId?: string;
  status: "draft" | "loading" | "done" | "error";
  createdAt: number;
}

interface CommentSidebarProps {
  threads: CommentThread[];
  fileContent: string;
  agents: Agent[];
  onUpdateThread: (id: string, patch: Partial<CommentThread>) => void;
  onRemoveThread: (id: string) => void;
  createTask?: (params: CreateTaskParams) => Task;
  updateTask?: (id: string, patch: Partial<Task>) => void;
  onFileChanged?: (path: string) => void;
}

function CommentCard({
  thread,
  fileContent,
  agents,
  onUpdate,
  onRemove,
  createTask,
  updateTask,
  onFileChanged,
}: {
  thread: CommentThread;
  fileContent: string;
  agents: Agent[];
  onUpdate: (patch: Partial<CommentThread>) => void;
  onRemove: () => void;
  createTask?: (params: CreateTaskParams) => Task;
  updateTask?: (id: string, patch: Partial<Task>) => void;
  onFileChanged?: (path: string) => void;
}) {
  const [input, setInput] = useState("");
  const [showAgentPicker, setShowAgentPicker] = useState(false);
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(
    thread.agentId ? agents.find(a => a.id === thread.agentId) || null : null
  );
  const abortRef = useRef<AbortController | null>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo(0, scrollRef.current.scrollHeight);
  }, [thread.messages]);

  const sendMessage = useCallback(async (prompt: string, agentId?: string) => {
    onUpdate({ status: "loading" });

    const isFirst = thread.messages.filter(m => m.role === "user").length === 0;
    const fullPrompt = isFirst
      ? `I'm reading the file "${thread.filePath}". Here's the full content:\n\n${fileContent}\n\n---\n\nI've selected this specific section:\n\n> ${thread.selectedText}\n\nMy question about this selection: ${prompt}\n\nPlease focus your answer on the selected section, using the full file as context.`
      : prompt;

    // Create task for tracking
    let taskRef: Task | undefined;
    if (isFirst && createTask) {
      taskRef = createTask({
        type: "inline",
        title: prompt.slice(0, 60),
        prompt: fullPrompt,
        agentId: agentId || "",
        agentName: selectedAgent?.name || "",
        source: { kind: "inline", filePath: thread.filePath, selectedText: thread.selectedText },
      });
      onUpdate({ taskId: taskRef.id });
    }

    const newMessages: CommentMessage[] = [...thread.messages, { role: "assistant", content: "" }];
    onUpdate({ messages: newMessages });

    let currentReply = "";
    let sessionId = thread.sessionId;

    try {
      const controller = new AbortController();
      abortRef.current = controller;

      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          prompt: fullPrompt,
          agent_id: agentId || undefined,
          session_id: sessionId || undefined,
        }),
        signal: controller.signal,
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
              if (event.type === "session" && event.sessionId) {
                sessionId = event.sessionId;
              } else if (event.type === "text") {
                currentReply += event.content;
                const updated = [...newMessages];
                updated[updated.length - 1] = { role: "assistant", content: currentReply };
                onUpdate({ messages: updated, sessionId });
              } else if (event.type === "result_text" && !currentReply) {
                currentReply = event.content;
                const updated = [...newMessages];
                updated[updated.length - 1] = { role: "assistant", content: currentReply };
                onUpdate({ messages: updated, sessionId });
              }
            } catch { /* skip */ }
          }
        }
      }

      onUpdate({ status: "done", sessionId });
      if (taskRef) updateTask?.(taskRef.id, { status: "completed", result: currentReply, sessionId, completedAt: Date.now() });
    } catch (e: unknown) {
      if (e instanceof Error && e.name !== "AbortError") {
        const errMsg = `Error: ${e.message}`;
        const updated = [...newMessages];
        updated[updated.length - 1] = { role: "assistant", content: errMsg };
        onUpdate({ messages: updated, status: "error" });
        if (taskRef) updateTask?.(taskRef.id, { status: "error", error: e.message, completedAt: Date.now() });
      }
    }
    abortRef.current = null;
  }, [thread, fileContent, selectedAgent, onUpdate, createTask, updateTask]);

  const handleInputChange = (value: string) => {
    setInput(value);
    setShowAgentPicker(value.endsWith("@") || (value.startsWith("@") && !value.includes(" ")));
  };

  const pickAgent = (agent: Agent) => {
    const before = input.lastIndexOf("@");
    const prefix = before >= 0 ? input.slice(0, before) : input;
    setInput(`${prefix}@${agent.name} `);
    setSelectedAgent(agent);
    setShowAgentPicker(false);
    inputRef.current?.focus();
  };

  const handleSubmit = () => {
    const text = input.trim();
    if (!text || thread.status === "loading") return;

    let agentId = selectedAgent?.id;
    let prompt = text;
    const match = text.match(/^@(\S+)\s+([\s\S]+)/);
    if (match) {
      const agent = agents.find(a => a.name.toLowerCase() === match[1].toLowerCase());
      if (agent) { agentId = agent.id; prompt = match[2]; setSelectedAgent(agent); }
    }

    onUpdate({
      messages: [...thread.messages, { role: "user", content: prompt }],
      agentId: agentId || thread.agentId,
      agentName: selectedAgent?.name || thread.agentName,
    });
    setInput("");
    setShowAgentPicker(false);
    sendMessage(prompt, agentId);
  };

  const handleStop = () => { abortRef.current?.abort(); onUpdate({ status: "done" }); };

  return (
    <div className="rounded-lg border border-border bg-background shadow-sm">
      {/* Anchor header */}
      <div className="flex items-center justify-between rounded-t-lg border-b border-amber-200 bg-amber-50 px-3 py-1.5">
        <div className="flex items-center gap-1.5 min-w-0">
          <span className="shrink-0 text-amber-500 font-bold text-xs">|</span>
          <span className="truncate text-xs text-foreground/70">{thread.selectedText.slice(0, 60)}{thread.selectedText.length > 60 ? "..." : ""}</span>
        </div>
        <button onClick={onRemove} className="shrink-0 rounded p-0.5 text-muted hover:text-foreground">
          <X className="size-3.5" />
        </button>
      </div>

      {/* Messages */}
      {thread.messages.length > 0 && (
        <div ref={scrollRef} className="max-h-[250px] overflow-auto px-3 py-2 space-y-2">
          {thread.messages.map((msg, i) => (
            <div key={i} className="flex items-start gap-2">
              {msg.role === "user" ? (
                <div className="mt-0.5 flex size-5 shrink-0 items-center justify-center rounded-full bg-accent/10">
                  <span className="text-[10px] text-accent font-bold">U</span>
                </div>
              ) : (
                <Bot className="mt-0.5 size-5 shrink-0 text-muted" />
              )}
              <div className="min-w-0 flex-1">
                {msg.role === "user" ? (
                  <p className="text-xs leading-relaxed">{msg.content}</p>
                ) : (
                  <div className="markdown-body text-xs">
                    <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeHighlight]}>
                      {msg.content}
                    </ReactMarkdown>
                    {thread.status === "loading" && i === thread.messages.length - 1 && !msg.content && (
                      <Loader2 className="size-3.5 animate-spin text-muted" />
                    )}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Input */}
      <div className="border-t border-border px-3 py-2">
        {showAgentPicker && agents.length > 0 && (
          <div className="mb-2 rounded-lg border border-border bg-background p-1 shadow-lg">
            {agents.map(a => (
              <button key={a.id} onClick={() => pickAgent(a)} className="flex w-full items-center gap-2 rounded-md px-2 py-1 text-xs hover:bg-sidebar-hover">
                <span>{a.icon}</span><span className="font-medium">{a.name}</span>
              </button>
            ))}
          </div>
        )}
        {selectedAgent && (
          <div className="mb-1">
            <span className="inline-flex items-center gap-1 rounded-full bg-accent-light px-2 py-0.5 text-[10px] text-accent">
              {selectedAgent.icon} {selectedAgent.name}
              <button onClick={() => setSelectedAgent(null)} className="text-accent/50 hover:text-accent">×</button>
            </span>
          </div>
        )}
        <textarea
          ref={inputRef}
          value={input}
          onChange={e => handleInputChange(e.target.value)}
          onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSubmit(); } }}
          placeholder={thread.messages.length === 0 ? "Ask a question..." : "Reply..."}
          rows={1}
          className="w-full resize-none bg-transparent text-xs outline-none placeholder:text-muted"
        />
        <div className="flex items-center justify-between pt-1">
          <button onClick={() => setShowAgentPicker(!showAgentPicker)} className="rounded p-0.5 text-muted hover:bg-sidebar-hover" title="@">
            <span className="text-xs font-bold">@</span>
          </button>
          <div className="flex gap-1.5">
            {thread.status === "loading" ? (
              <button onClick={handleStop} className="rounded bg-red-500 px-2 py-0.5 text-[10px] text-white">
                <Square className="inline size-2 mr-0.5" />Stop
              </button>
            ) : (
              <button onClick={handleSubmit} disabled={!input.trim()} className="rounded bg-accent px-2 py-0.5 text-[10px] text-white disabled:opacity-40">
                Send
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export function CommentSidebar({
  threads,
  fileContent,
  agents,
  onUpdateThread,
  onRemoveThread,
  createTask,
  updateTask,
  onFileChanged,
}: CommentSidebarProps) {
  return (
    <div className="flex h-full w-[380px] shrink-0 flex-col border-l border-border bg-sidebar/30">
      <div className="flex items-center justify-between border-b border-border px-3 py-2">
        <div className="flex items-center gap-1.5">
          <MessageSquare className="size-3.5 text-muted" />
          <span className="text-xs font-semibold text-muted">Comments ({threads.length})</span>
        </div>
      </div>
      <div className="flex-1 overflow-auto p-3 space-y-3">
        {threads.length === 0 && (
          <p className="py-8 text-center text-xs text-muted">Select text to start a comment</p>
        )}
        {threads.map(thread => (
          <CommentCard
            key={thread.id}
            thread={thread}
            fileContent={fileContent}
            agents={agents}
            onUpdate={patch => onUpdateThread(thread.id, patch)}
            onRemove={() => onRemoveThread(thread.id)}
            createTask={createTask}
            updateTask={updateTask}
            onFileChanged={onFileChanged}
          />
        ))}
      </div>
    </div>
  );
}
