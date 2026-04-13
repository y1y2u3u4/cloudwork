"use client";

import { Loader2, CheckCircle, AlertCircle, XCircle, FileText, MessageSquare, Trash2, Clock } from "lucide-react";
import type { Task } from "@/lib/taskTypes";

function timeAgo(ts: number): string {
  const diff = Math.floor((Date.now() - ts) / 1000);
  if (diff < 60) return `${diff}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

function StatusIcon({ status }: { status: Task["status"] }) {
  switch (status) {
    case "pending":
      return <Clock className="size-4 text-muted" />;
    case "running":
      return <Loader2 className="size-4 animate-spin text-accent" />;
    case "completed":
      return <CheckCircle className="size-4 text-green-500" />;
    case "error":
      return <AlertCircle className="size-4 text-red-500" />;
    case "interrupted":
      return <XCircle className="size-4 text-amber-500" />;
  }
}

export function TasksPanel({
  tasks,
  onNavigate,
  onDelete,
  onClearCompleted,
}: {
  tasks: Task[];
  onNavigate: (task: Task) => void;
  onDelete: (taskId: string) => void;
  onClearCompleted: () => void;
}) {
  const running = tasks.filter((t) => t.status === "running" || t.status === "pending");
  const completed = tasks.filter((t) => t.status === "completed");
  const other = tasks.filter((t) => t.status === "error" || t.status === "interrupted");

  const hasCompleted = completed.length > 0 || other.length > 0;

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border px-4 py-2.5">
        <span className="text-sm font-semibold">Tasks</span>
        {hasCompleted && (
          <button
            onClick={onClearCompleted}
            className="text-xs text-muted hover:text-foreground"
          >
            Clear completed
          </button>
        )}
      </div>

      {/* Task list */}
      <div className="flex-1 overflow-auto">
        {tasks.length === 0 ? (
          <div className="flex h-full items-center justify-center">
            <div className="text-center">
              <Clock className="mx-auto mb-2 size-8 text-muted/30" />
              <p className="text-sm text-muted">No tasks yet</p>
              <p className="mt-1 text-xs text-muted/60">
                Tasks from chat and file interactions appear here
              </p>
            </div>
          </div>
        ) : (
          <div className="divide-y divide-border">
            {/* Running / Pending */}
            {running.length > 0 && (
              <div>
                <div className="bg-accent/5 px-4 py-1.5">
                  <span className="text-xs font-medium text-accent">
                    Active ({running.length})
                  </span>
                </div>
                {running.map((task) => (
                  <TaskRow
                    key={task.id}
                    task={task}
                    onNavigate={onNavigate}
                    onDelete={onDelete}
                  />
                ))}
              </div>
            )}

            {/* Completed */}
            {completed.length > 0 && (
              <div>
                <div className="bg-sidebar/50 px-4 py-1.5">
                  <span className="text-xs font-medium text-muted">
                    Completed ({completed.length})
                  </span>
                </div>
                {completed.map((task) => (
                  <TaskRow
                    key={task.id}
                    task={task}
                    onNavigate={onNavigate}
                    onDelete={onDelete}
                  />
                ))}
              </div>
            )}

            {/* Error / Interrupted */}
            {other.length > 0 && (
              <div>
                <div className="bg-sidebar/50 px-4 py-1.5">
                  <span className="text-xs font-medium text-muted">
                    Failed ({other.length})
                  </span>
                </div>
                {other.map((task) => (
                  <TaskRow
                    key={task.id}
                    task={task}
                    onNavigate={onNavigate}
                    onDelete={onDelete}
                  />
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function TaskRow({
  task,
  onNavigate,
  onDelete,
}: {
  task: Task;
  onNavigate: (task: Task) => void;
  onDelete: (taskId: string) => void;
}) {
  return (
    <div
      className="group flex cursor-pointer items-center gap-3 px-4 py-2.5 transition-colors hover:bg-sidebar-hover"
      onClick={() => onNavigate(task)}
    >
      <StatusIcon status={task.status} />

      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium">{task.title}</p>
        <div className="flex items-center gap-2 text-xs text-muted">
          {task.agentName && (
            <span className="rounded bg-accent-light px-1.5 py-0.5 text-accent">
              {task.agentName}
            </span>
          )}
          <span className="flex items-center gap-1">
            {task.source.kind === "inline" ? (
              <>
                <FileText className="size-3" />
                {task.source.filePath.split("/").pop()}
              </>
            ) : (
              <>
                <MessageSquare className="size-3" />
                Chat
              </>
            )}
          </span>
        </div>
      </div>

      <span className="shrink-0 text-xs text-muted">
        {timeAgo(task.completedAt || task.startedAt || task.createdAt)}
      </span>

      <button
        onClick={(e) => {
          e.stopPropagation();
          onDelete(task.id);
        }}
        className="hidden shrink-0 rounded p-1 text-muted hover:text-red-500 group-hover:block"
      >
        <Trash2 className="size-3.5" />
      </button>
    </div>
  );
}
