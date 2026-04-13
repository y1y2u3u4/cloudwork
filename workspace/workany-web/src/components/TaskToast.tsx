"use client";

import { useEffect, useState } from "react";
import { CheckCircle, X, ArrowRight } from "lucide-react";
import type { Task } from "@/lib/taskTypes";

interface TaskToastProps {
  tasks: Task[];
  onView: (task: Task) => void;
  onDismiss: (taskId: string) => void;
}

interface ToastItem {
  task: Task;
  expiresAt: number;
}

export function TaskToast({ tasks, onView, onDismiss }: TaskToastProps) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  // Add new completed tasks as toasts
  useEffect(() => {
    for (const task of tasks) {
      setToasts((prev) => {
        if (prev.some((t) => t.task.id === task.id)) return prev;
        return [...prev, { task, expiresAt: Date.now() + 8000 }];
      });
    }
  }, [tasks]);

  // Auto-dismiss expired toasts
  useEffect(() => {
    if (toasts.length === 0) return;
    const timer = setInterval(() => {
      const now = Date.now();
      setToasts((prev) => {
        const filtered = prev.filter((t) => t.expiresAt > now);
        if (filtered.length !== prev.length) {
          for (const removed of prev) {
            if (!filtered.includes(removed)) {
              onDismiss(removed.task.id);
            }
          }
        }
        return filtered;
      });
    }, 1000);
    return () => clearInterval(timer);
  }, [toasts.length, onDismiss]);

  if (toasts.length === 0) return null;

  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2">
      {toasts.map(({ task }) => (
        <div
          key={task.id}
          className="flex items-center gap-2.5 rounded-lg border border-green-200 bg-green-50 px-3 py-2.5 shadow-lg animate-in slide-in-from-right"
        >
          <CheckCircle className="size-4 shrink-0 text-green-600" />
          <div className="min-w-0 flex-1">
            <p className="truncate text-xs font-medium text-green-800">
              Task completed
            </p>
            <p className="truncate text-xs text-green-600">
              {task.title}
            </p>
          </div>
          <button
            onClick={() => {
              onView(task);
              setToasts((prev) => prev.filter((t) => t.task.id !== task.id));
            }}
            className="flex items-center gap-1 rounded-md bg-green-600 px-2 py-1 text-xs text-white hover:bg-green-700"
          >
            View <ArrowRight className="size-3" />
          </button>
          <button
            onClick={() => {
              onDismiss(task.id);
              setToasts((prev) => prev.filter((t) => t.task.id !== task.id));
            }}
            className="text-green-400 hover:text-green-600"
          >
            <X className="size-3.5" />
          </button>
        </div>
      ))}
    </div>
  );
}
