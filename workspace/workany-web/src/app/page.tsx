"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import {
  PanelLeft,
  Search,
  MessageSquare,
  FolderTree,
  X,
  ListTodo,
} from "lucide-react";
import { FileTree } from "@/components/FileTree";
import { MarkdownViewer } from "@/components/MarkdownViewer";
import { AgentPanel } from "@/components/AgentPanel";
import { ChatPanel, ContextQuote } from "@/components/ChatPanel";
import { SelectionActionBar } from "@/components/SelectionActionBar";
import { CommentSidebar, CommentThread } from "@/components/CommentSidebar";
import { TaskRunner } from "@/components/TaskRunner";
import { TaskToast } from "@/components/TaskToast";
import { TasksPanel } from "@/components/TasksPanel";
import { useTaskStore } from "@/lib/useTaskStore";
import type { Agent } from "@/lib/agents";
import type { Task } from "@/lib/taskTypes";

interface FileEntry {
  name: string;
  path: string;
  isDirectory: boolean;
  extension?: string;
  children?: FileEntry[];
}

type ViewMode = "file" | "chat" | "tasks";

export default function Home() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [entries, setEntries] = useState<FileEntry[]>([]);
  const [selectedPath, setSelectedPath] = useState("");
  const [fileContent, setFileContent] = useState("");
  const [agents, setAgents] = useState<Agent[]>([]);
  const [viewMode, setViewMode] = useState<ViewMode>("file");
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<
    { path: string; name: string; match: string; preview?: string }[]
  >([]);
  const [searching, setSearching] = useState(false);
  const [workspaceDirs, setWorkspaceDirs] = useState<string[]>([]);
  const [contextQuote, setContextQuote] = useState<ContextQuote | null>(null);
  const [comments, setComments] = useState<CommentThread[]>([]);
  const [navigateConvoId, setNavigateConvoId] = useState<string | null>(null);
  const previewRef = useRef<HTMLDivElement>(null);

  // Task store
  const taskStore = useTaskStore();

  // Load file tree
  const loadTree = useCallback(async () => {
    try {
      const res = await fetch("/api/workspace?action=tree&depth=1");
      const data = await res.json();
      setEntries(data.entries || []);
      const dirs = (data.entries || [])
        .filter((e: FileEntry) => e.isDirectory)
        .map((e: FileEntry) => e.path);
      setWorkspaceDirs(dirs);
    } catch (err) {
      console.error("Failed to load tree:", err);
    }
  }, []);

  // Load agents
  const loadAgents = useCallback(async () => {
    try {
      const res = await fetch("/api/agents");
      const data = await res.json();
      setAgents(data.agents || []);
    } catch (err) {
      console.error("Failed to load agents:", err);
    }
  }, []);

  useEffect(() => {
    loadTree();
    loadAgents();
  }, [loadTree, loadAgents]);

  // Handle file selection
  const handleSelect = async (path: string, isDir: boolean) => {
    setSelectedPath(path);
    if (!isDir) {
      setViewMode("file");
      try {
        const res = await fetch(
          `/api/workspace?action=read&path=${encodeURIComponent(path)}`
        );
        const data = await res.json();
        setFileContent(data.error ? `Error: ${data.error}` : data.content || "");
      } catch {
        setFileContent("Failed to load file");
      }
    }
  };

  // Open file from chat (FileRefCard click)
  const handleOpenFile = (path: string) => {
    handleSelect(path, false);
  };

  // Selection action from file preview → add new comment thread
  const handleSelectionAction = (context: {
    selectedText: string;
    filePath: string;
    position: { top: number; left: number };
  }) => {
    const newThread: CommentThread = {
      id: Date.now().toString(36) + Math.random().toString(36).slice(2, 6),
      selectedText: context.selectedText,
      filePath: context.filePath,
      messages: [],
      sessionId: "",
      status: "draft",
      createdAt: Date.now(),
    };
    setComments(prev => [newThread, ...prev]);
  };

  const handleUpdateThread = useCallback((id: string, patch: Partial<CommentThread>) => {
    setComments(prev => prev.map(t => t.id === id ? { ...t, ...patch } : t));
  }, []);

  const handleRemoveThread = useCallback((id: string) => {
    setComments(prev => prev.filter(t => t.id !== id));
    // Remove associated highlight
    document.querySelectorAll("mark.workany-highlight").forEach(el => {
      const parent = el.parentNode;
      if (parent) { parent.replaceChild(document.createTextNode(el.textContent || ""), el); parent.normalize(); }
    });
  }, []);

  const handleClearQuote = () => setContextQuote(null);

  // Navigate to a task's source
  const handleNavigateToTask = useCallback((task: Task) => {
    if (task.source.kind === "chat") {
      setNavigateConvoId(task.source.conversationId);
      setViewMode("chat");
      // Clear after navigation
      setTimeout(() => setNavigateConvoId(null), 500);
    } else if (task.source.kind === "inline") {
      handleSelect(task.source.filePath, false);
      // Add the task result as a comment thread if not already there
      setComments(prev => {
        if (prev.some(t => t.taskId === task.id)) return prev;
        return [{
          id: task.id,
          selectedText: task.source.selectedText,
          filePath: task.source.filePath,
          messages: [
            { role: "user" as const, content: task.title },
            { role: "assistant" as const, content: task.result },
          ],
          sessionId: task.sessionId,
          taskId: task.id,
          agentId: task.agentId,
          agentName: task.agentName,
          status: "done" as const,
          createdAt: task.createdAt,
        }, ...prev];
      });
    }
  }, []);

  // Task complete notification → navigate
  const handleTaskComplete = useCallback((task: Task) => {
    // Toast will handle notification via recentlyCompleted
  }, []);

  // Search
  const handleSearch = async (query: string) => {
    setSearchQuery(query);
    if (query.length < 2) {
      setSearchResults([]);
      return;
    }
    setSearching(true);
    try {
      const res = await fetch(
        `/api/workspace?action=search&q=${encodeURIComponent(query)}`
      );
      const data = await res.json();
      setSearchResults(data.results || []);
    } catch {
      setSearchResults([]);
    }
    setSearching(false);
  };

  const isMarkdown =
    selectedPath.endsWith(".md") || selectedPath.endsWith(".mdx");

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      {/* TaskRunner (headless) */}
      <TaskRunner
        tasks={taskStore.tasks}
        updateTask={taskStore.updateTask}
        onTaskComplete={handleTaskComplete}
      />

      {/* Toast notifications */}
      <TaskToast
        tasks={taskStore.recentlyCompleted}
        onView={(task) => {
          taskStore.markTaskSeen(task.id);
          handleNavigateToTask(task);
        }}
        onDismiss={(id) => taskStore.markTaskSeen(id)}
      />

      {/* Sidebar */}
      {sidebarOpen && (
        <aside className="flex h-full w-64 shrink-0 flex-col border-r border-border bg-sidebar">
          {/* Sidebar header */}
          <div className="flex items-center justify-between px-3 py-2.5">
            <span className="text-sm font-semibold tracking-tight">
              WorkAny
            </span>
            <button
              onClick={() => setSidebarOpen(false)}
              className="rounded p-1 text-muted hover:bg-sidebar-hover"
            >
              <PanelLeft className="size-4" />
            </button>
          </div>

          {/* View mode toggle — 3 tabs */}
          <div className="flex gap-1 px-2 pb-2">
            <button
              onClick={() => setViewMode("file")}
              className={`flex flex-1 items-center justify-center gap-1.5 rounded-md py-1.5 text-xs font-medium transition-colors ${
                viewMode === "file"
                  ? "bg-accent-light text-accent"
                  : "text-muted hover:bg-sidebar-hover"
              }`}
            >
              <FolderTree className="size-3.5" />
              Files
            </button>
            <button
              onClick={() => setViewMode("chat")}
              className={`flex flex-1 items-center justify-center gap-1.5 rounded-md py-1.5 text-xs font-medium transition-colors ${
                viewMode === "chat"
                  ? "bg-accent-light text-accent"
                  : "text-muted hover:bg-sidebar-hover"
              }`}
            >
              <MessageSquare className="size-3.5" />
              Chat
            </button>
            <button
              onClick={() => setViewMode("tasks")}
              className={`relative flex flex-1 items-center justify-center gap-1.5 rounded-md py-1.5 text-xs font-medium transition-colors ${
                viewMode === "tasks"
                  ? "bg-accent-light text-accent"
                  : "text-muted hover:bg-sidebar-hover"
              }`}
            >
              <ListTodo className="size-3.5" />
              Tasks
              {taskStore.runningCount > 0 && (
                <span className="absolute -right-0.5 -top-0.5 flex size-4 items-center justify-center rounded-full bg-accent text-[10px] text-white">
                  {taskStore.runningCount}
                </span>
              )}
            </button>
          </div>

          {/* Search */}
          <div className="px-2 pb-2">
            <div className="flex items-center gap-1.5 rounded-md border border-border bg-background px-2 py-1">
              <Search className="size-3.5 text-muted" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => handleSearch(e.target.value)}
                placeholder="Search files..."
                className="flex-1 bg-transparent text-xs outline-none placeholder:text-muted"
              />
              {searchQuery && (
                <button
                  onClick={() => {
                    setSearchQuery("");
                    setSearchResults([]);
                  }}
                  className="text-muted hover:text-foreground"
                >
                  <X className="size-3" />
                </button>
              )}
            </div>
          </div>

          {/* Search results or file tree */}
          <div className="flex-1 overflow-auto px-1">
            {searchQuery.length >= 2 ? (
              <div className="space-y-0.5 py-1">
                {searching && (
                  <p className="px-2 py-2 text-xs text-muted">Searching...</p>
                )}
                {searchResults.map((r, i) => (
                  <button
                    key={i}
                    onClick={() => handleSelect(r.path, false)}
                    className="flex w-full flex-col rounded-md px-2 py-1.5 text-left hover:bg-sidebar-hover"
                  >
                    <span className="truncate text-xs font-medium">
                      {r.name}
                    </span>
                    <span className="truncate text-xs text-muted">
                      {r.path}
                    </span>
                    {r.preview && (
                      <span className="mt-0.5 truncate text-xs text-muted/70">
                        {r.preview}
                      </span>
                    )}
                  </button>
                ))}
                {!searching && searchResults.length === 0 && (
                  <p className="px-2 py-4 text-center text-xs text-muted">
                    No results
                  </p>
                )}
              </div>
            ) : (
              <FileTree
                entries={entries}
                selectedPath={selectedPath}
                onSelect={handleSelect}
              />
            )}
          </div>

          {/* Agent section */}
          <div className="shrink-0 border-t border-border px-1 py-2">
            <AgentPanel
              agents={agents}
              onAgentsChange={loadAgents}
              workspaceDirs={workspaceDirs}
            />
          </div>
        </aside>
      )}

      {/* Main content */}
      <main className="flex min-w-0 flex-1 flex-col">
        {/* Top bar when sidebar closed */}
        {!sidebarOpen && (
          <div className="flex shrink-0 items-center gap-2 border-b border-border px-3 py-2">
            <button
              onClick={() => setSidebarOpen(true)}
              className="rounded p-1 text-muted hover:bg-sidebar-hover"
            >
              <PanelLeft className="size-4" />
            </button>
            <span className="text-sm font-semibold">WorkAny</span>
          </div>
        )}

        {viewMode === "file" ? (
          selectedPath && !entries.find((e) => e.path === selectedPath)?.isDirectory ? (
            <div className="flex h-full">
              {/* File preview — left side */}
              <div className="relative flex min-w-0 flex-1 flex-col" ref={previewRef}>
                <SelectionActionBar
                  containerRef={previewRef}
                  filePath={selectedPath}
                  onAction={handleSelectionAction}
                />
                {isMarkdown ? (
                  <MarkdownViewer content={fileContent} filePath={selectedPath} onSave={(newContent) => setFileContent(newContent)} />
                ) : (
                  <>
                    <div className="flex shrink-0 items-center gap-2 border-b border-border px-4 py-2.5">
                      <span className="text-sm font-medium">
                        {selectedPath.split("/").pop()}
                      </span>
                      <span className="text-xs text-muted">{selectedPath}</span>
                    </div>
                    <div className="flex-1 overflow-auto px-6 py-4">
                      <pre className="whitespace-pre-wrap font-mono text-sm leading-relaxed select-text">
                        {fileContent}
                      </pre>
                    </div>
                  </>
                )}
              </div>
              {/* Comment sidebar — right side, Feishu-style multi-thread */}
              {comments.length > 0 && (
                <CommentSidebar
                  threads={comments}
                  fileContent={fileContent}
                  agents={agents}
                  onUpdateThread={handleUpdateThread}
                  onRemoveThread={handleRemoveThread}
                  createTask={taskStore.createTask}
                  updateTask={taskStore.updateTask}
                  onFileChanged={(path) => {
                    if (path === selectedPath) {
                      fetch(`/api/workspace?action=read&path=${encodeURIComponent(path)}`)
                        .then(r => r.json())
                        .then(data => { if (!data.error) setFileContent(data.content || ""); });
                    }
                  }}
                />
              )}
            </div>
          ) : (
            <div className="flex h-full items-center justify-center">
              <div className="text-center">
                <FolderTree className="mx-auto mb-2 size-10 text-muted/30" />
                <p className="text-sm text-muted">
                  Select a file to view
                </p>
              </div>
            </div>
          )
        ) : viewMode === "chat" ? (
          <ChatPanel
            agents={agents}
            activeFile={selectedPath && !entries.find((e) => e.path === selectedPath)?.isDirectory ? { path: selectedPath, content: fileContent } : undefined}
            contextQuote={contextQuote}
            onClearQuote={handleClearQuote}
            onOpenFile={handleOpenFile}
            createTask={taskStore.createTask}
            updateTask={taskStore.updateTask}
            navigateToConversationId={navigateConvoId}
            onFileChanged={(path) => {
              if (path === selectedPath) {
                fetch(`/api/workspace?action=read&path=${encodeURIComponent(path)}`)
                  .then(r => r.json())
                  .then(data => { if (!data.error) setFileContent(data.content || ""); });
              }
            }}
          />
        ) : (
          <TasksPanel
            tasks={taskStore.tasks}
            onNavigate={handleNavigateToTask}
            onDelete={taskStore.deleteTask}
            onClearCompleted={taskStore.clearCompleted}
          />
        )}
      </main>
    </div>
  );
}
