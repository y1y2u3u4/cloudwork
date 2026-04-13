"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { Send, Bot, User, Loader2, Square, FileText, X, Plus, Trash2, MessageSquare } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import { FileRefCard } from "./FileRefCard";
import type { Task, CreateTaskParams } from "@/lib/taskTypes";

interface Agent {
  id: string;
  name: string;
  icon: string;
  project_path: string;
  model: string;
  system_prompt: string;
  claude_md: string;
}

interface ChatMessage {
  role: "user" | "assistant" | "tool";
  content: string;
  toolName?: string;
  fileRefs?: { path: string; name: string }[];
}

interface ActiveFile {
  path: string;
  content: string;
}

export interface ContextQuote {
  text: string;
  filePath: string;
  lineRange?: string;
  agentId?: string;
  agentName?: string;
}

interface Conversation {
  id: string;
  title: string;
  agentId: string;
  agentName: string;
  sessionId: string;
  messages: ChatMessage[];
  createdAt: number;
  updatedAt: number;
}

const STORAGE_KEY = "workany-conversations";

function loadConversations(): Conversation[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function saveConversations(convos: Conversation[]) {
  if (typeof window === "undefined") return;
  localStorage.setItem(STORAGE_KEY, JSON.stringify(convos));
}

function generateId() {
  return Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
}

function truncateTitle(text: string, maxLen = 30): string {
  const clean = text.replace(/^@\S+\s+/, "").replace(/\[Context from[^\]]*\][\s\S]*?\n\n/, "").trim();
  return clean.length > maxLen ? clean.slice(0, maxLen) + "..." : clean;
}

