"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { Send, X, Loader2, Bot, User, Check, SkipForward, Square } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";

interface Agent {
  id: string;
  name: string;
  icon: string;
}

interface ThreadMessage {
  role: "user" | "assistant";
  content: string;
  applied?: boolean;
}

interface ThreadPanelProps {
  filePath: string;
  selectedText: string;
  fileContent: string; // full file content for context
  agents: Agent[];
  onClose: () => void;
  onFileChanged?: (path: string) => void;
  initialResult?: string;
}

// Detect if AI response contains code suggestions (code blocks or edit instructions)
function hasCodeSuggestion(content: string): boolean {
  return /```[\s\S]+```/.test(content) || /修改|改为|替换|更新|添加|删除|change|update|replace|add|remove/i.test(content);
}

export function ThreadPanel({
  filePath,
  selectedText,
  fileContent,
  agents,
  onClose,
  onFileChanged,
  initialResult,
}: ThreadPanelProps) {
  const [messages, setMessages] = useState<ThreadMessage[]>(() => {
    if (initialResult) {
      return [{ role: "assistant", content: initialResult }];
    }
    return [];
  });
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null);
  const [showAgentPicker, setShowAgentPicker] = useState(false);
  const [applying, setApplying] = useState<number | null>(null);

  const sessionIdRef = useRef<string>("");
  const abortRef = useRef<AbortController | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo(0, scrollRef.current.scrollHeight);
  }, [messages]);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

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

  const sendMessage = useCallback(async (prompt: string, agentId?: string) => {
    setLoading(true);

    const isFirstMessage = messages.length === 0 && !sessionIdRef.current;
    const fullPrompt = isFirstMessage
      ? `[Context from ${filePath}]\n${selectedText}\n\n${prompt}`
      : prompt;

    let currentReply = "";
    setMessages(prev => [...prev, { role: "assistant", content: "" }]);

    try {
      const controller = new AbortController();
      abortRef.current = controller;

      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          prompt: fullPrompt,
          agent_id: agentId || undefined,
          session_id: sessionIdRef.current || undefined,
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
                sessionIdRef.current = event.sessionId;
              } else if (event.type === "text") {
                currentReply += event.content;
                setMessages(prev => {
                  const updated = [...prev];
                  updated[updated.length - 1] = { role: "assistant", content: currentReply };
                  return updated;
                });
              } else if (event.type === "result_text" && !currentReply) {
                currentReply = event.content;
                setMessages(prev => {
                  const updated = [...prev];
                  updated[updated.length - 1] = { role: "assistant", content: currentReply };
                  return updated;
                });
              }
            } catch { /* skip */ }
          }
        }
      }
    } catch (e: unknown) {
      if (e instanceof Error && e.name !== "AbortError") {
        currentReply = `Error: ${e.message}`;
        setMessages(prev => {
          const updated = [...prev];
          updated[updated.length - 1] = { role: "assistant", content: currentReply };
          return updated;
        });
      }
    }

    abortRef.current = null;
    setLoading(false);
  }, [messages.length, filePath, selectedText]);

  const handleSubmit = () => {
    const text = input.trim();
    if (!text || loading) return;

    let agentId = selectedAgent?.id || "";
    let prompt = text;

    const mentionMatch = text.match(/^@(\S+)\s+([\s\S]+)/);
    if (mentionMatch) {
      const agent = agents.find(a => a.name.toLowerCase() === mentionMatch[1].toLowerCase());
      if (agent) {
        agentId = agent.id;
        prompt = mentionMatch[2];
        if (!selectedAgent) setSelectedAgent(agent);
      }
    }

    setMessages(prev => [...prev, { role: "user", content: prompt }]);
    setInput("");
    setShowAgentPicker(false);
    sendMessage(prompt, agentId);
  };

  const handleStop = () => {
    abortRef.current?.abort();
    setLoading(false);
  };

  const handleApply = async (msgIndex: number) => {
    setApplying(msgIndex);
    const applyPrompt = `Please apply the changes you just suggested to the file at ${filePath}. Use the Edit or Write tool to make the modifications directly.`;

    setMessages(prev => [...prev, { role: "user", content: "Apply changes to file" }]);
    await sendMessage(applyPrompt, selectedAgent?.id);

    setMessages(prev =>
      prev.map((m, i) => i === msgIndex ? { ...m, applied: true } : m)
    );
    setApplying(null);
    onFileChanged?.(filePath);
  };

  const handleSkip = (msgIndex: number) => {
    setMessages(prev =>
      prev.map((m, i) => i === msgIndex ? { ...m, applied: false } : m)
    );
  };

  return (
    <div className="fixed right-0 top-0 z-40 flex h-screen w-[420px] flex-col border-l border-border bg-background shadow-2xl transition-transform animate-in slide-in-from-right duration-200">
      {/* Collapse handle — tab on the left edge */}
      <button
        onClick={onClose}
        className="absolute -left-6 top-1/2 z-40 flex h-12 w-6 -translate-y-1/2 items-center justify-center rounded-l-md border border-r-0 border-border bg-background text-muted shadow-md hover:bg-sidebar-hover hover:text-foreground"
        title="Close panel"
      >
        <svg width="10" height="10" viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
          <path d="M3 1L7 5L3 9" />
        </svg>
      </button>

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
          <span className="max-w-[200px] truncate text-muted">{filePath.split("/").pop()}</span>
        </div>
        <button onClick={onClose} className="rounded p-1 text-muted hover:text-foreground">
          <X className="size-4" />
        </button>
      </div>

      {/* Quoted text — compact, like Feishu comment anchor */}
      <div className="border-b border-border bg-accent/5 px-3 py-2">
        <p className="line-clamp-2 text-xs leading-relaxed text-foreground/70">{selectedText}</p>
      </div>

      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-auto px-3 py-3 space-y-3">
        {messages.length === 0 && !loading && (
          <p className="text-center text-xs text-muted py-8">Ask a question about this selection</p>
        )}

        {messages.map((msg, i) => (
          <div key={i}>
            <div className="flex gap-2">
              {msg.role === "assistant" ? (
                <Bot className="mt-0.5 size-4 shrink-0 text-muted" />
              ) : (
                <User className="mt-0.5 size-4 shrink-0 text-accent" />
              )}
              <div className="min-w-0 flex-1">
                {msg.role === "user" ? (
                  <p className="text-xs leading-relaxed">{msg.content}</p>
                ) : (
                  <div className="markdown-body text-xs">
                    <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeHighlight]}>
                      {msg.content}
                    </ReactMarkdown>
                    {loading && i === messages.length - 1 && !msg.content && (
                      <Loader2 className="size-3.5 animate-spin text-muted" />
                    )}
                  </div>
                )}
              </div>
            </div>

            {/* Apply/Skip buttons for assistant messages with code suggestions */}
            {msg.role === "assistant" && msg.content && !loading && hasCodeSuggestion(msg.content) && msg.applied === undefined && (
              <div className="ml-6 mt-2 flex gap-2">
                <button
                  onClick={() => handleApply(i)}
                  disabled={applying !== null}
                  className="flex items-center gap-1 rounded-md bg-accent px-2.5 py-1 text-xs text-white hover:bg-accent/90 disabled:opacity-50"
                >
                  {applying === i ? <Loader2 className="size-3 animate-spin" /> : <Check className="size-3" />}
                  Apply
                </button>
                <button
                  onClick={() => handleSkip(i)}
                  className="flex items-center gap-1 rounded-md border border-border px-2.5 py-1 text-xs text-muted hover:bg-sidebar-hover"
                >
                  <SkipForward className="size-3" />
                  Skip
                </button>
              </div>
            )}
            {msg.role === "assistant" && msg.applied === true && (
              <div className="ml-6 mt-1">
                <span className="flex items-center gap-1 text-xs text-green-600">
                  <Check className="size-3" /> Applied
                </span>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Input area */}
      <div className="relative shrink-0 border-t border-border px-3 py-2">
        {/* Agent picker */}
        {showAgentPicker && agents.length > 0 && (
          <div className="absolute bottom-full left-3 mb-1 rounded-lg border border-border bg-background p-1 shadow-lg">
            {agents.map(a => (
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
        )}

        {/* Agent badge */}
        {selectedAgent && (
          <div className="mb-1.5">
            <span className="inline-flex items-center gap-1 rounded-full bg-accent-light px-2 py-0.5 text-xs text-accent">
              {selectedAgent.icon} {selectedAgent.name}
              <button onClick={() => setSelectedAgent(null)} className="text-accent/50 hover:text-accent">×</button>
            </span>
          </div>
        )}

        <div className="flex items-end gap-2 rounded-lg border border-border bg-background px-2.5 py-1.5 focus-within:border-accent/50">
          <textarea
            ref={inputRef}
            value={input}
            onChange={e => handleInputChange(e.target.value)}
            onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSubmit(); } }}
            placeholder={messages.length === 0 ? "Ask about this... (@ to pick agent)" : "Follow up..."}
            rows={1}
            className="max-h-20 min-h-[20px] flex-1 resize-none bg-transparent text-xs outline-none"
          />
          {loading ? (
            <button onClick={handleStop} className="flex size-6 shrink-0 items-center justify-center rounded-md bg-red-500 text-white">
              <Square className="size-2.5" />
            </button>
          ) : (
            <button
              onClick={handleSubmit}
              disabled={!input.trim()}
              className="flex size-6 shrink-0 items-center justify-center rounded-md bg-accent text-white disabled:opacity-30"
            >
              <Send className="size-3" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
