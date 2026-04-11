"use client";

import { useState, useRef, useEffect } from "react";
import { Send, Bot, User, Loader2, Square, FileText, X } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";

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
}

interface ActiveFile {
  path: string;
  content: string;
}

export function ChatPanel({
  agents,
  activeFile,
  onFileChanged,
}: {
  agents: Agent[];
  activeFile?: ActiveFile;
  onFileChanged?: (path: string) => void;
}) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [selectedAgent, setSelectedAgent] = useState<string>("");
  const [showAgentPicker, setShowAgentPicker] = useState(false);
  const [attachedFile, setAttachedFile] = useState<ActiveFile | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  // Auto-attach file when switching to chat with a file selected
  useEffect(() => {
    if (activeFile) {
      setAttachedFile(activeFile);
    }
  }, [activeFile]);

  useEffect(() => {
    scrollRef.current?.scrollTo(0, scrollRef.current.scrollHeight);
  }, [messages]);

  // Parse @agent from input
  const parseAgentMention = (
    text: string
  ): { agentId: string; prompt: string } | null => {
    const match = text.match(/^@(\S+)\s+([\s\S]+)/);
    if (match) {
      const name = match[1];
      const agent = agents.find(
        (a) => a.name.toLowerCase() === name.toLowerCase()
      );
      if (agent) return { agentId: agent.id, prompt: match[2] };
    }
    return null;
  };

  const handleSubmit = async () => {
    const text = input.trim();
    if (!text || loading) return;

    // Parse @mention or use selected agent
    const mention = parseAgentMention(text);
    const agentId = mention?.agentId || selectedAgent || "";
    const prompt = mention?.prompt || text;

    const agent = agents.find((a) => a.id === agentId);
    const fileLabel = attachedFile ? `\n📎 ${attachedFile.path.split("/").pop()}` : "";
    const userMsg: ChatMessage = {
      role: "user",
      content: (agent ? `@${agent.name} ${prompt}` : prompt) + fileLabel,
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    const assistantMsg: ChatMessage = { role: "assistant", content: "" };
    setMessages((prev) => [...prev, assistantMsg]);

    try {
      const controller = new AbortController();
      abortRef.current = controller;

      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          prompt,
          agent_id: agentId,
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

              if (event.type === "text") {
                setMessages((prev) => {
                  const updated = [...prev];
                  // Find the last assistant message to append to
                  let found = false;
                  for (let j = updated.length - 1; j >= 0; j--) {
                    if (updated[j].role === "assistant") {
                      updated[j] = { ...updated[j], content: updated[j].content + event.content };
                      found = true;
                      break;
                    }
                  }
                  if (!found) {
                    updated.push({ role: "assistant", content: event.content });
                  }
                  return updated;
                });
              } else if (event.type === "result_text") {
                // Final result - if assistant message is empty, use this as the answer
                setMessages((prev) => {
                  const updated = [...prev];
                  // Find the last assistant message
                  for (let j = updated.length - 1; j >= 0; j--) {
                    if (updated[j].role === "assistant") {
                      if (!updated[j].content) {
                        updated[j] = { ...updated[j], content: event.content };
                      }
                      break;
                    }
                  }
                  return updated;
                });
              } else if (event.type === "tool_use") {
                setMessages((prev) => [
                  ...prev,
                  {
                    role: "tool",
                    content: JSON.stringify(event.input, null, 2).slice(0, 200),
                    toolName: event.name,
                  },
                ]);
              }
            } catch {
              // skip
            }
          }
        }
      }
    } catch (e: unknown) {
      if (e instanceof Error && e.name !== "AbortError") {
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: `Error: ${e.message}` },
        ]);
      }
    }

    abortRef.current = null;
    setLoading(false);
    // Notify parent to reload file if agent may have modified it
    if (attachedFile) {
      onFileChanged?.(attachedFile.path);
    }
  };

  const handleStop = () => {
    abortRef.current?.abort();
    setLoading(false);
  };

  const handleInputChange = (value: string) => {
    setInput(value);
    // Show agent picker on @
    if (value.endsWith("@") || (value.startsWith("@") && !value.includes(" "))) {
      setShowAgentPicker(true);
    } else {
      setShowAgentPicker(false);
    }
  };

  const insertAgent = (agent: Agent) => {
    const before = input.lastIndexOf("@");
    const prefix = before >= 0 ? input.slice(0, before) : input;
    setInput(`${prefix}@${agent.name} `);
    setShowAgentPicker(false);
  };

  return (
    <div className="flex h-full flex-col">
      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-auto px-4 py-3">
        {messages.length === 0 && (
          <div className="flex h-full items-center justify-center">
            <div className="text-center">
              <p className="text-sm text-muted">
                Type a message or <span className="font-mono text-accent">@agent</span> to start
              </p>
              {agents.length > 0 && (
                <div className="mt-3 flex flex-wrap justify-center gap-2">
                  {agents.map((a) => (
                    <button
                      key={a.id}
                      onClick={() => {
                        setInput(`@${a.name} `);
                        setSelectedAgent(a.id);
                      }}
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
                    <p className="text-xs font-medium text-orange-700">
                      {msg.toolName}
                    </p>
                    <pre className="mt-1 overflow-x-auto text-xs text-orange-600">
                      {msg.content}
                    </pre>
                  </div>
                ) : msg.role === "user" ? (
                  <p className="text-sm leading-relaxed">{msg.content}</p>
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
              {agents.map((a) => (
                <button
                  key={a.id}
                  onClick={() => insertAgent(a)}
                  className="flex w-full items-center gap-2 rounded-md px-3 py-1.5 text-sm transition-colors hover:bg-sidebar-hover"
                >
                  <span>{a.icon}</span>
                  <span>{a.name}</span>
                  <span className="ml-auto text-xs text-muted">
                    {a.project_path || "default"}
                  </span>
                </button>
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
                <button
                  onClick={() => setAttachedFile(null)}
                  className="ml-0.5 text-accent/40 hover:text-accent"
                >
                  <X className="size-3" />
                </button>
              </span>
            </div>
          )}

          {/* Selected agent badge */}
          {selectedAgent && !input.startsWith("@") && (
            <div className="mb-2 flex items-center gap-1.5">
              <span className="flex items-center gap-1 rounded-full bg-accent-light px-2.5 py-0.5 text-xs text-accent">
                {agents.find((a) => a.id === selectedAgent)?.icon}{" "}
                {agents.find((a) => a.id === selectedAgent)?.name}
                <button
                  onClick={() => setSelectedAgent("")}
                  className="ml-1 text-accent/50 hover:text-accent"
                >
                  ×
                </button>
              </span>
            </div>
          )}

          <div className="flex items-end gap-2 rounded-xl border border-border bg-background px-3 py-2 shadow-sm focus-within:border-accent/50 focus-within:ring-1 focus-within:ring-accent/20">
            <textarea
              value={input}
              onChange={(e) => handleInputChange(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSubmit();
                }
              }}
              placeholder="Message... (use @agent to route)"
              rows={1}
              className="max-h-32 min-h-[24px] flex-1 resize-none bg-transparent text-sm outline-none"
            />
            {loading ? (
              <button
                onClick={handleStop}
                className="flex size-7 shrink-0 items-center justify-center rounded-lg bg-red-500 text-white transition-colors hover:bg-red-600"
              >
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
  );
}