export function ChatPanel({
  agents,
  activeFile,
  onFileChanged,
  contextQuote,
  onClearQuote,
  onOpenFile,
  createTask,
  updateTask,
  navigateToConversationId,
}: {
  agents: Agent[];
  activeFile?: ActiveFile;
  onFileChanged?: (path: string) => void;
  contextQuote?: ContextQuote | null;
  onClearQuote?: () => void;
  onOpenFile?: (path: string) => void;
  createTask?: (params: CreateTaskParams) => Task;
  updateTask?: (id: string, patch: Partial<Task>) => void;
  navigateToConversationId?: string | null;
}) {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConvoId, setActiveConvoId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [selectedAgent, setSelectedAgent] = useState<string>("");
  const [showAgentPicker, setShowAgentPicker] = useState(false);
  const [attachedFile, setAttachedFile] = useState<ActiveFile | null>(null);
  const [fileRefs, setFileRefs] = useState<{ path: string; name: string }[]>([]);
  const [isDragOver, setIsDragOver] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  const sessionIdRef = useRef<string>("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Load conversations from localStorage on mount
  useEffect(() => {
    const convos = loadConversations();
    setConversations(convos);
  }, []);

  // Auto-attach file when switching to chat with a file selected
  useEffect(() => {
    if (activeFile) {
      setAttachedFile(activeFile);
    }
  }, [activeFile]);

  useEffect(() => {
    scrollRef.current?.scrollTo(0, scrollRef.current.scrollHeight);
  }, [messages]);

  // When contextQuote arrives, set agent and focus input
  useEffect(() => {
    if (contextQuote) {
      if (contextQuote.agentId) setSelectedAgent(contextQuote.agentId);
      textareaRef.current?.focus();
    }
  }, [contextQuote]);

  const switchConversation = useCallback((convo: Conversation) => {
    setActiveConvoId(convo.id);
    setMessages(convo.messages);
    sessionIdRef.current = convo.sessionId;
    setSelectedAgent(convo.agentId);
  }, []);

  // Navigate to a specific conversation (from Tasks panel)
  useEffect(() => {
    if (navigateToConversationId) {
      const convos = loadConversations();
      const convo = convos.find(c => c.id === navigateToConversationId);
      if (convo) switchConversation(convo);
    }
  }, [navigateToConversationId, switchConversation]);

  const newConversation = useCallback(() => {
    setActiveConvoId(null);
    setMessages([]);
    sessionIdRef.current = "";
    setSelectedAgent("");
    setInput("");
    setFileRefs([]);
    onClearQuote?.();
  }, [onClearQuote]);

  const deleteConversation = useCallback((id: string) => {
    setConversations(prev => {
      const updated = prev.filter(c => c.id !== id);
      saveConversations(updated);
      return updated;
    });
    if (activeConvoId === id) newConversation();
  }, [activeConvoId, newConversation]);

  const persistMessages = useCallback((convoId: string, msgs: ChatMessage[], sessionId: string, agentId: string, agentName: string, title?: string) => {
    setConversations(prev => {
      const idx = prev.findIndex(c => c.id === convoId);
      let updated: Conversation[];
      if (idx >= 0) {
        updated = [...prev];
        updated[idx] = { ...updated[idx], messages: msgs, sessionId: sessionId || updated[idx].sessionId, updatedAt: Date.now() };
      } else {
        updated = [{ id: convoId, title: title || "New Chat", agentId, agentName, sessionId, messages: msgs, createdAt: Date.now(), updatedAt: Date.now() }, ...prev];
      }
      saveConversations(updated);
      return updated;
    });
  }, []);

  const parseAgentMention = (text: string): { agentId: string; prompt: string } | null => {
    const match = text.match(/^@(\S+)\s+([\s\S]+)/);
    if (match) {
      const agent = agents.find(a => a.name.toLowerCase() === match[1].toLowerCase());
      if (agent) return { agentId: agent.id, prompt: match[2] };
    }
    return null;
  };

  // Drag & drop handlers
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = "copy";
    setIsDragOver(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    if (e.currentTarget.contains(e.relatedTarget as Node)) return;
    setIsDragOver(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);

    // Check workspace file first
    const wsData = e.dataTransfer.getData("application/workspace-file");
    if (wsData) {
      try {
        const file = JSON.parse(wsData);
        if (file.path && !fileRefs.some(f => f.path === file.path)) {
          setFileRefs(prev => [...prev, { path: file.path, name: file.name }]);
        }
      } catch { /* skip */ }
      return;
    }

    // System files — read as text and attach
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      const file = files[0];
      const reader = new FileReader();
      reader.onload = () => {
        setAttachedFile({ path: file.name, content: reader.result as string });
      };
      reader.readAsText(file);
    }
  };

  const removeFileRef = (path: string) => {
    setFileRefs(prev => prev.filter(f => f.path !== path));
  };

  const handleSubmit = async () => {
    const text = input.trim();
    if (!text || loading) return;

    const mention = parseAgentMention(text);
    const agentId = mention?.agentId || selectedAgent || "";
    const prompt = mention?.prompt || text;

    const agent = agents.find(a => a.id === agentId);

    // Build full prompt with context quote + file refs
    let fullPrompt = prompt;
    if (contextQuote) {
      fullPrompt = `[Context from ${contextQuote.filePath}${contextQuote.lineRange ? `:${contextQuote.lineRange}` : ""}]\n${contextQuote.text}\n\n${fullPrompt}`;
    }

    // Build display message
    const parts: string[] = [];
    if (agent) parts.push(`@${agent.name}`);
    parts.push(prompt);
    if (contextQuote) parts.push(`\n📌 ${contextQuote.filePath}`);
    if (fileRefs.length > 0) parts.push(`\n${fileRefs.map(f => `📎 ${f.name}`).join("\n")}`);
    if (attachedFile) parts.push(`\n📎 ${attachedFile.path.split("/").pop()}`);

    const userMsg: ChatMessage = {
      role: "user",
      content: parts.join(" "),
      fileRefs: fileRefs.length > 0 ? [...fileRefs] : undefined,
    };

    const newMessages = [...messages, userMsg];
    setMessages(newMessages);
    setInput("");
    setLoading(true);

    const convoId = activeConvoId || generateId();
    if (!activeConvoId) setActiveConvoId(convoId);

    // Create task for tracking
    const taskRef = createTask?.({
      type: "chat",
      title: prompt.slice(0, 60),
      prompt,
      agentId,
      agentName: agent?.name || "",
      source: { kind: "chat", conversationId: convoId },
    });

    setMessages(prev => [...prev, { role: "assistant", content: "" }]);

    let currentSessionId = sessionIdRef.current;

    // Fetch file ref contents to include in prompt
    const fileContextParts: string[] = [];
    for (const ref of fileRefs) {
      try {
        const res = await fetch(`/api/workspace?action=read&path=${encodeURIComponent(ref.path)}`);
        const data = await res.json();
        if (data.content) {
          fileContextParts.push(`[Referenced file: ${ref.name}]\n${data.content}`);
        }
      } catch { /* skip */ }
    }
    if (fileContextParts.length > 0) {
      fullPrompt = fileContextParts.join("\n\n") + "\n\n" + fullPrompt;
    }

    try {
      const controller = new AbortController();
      abortRef.current = controller;

      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          prompt: fullPrompt,
          agent_id: agentId,
          session_id: currentSessionId || undefined,
          file_context: attachedFile ? { path: attachedFile.path, content: attachedFile.content } : undefined,
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
                currentSessionId = event.sessionId;
                sessionIdRef.current = event.sessionId;
              } else if (event.type === "text") {
                setMessages(prev => {
                  const updated = [...prev];
                  for (let j = updated.length - 1; j >= 0; j--) {
                    if (updated[j].role === "assistant") {
                      updated[j] = { ...updated[j], content: updated[j].content + event.content };
                      break;
                    }
                  }
                  return updated;
                });
              } else if (event.type === "result_text") {
                setMessages(prev => {
                  const updated = [...prev];
                  for (let j = updated.length - 1; j >= 0; j--) {
                    if (updated[j].role === "assistant") {
                      if (!updated[j].content) updated[j] = { ...updated[j], content: event.content };
                      break;
                    }
                  }
                  return updated;
                });
              } else if (event.type === "tool_use") {
                setMessages(prev => [...prev, {
                  role: "tool",
                  content: JSON.stringify(event.input, null, 2).slice(0, 200),
                  toolName: event.name,
                }]);
              }
            } catch { /* skip */ }
          }
        }
      }
    } catch (e: unknown) {
      if (e instanceof Error && e.name !== "AbortError") {
        setMessages(prev => [...prev, { role: "assistant", content: `Error: ${e.message}` }]);
        if (taskRef) updateTask?.(taskRef.id, { status: "error", error: e.message, completedAt: Date.now() });
      }
    }

    abortRef.current = null;
    setLoading(false);
    setFileRefs([]);
    onClearQuote?.();

    // Update task tracking
    if (taskRef) {
      updateTask?.(taskRef.id, { status: "completed", sessionId: currentSessionId, completedAt: Date.now() });
    }

    setMessages(prev => {
      persistMessages(convoId, prev, currentSessionId, agentId, agent?.name || "", truncateTitle(userMsg.content));
      return prev;
    });

    if (attachedFile) onFileChanged?.(attachedFile.path);
  };

  const handleStop = () => {
    abortRef.current?.abort();
    setLoading(false);
  };

  const handleInputChange = (value: string) => {
    setInput(value);
    setShowAgentPicker(value.endsWith("@") || (value.startsWith("@") && !value.includes(" ")));
  };

  const insertAgent = (agent: Agent) => {
    const before = input.lastIndexOf("@");
    const prefix = before >= 0 ? input.slice(0, before) : input;
    setInput(`${prefix}@${agent.name} `);
    setShowAgentPicker(false);
  };

  return (
    <div className="flex h-full">
      {/* Conversation list sidebar */}
      <div className="flex w-52 shrink-0 flex-col border-r border-border bg-sidebar">
        <div className="flex items-center justify-between px-3 py-2.5">
          <span className="text-xs font-semibold text-muted uppercase tracking-wider">Chats</span>
          <button onClick={newConversation} className="rounded p-1 text-muted transition-colors hover:bg-sidebar-hover hover:text-foreground" title="New Chat">
            <Plus className="size-3.5" />
          </button>
        </div>
        <div className="flex-1 overflow-auto px-1.5">
          {conversations.length === 0 ? (
            <p className="px-2 py-4 text-center text-xs text-muted">No conversations</p>
          ) : (
            <div className="space-y-0.5">
              {conversations.map(convo => (
                <div
                  key={convo.id}
                  className={`group flex items-center gap-1.5 rounded-md px-2 py-1.5 text-sm cursor-pointer transition-colors ${
                    activeConvoId === convo.id ? "bg-accent-light text-accent" : "text-foreground/70 hover:bg-sidebar-hover"
                  }`}
                  onClick={() => switchConversation(convo)}
                >
                  <MessageSquare className="size-3.5 shrink-0" />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-xs font-medium">{convo.title}</p>
                    {convo.agentName && <p className="truncate text-xs text-muted">{convo.agentName}</p>}
                  </div>
                  <button
                    onClick={e => { e.stopPropagation(); deleteConversation(convo.id); }}
                    className="hidden shrink-0 rounded p-0.5 text-muted hover:text-red-500 group-hover:block"
                  >
                    <Trash2 className="size-3" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Chat area with drop zone */}
      <div
        className={`flex min-w-0 flex-1 flex-col transition-colors ${isDragOver ? "bg-accent/5 ring-2 ring-inset ring-accent/30 ring-dashed" : ""}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        {/* Drag overlay */}
        {isDragOver && (
          <div className="pointer-events-none absolute inset-0 z-10 flex items-center justify-center">
            <div className="rounded-xl border-2 border-dashed border-accent/50 bg-accent/10 px-8 py-4">
              <p className="text-sm font-medium text-accent">Drop file to add as context</p>
            </div>
          </div>
        )}

        {/* Messages */}
        <div ref={scrollRef} className="flex-1 overflow-auto px-4 py-3">
          {messages.length === 0 && (
            <div className="flex h-full items-center justify-center">
              <div className="text-center">
                <p className="text-sm text-muted">
                  Type a message or <span className="font-mono text-accent">@agent</span> to start
                </p>
                <p className="mt-1 text-xs text-muted/60">
                  Drag files here to add context
                </p>
                {agents.length > 0 && (
                  <div className="mt-3 flex flex-wrap justify-center gap-2">
                    {agents.map(a => (
                      <button
                        key={a.id}
                        onClick={() => { setInput(`@${a.name} `); setSelectedAgent(a.id); }}
                        className="flex items-center gap-1.5 rounded-full border border-border px-3 py-1 text-xs transition-colors hover:bg-sidebar-hover"
                      >
                        <span>{a.icon}</span>
                        <span>{a.name}</span>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          <div className="mx-auto max-w-3xl space-y-3">
            {messages.map((msg, i) => (
              <div key={i} className="flex gap-2.5">
                {msg.role === "user" ? (
                  <div className="mt-0.5 flex size-6 shrink-0 items-center justify-center rounded-full bg-accent/10">
                    <User className="size-3.5 text-accent" />
                  </div>
                ) : msg.role === "tool" ? (
                  <div className="mt-0.5 flex size-6 shrink-0 items-center justify-center rounded-full bg-orange-100">
                    <span className="text-xs">🔧</span>
                  </div>
                ) : (
                  <div className="mt-0.5 flex size-6 shrink-0 items-center justify-center rounded-full bg-sidebar">
                    <Bot className="size-3.5 text-muted" />
                  </div>
                )}
                <div className="min-w-0 flex-1">
                  {msg.role === "tool" ? (
                    <div className="rounded-lg bg-orange-50 p-2.5">
                      <p className="text-xs font-medium text-orange-700">{msg.toolName}</p>
                      <pre className="mt-1 overflow-x-auto text-xs text-orange-600">{msg.content}</pre>
                    </div>
                  ) : msg.role === "user" ? (
                    <div>
                      <p className="text-sm leading-relaxed">{msg.content}</p>
                      {/* File reference cards */}
                      {msg.fileRefs?.map(ref => (
                        <FileRefCard
                          key={ref.path}
                          name={ref.name}
                          filePath={ref.path}
                          onClick={() => onOpenFile?.(ref.path)}
                        />
                      ))}
                    </div>
                  ) : (
                    <div className="markdown-body text-sm">
                      <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeHighlight]}>
                        {msg.content}
                      </ReactMarkdown>
                      {loading && i === messages.length - 1 && !msg.content && (
                        <Loader2 className="size-4 animate-spin text-muted" />
                      )}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Input area */}
        <div className="shrink-0 border-t border-border px-4 py-3">
          <div className="relative mx-auto max-w-3xl">
            {/* Agent picker popup */}
            {showAgentPicker && agents.length > 0 && (
              <div className="absolute bottom-full left-0 mb-2 rounded-lg border border-border bg-background p-1 shadow-lg">
                {agents.map(a => (
                  <button
                    key={a.id}
                    onClick={() => insertAgent(a)}
                    className="flex w-full items-center gap-2 rounded-md px-3 py-1.5 text-sm transition-colors hover:bg-sidebar-hover"
                  >
                    <span>{a.icon}</span>
                    <span>{a.name}</span>
                    <span className="ml-auto text-xs text-muted">{a.project_path || "default"}</span>
                  </button>
                ))}
              </div>
            )}

            {/* Context quote block */}
            {contextQuote && (
              <div className="mb-2 flex items-start gap-2 rounded-lg border-l-2 border-accent bg-accent/5 px-3 py-2">
                <div className="min-w-0 flex-1">
                  <p className="text-xs font-medium text-accent">{contextQuote.filePath}{contextQuote.lineRange ? `:${contextQuote.lineRange}` : ""}</p>
                  <p className="mt-0.5 line-clamp-3 font-mono text-xs text-foreground/70">{contextQuote.text}</p>
                </div>
                <button onClick={onClearQuote} className="shrink-0 text-muted hover:text-foreground">
                  <X className="size-3.5" />
                </button>
              </div>
            )}

            {/* File reference chips */}
            {fileRefs.length > 0 && (
              <div className="mb-2 flex flex-wrap gap-1.5">
                {fileRefs.map(ref => (
                  <span key={ref.path} className="flex items-center gap-1 rounded-lg border border-accent/20 bg-accent-light px-2 py-0.5 text-xs text-accent">
                    <FileText className="size-3" />
                    <span className="max-w-[160px] truncate font-medium">{ref.name}</span>
                    <button onClick={() => removeFileRef(ref.path)} className="text-accent/40 hover:text-accent">
                      <X className="size-3" />
                    </button>
                  </span>
                ))}
              </div>
            )}

            {/* Attached file badge */}
            {attachedFile && (
              <div className="mb-2 flex items-center gap-1.5">
                <span className="flex items-center gap-1.5 rounded-lg border border-accent/20 bg-accent-light px-2.5 py-1 text-xs text-accent">
                  <FileText className="size-3" />
                  <span className="max-w-[200px] truncate font-medium">{attachedFile.path.split("/").pop()}</span>
                  <span className="text-accent/50">{(attachedFile.content.length / 1024).toFixed(1)}KB</span>
                  <button onClick={() => setAttachedFile(null)} className="ml-0.5 text-accent/40 hover:text-accent">
                    <X className="size-3" />
                  </button>
                </span>
              </div>
            )}

            {/* Selected agent badge */}
            {selectedAgent && !input.startsWith("@") && (
              <div className="mb-2 flex items-center gap-1.5">
                <span className="flex items-center gap-1 rounded-full bg-accent-light px-2.5 py-0.5 text-xs text-accent">
                  {agents.find(a => a.id === selectedAgent)?.icon}{" "}
                  {agents.find(a => a.id === selectedAgent)?.name}
                  <button onClick={() => setSelectedAgent("")} className="ml-1 text-accent/50 hover:text-accent">×</button>
                </span>
              </div>
            )}

            <div className="flex items-end gap-2 rounded-xl border border-border bg-background px-3 py-2 shadow-sm focus-within:border-accent/50 focus-within:ring-1 focus-within:ring-accent/20">
              <textarea
                ref={textareaRef}
                value={input}
                onChange={e => handleInputChange(e.target.value)}
                onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSubmit(); } }}
                placeholder="Message... (use @agent to route)"
                rows={1}
                className="max-h-32 min-h-[24px] flex-1 resize-none bg-transparent text-sm outline-none"
              />
              {loading ? (
                <button onClick={handleStop} className="flex size-7 shrink-0 items-center justify-center rounded-lg bg-red-500 text-white transition-colors hover:bg-red-600">
                  <Square className="size-3" />
                </button>
              ) : (
                <button
                  onClick={handleSubmit}
                  disabled={!input.trim()}
                  className="flex size-7 shrink-0 items-center justify-center rounded-lg bg-accent text-white transition-colors hover:bg-accent/90 disabled:opacity-30"
                >
                  <Send className="size-3.5" />
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
