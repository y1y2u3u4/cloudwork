"use client";

import { useState, useEffect, useCallback } from "react";
import {
  PanelLeft,
  Search,
  MessageSquare,
  FolderTree,
  X,
} from "lucide-react";
import { FileTree } from "@/components/FileTree";
import { MarkdownViewer } from "@/components/MarkdownViewer";
import { AgentPanel } from "@/components/AgentPanel";
import { ChatPanel } from "@/components/ChatPanel";
import type { Agent } from "@/lib/agents";

interface FileEntry {
  name: string;
  path: string;
  isDirectory: boolean;
  extension?: string;
  children?: FileEntry[];
}

type ViewMode = "file" | "chat";

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

  // Load file tree
  const loadTree = useCallback(async () => {
    try {
      const res = await fetch("/api/workspace?action=tree&depth=1");
      const data = await res.json();
      setEntries(data.entries || []);
      // Extract top-level directories for agent project picker
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
        if (data.error) {
          setFileContent(`Error: ${data.error}`);
        } else {
          setFileContent(data.content || "");
        }
      } catch {
        setFileContent("Failed to load file");
      }
    }
  };

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

          {/* View mode toggle */}
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
            isMarkdown ? (
              <MarkdownViewer content={fileContent} filePath={selectedPath} onSave={(newContent) => setFileContent(newContent)} />
            ) : (
              <div className="flex h-full flex-col">
                <div className="flex shrink-0 items-center gap-2 border-b border-border px-4 py-2.5">
                  <span className="text-sm font-medium">
                    {selectedPath.split("/").pop()}
                  </span>
                  <span className="text-xs text-muted">{selectedPath}</span>
                </div>
                <div className="flex-1 overflow-auto px-6 py-4">
                  <pre className="whitespace-pre-wrap font-mono text-sm leading-relaxed">
                    {fileContent}
                  </pre>
                </div>
              </div>
            )
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
        ) : (
          <ChatPanel
            agents={agents}
            activeFile={selectedPath && !entries.find((e) => e.path === selectedPath)?.isDirectory ? { path: selectedPath, content: fileContent } : undefined}
            onFileChanged={(path) => {
              // Reload file content if the changed file is the one we're viewing
              if (path === selectedPath) {
                fetch(`/api/workspace?action=read&path=${encodeURIComponent(path)}`)
                  .then(r => r.json())
                  .then(data => { if (!data.error) setFileContent(data.content || ""); });
              }
            }}
          />
        )}
      </main>
    </div>
  );
}
