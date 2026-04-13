"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { Loader2, Bot, Square } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";

interface Agent {
  id: string;
  name: string;
  icon: string;
}

interface CommentMessage {
  role: "user" | "assistant";
  content: string;
}

interface CommentBoxProps {
  selectedText: string;
  filePath: string;
  fileContent: string;
  agents: Agent[];
  onClose: () => void;
  onFileChanged?: (path: string) => void;
}

export function CommentBox({
  selectedText,
  filePath,
  fileContent,
  agents,
  onClose,
  onFileChanged,
}: CommentBoxProps) {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<CommentMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [showAgentPicker, setShowAgentPicker] = useState(false);
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null);
  const sessionIdRef = useRef("");
  const abortRef = useRef<AbortController | null>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => { inputRef.current?.focus(); }, []);
  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [onClose]);
  useEffect(() => {
    scrollRef.current?.scrollTo(0, scrollRef.current.scrollHeight);
  }, [messages]);

  const sendMessage = useCallback(async (prompt: string, agentId?: string) => {
    setLoading(true);

    // First message: include full file + highlight the selected section
    const isFirst = messages.length === 0 && !sessionIdRef.current;
    const fullPrompt = isFirst
      ? `I'm reading the file "${filePath}". Here's the full content:\n\n${fileContent}\n\n---\n\nI've selected this specific section:\n\n> ${selectedText}\n\nMy question about this selection: ${prompt}\n\nPlease focus your answer on the selected section, using the full file as context.`
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
              if (event.type === "session" && event.sessionId) sessionIdRef.current = event.sessionId;
              else if (event.type === "text") {
                currentReply += event.content;
                setMessages(prev => { const u = [...prev]; u[u.length - 1] = { role: "assistant", content: currentReply }; return u; });
              } else if (event.type === "result_text" && !currentReply) {
                currentReply = event.content;
                setMessages(prev => { const u = [...prev]; u[u.length - 1] = { role: "assistant", content: currentReply }; return u; });
              }
            } catch { /* skip */ }
          }
        }
      }
    } catch (e: unknown) {
      if (e instanceof Error && e.name !== "AbortError") {
        currentReply = `Error: ${e.message}`;
        setMessages(prev => { const u = [...prev]; u[u.length - 1] = { role: "assistant", content: currentReply }; return u; });
      }
    }
    abortRef.current = null;
    setLoading(false);
  }, [messages.length, filePath, fileContent, selectedText]);

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
    if (!text || loading) return;

    let agentId = selectedAgent?.id;
    let prompt = text;
    const match = text.match(/^@(\S+)\s+([\s\S]+)/);
    if (match) {
      const agent = agents.find(a => a.name.toLowerCase() === match[1].toLowerCase());
      if (agent) { agentId = agent.id; prompt = match[2]; if (!selectedAgent) setSelectedAgent(agent); }
    }

    setMessages(prev => [...prev, { role: "user", content: prompt }]);
    setInput("");
    setShowAgentPicker(false);
    sendMessage(prompt, agentId);
  };

  const handleStop = () => { abortRef.current?.abort(); setLoading(false); };

  return (
    <div className="flex h-full w-full flex-col rounded-lg border border-border bg-background shadow-sm">
      {/* Anchor header — like Feishu's "#3 | 蔬菜解决价格竞..." */}
      <div className="flex items-center justify-between rounded-t-lg border-b border-amber-200 bg-amber-50 px-3 py-2">
        <div className="flex items-center gap-1.5 min-w-0">
          <span className="shrink-0 text-amber-500 font-bold text-xs">|</span>
          <span className="truncate text-xs text-foreground/70">{selectedText.slice(0, 80)}{selectedText.length > 80 ? "..." : ""}</span>
        </div>
        <div className="flex items-center gap-1 shrink-0">
          {selectedAgent && <span className="text-xs text-accent">{selectedAgent.icon}</span>}
          <button onClick={onClose} className="rounded p-0.5 text-muted hover:text-foreground">
            <span className="text-lg leading-none">×</span>
          </button>
        </div>
      </div>

      {/* Messages area */}
      {messages.length > 0 && (
        <div ref={scrollRef} className="flex-1 overflow-auto px-3 py-2 space-y-3 max-h-[300px]">
          {messages.map((msg, i) => (
            <div key={i}>
              {msg.role === "user" ? (
                <div className="flex items-start gap-2">
                  <div className="mt-0.5 flex size-5 shrink-0 items-center justify-center rounded-full bg-accent/10">
                    <span className="text-[10px] text-accent font-bold">U</span>
                  </div>
                  <p className="text-xs leading-relaxed text-foreground">{msg.content}</p>
                </div>
              ) : (
                <div className="flex items-start gap-2">
                  <Bot className="mt-0.5 size-5 shrink-0 text-muted" />
                  <div className="min-w-0 flex-1 markdown-body text-xs">
                    <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeHighlight]}>
                      {msg.content}
                    </ReactMarkdown>
                    {loading && i === messages.length - 1 && !msg.content && (
                      <Loader2 className="size-3.5 animate-spin text-muted" />
                    )}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Input area — always at bottom */}
      <div className="border-t border-border px-3 py-2">
        {/* Agent picker */}
        {showAgentPicker && agents.length > 0 && (
          <div className="mb-2 rounded-lg border border-border bg-background p-1 shadow-lg">
            {agents.map(a => (
              <button key={a.id} onClick={() => pickAgent(a)} className="flex w-full items-center gap-2 rounded-md px-3 py-1.5 text-xs hover:bg-sidebar-hover">
                <span>{a.icon}</span>
                <span className="font-medium">{a.name}</span>
              </button>
            ))}
          </div>
        )}

        {selectedAgent && (
          <div className="mb-1.5">
            <span className="inline-flex items-center gap-1 rounded-full bg-accent-light px-2 py-0.5 text-xs text-accent">
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
          placeholder={messages.length === 0 ? "Write your question, Shift+Enter for newline" : "Reply..."}
          rows={messages.length === 0 ? 2 : 1}
          className="w-full resize-none bg-transparent text-sm outline-none placeholder:text-muted"
        />

        <div className="flex items-center justify-between pt-1.5">
          <div className="flex gap-1">
            <button onClick={() => setShowAgentPicker(!showAgentPicker)} className="rounded p-1 text-muted hover:bg-sidebar-hover" title="@ Pick agent">
              <span className="text-sm font-bold">@</span>
            </button>
          </div>
          <div className="flex gap-2">
            <button onClick={onClose} className="rounded-md px-3 py-1 text-xs text-muted hover:bg-sidebar-hover">Cancel</button>
            {loading ? (
              <button onClick={handleStop} className="rounded-md bg-red-500 px-3 py-1 text-xs text-white hover:bg-red-600">
                <Square className="inline size-2.5 mr-1" />Stop
              </button>
            ) : (
              <button onClick={handleSubmit} disabled={!input.trim()} className="rounded-md bg-accent px-3 py-1 text-xs text-white hover:bg-accent/90 disabled:opacity-40">
                Send
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
