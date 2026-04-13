"use client";

import { useEffect, useRef, useCallback } from "react";
import type { Task, CreateTaskParams } from "@/lib/taskTypes";

const MAX_CONCURRENT = 3;

interface TaskRunnerProps {
  tasks: Task[];
  updateTask: (id: string, patch: Partial<Task>) => void;
  onTaskComplete?: (task: Task) => void;
}

export function TaskRunner({ tasks, updateTask, onTaskComplete }: TaskRunnerProps) {
  const controllersRef = useRef<Map<string, AbortController>>(new Map());
  const runningRef = useRef<Set<string>>(new Set());

  const runTask = useCallback(
    async (task: Task) => {
      if (runningRef.current.has(task.id)) return;
      runningRef.current.add(task.id);

      const controller = new AbortController();
      controllersRef.current.set(task.id, controller);

      updateTask(task.id, { status: "running", startedAt: Date.now() });

      let sessionId = "";
      let result = "";
      let lastPersist = 0;

      try {
        const body: Record<string, unknown> = {
          prompt: task.prompt,
          agent_id: task.agentId || undefined,
          session_id: task.sessionId || undefined,
        };

        // For inline tasks, include file context from source
        if (task.source.kind === "inline") {
          // File content will be fetched and included in prompt by the caller
        }

        const res = await fetch("/api/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
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
                  updateTask(task.id, { sessionId });
                } else if (event.type === "text") {
                  result += event.content;
                  // Debounced persist every 2 seconds
                  const now = Date.now();
                  if (now - lastPersist > 2000) {
                    updateTask(task.id, { result });
                    lastPersist = now;
                  }
                } else if (event.type === "result_text" && !result) {
                  result = event.content;
                }
              } catch { /* skip */ }
            }
          }
        }

        updateTask(task.id, {
          status: "completed",
          result,
          sessionId,
          completedAt: Date.now(),
        });
        onTaskComplete?.({ ...task, status: "completed", result, sessionId });
      } catch (e: unknown) {
        if (e instanceof Error && e.name === "AbortError") {
          updateTask(task.id, { status: "interrupted", completedAt: Date.now() });
        } else {
          updateTask(task.id, {
            status: "error",
            error: e instanceof Error ? e.message : "Unknown error",
            result,
            completedAt: Date.now(),
          });
        }
      } finally {
        controllersRef.current.delete(task.id);
        runningRef.current.delete(task.id);
      }
    },
    [updateTask, onTaskComplete]
  );

  // Watch for pending tasks and run them
  useEffect(() => {
    const pending = tasks.filter((t) => t.status === "pending");
    const runningCount = runningRef.current.size;
    const slotsAvailable = MAX_CONCURRENT - runningCount;

    if (slotsAvailable > 0 && pending.length > 0) {
      const toRun = pending.slice(0, slotsAvailable);
      for (const task of toRun) {
        runTask(task);
      }
    }
  }, [tasks, runTask]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      controllersRef.current.forEach((ctrl) => ctrl.abort());
    };
  }, []);

  // Cancel a task
  const cancelTask = useCallback(
    (taskId: string) => {
      const ctrl = controllersRef.current.get(taskId);
      if (ctrl) ctrl.abort();
    },
    []
  );

  // Expose cancel via window for TasksPanel to use
  useEffect(() => {
    (window as unknown as Record<string, unknown>).__cancelTask = cancelTask;
    return () => {
      delete (window as unknown as Record<string, unknown>).__cancelTask;
    };
  }, [cancelTask]);

  return null; // headless component
}
