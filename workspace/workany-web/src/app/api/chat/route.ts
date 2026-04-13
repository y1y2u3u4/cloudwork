import { NextRequest } from "next/server";
import { spawn } from "child_process";
import path from "path";
import { getAgent } from "@/lib/agents";
import { getWorkspaceRoot } from "@/lib/workspace";

export async function POST(req: NextRequest) {
  const body = await req.json();
  const { prompt, agent_id, file_context, session_id } = body;

  if (!prompt) {
    return Response.json({ error: "prompt required" }, { status: 400 });
  }

  // Resolve agent config
  let cwd = getWorkspaceRoot();
  let model = "sonnet";
  let agentName = ""; // Claude Code --agent name

  if (agent_id) {
    const agent = getAgent(agent_id);
    if (agent) {
      if (agent.project_path) {
        cwd = path.resolve(getWorkspaceRoot(), agent.project_path);
      }
      model = agent.model || "sonnet";
      agentName = agent.source === "claude-code" ? agent.name : "";
    }
  }

  // Build the full prompt with file context
  let fullPrompt = prompt;
  if (file_context?.path && file_context?.content) {
    const absPath = path.resolve(getWorkspaceRoot(), file_context.path);
    fullPrompt = `I have a file open at: ${absPath}\n\nFile content:\n\`\`\`\n${file_context.content}\n\`\`\`\n\nUser request: ${prompt}\n\nIf the user asks you to modify this file, use the Edit or Write tool to update it at the path above.`;
  }

  // Build claude CLI command
  const args: string[] = [];

  if (session_id) {
    // Resume existing conversation
    args.push("--resume", session_id, "-p", fullPrompt);
  } else {
    // New conversation
    args.push("-p", fullPrompt);
  }

  args.push(
    "--model", model,
    "--output-format", "stream-json",
    "--verbose",
    "--dangerously-skip-permissions",
  );

  // Use Claude Code's native --agent for registered agents
  if (agentName && !session_id) {
    args.push("--agent", agentName);
  }

  // Stream SSE response
  const encoder = new TextEncoder();
  const stream = new ReadableStream({
    start(controller) {
      const env = { ...process.env };
      delete env.CLAUDECODE;
      const proc = spawn("unbuffer", ["claude", ...args], {
        cwd,
        env,
        stdio: ["pipe", "pipe", "pipe"],
      });

      let sessionId = "";
      let lineBuf = "";
      let closed = false;

      const safeEnqueue = (data: Uint8Array) => {
        if (!closed) controller.enqueue(data);
      };
      const safeClose = () => {
        if (!closed) { closed = true; controller.close(); }
      };

      proc.stdout.on("data", (chunk: Buffer) => {
        lineBuf += chunk.toString("utf-8");
        const lines = lineBuf.split("\n");
        // Keep the last (potentially incomplete) line in buffer
        lineBuf = lines.pop() || "";

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed || !trimmed.startsWith("{")) continue;

          try {
            const event = JSON.parse(trimmed);
            const type = event.type;

            if (type === "system") {
              sessionId = event.session_id || sessionId;
              if (event.session_id) {
                safeEnqueue(
                  encoder.encode(`data: ${JSON.stringify({ type: "session", sessionId: event.session_id })}\n\n`)
                );
              }
            } else if (type === "assistant") {
              const content = event.message?.content || [];
              for (const block of content) {
                if (block.type === "text") {
                  safeEnqueue(
                    encoder.encode(`data: ${JSON.stringify({ type: "text", content: block.text })}\n\n`)
                  );
                } else if (block.type === "tool_use") {
                  safeEnqueue(
                    encoder.encode(`data: ${JSON.stringify({ type: "tool_use", name: block.name, input: block.input })}\n\n`)
                  );
                }
              }
            } else if (type === "result") {
              // Emit the final result text so frontend can display it
              if (event.result) {
                safeEnqueue(
                  encoder.encode(`data: ${JSON.stringify({ type: "result_text", content: event.result })}\n\n`)
                );
              }
              safeEnqueue(
                encoder.encode(`data: ${JSON.stringify({ type: "done", sessionId })}\n\n`)
              );
            }
          } catch {
            // skip malformed JSON
          }
        }
      });

      proc.stderr.on("data", (chunk: Buffer) => {
        console.error("[claude stderr]", chunk.toString());
      });

      proc.on("close", () => {
        // Flush remaining buffer
        if (lineBuf.trim()) {
          try {
            const event = JSON.parse(lineBuf.trim());
            if (event.type === "result") {
              if (event.result) {
                safeEnqueue(
                  encoder.encode(`data: ${JSON.stringify({ type: "result_text", content: event.result })}\n\n`)
                );
              }
            } else if (event.type === "assistant") {
              const content = event.message?.content || [];
              for (const block of content) {
                if (block.type === "text") {
                  safeEnqueue(
                    encoder.encode(`data: ${JSON.stringify({ type: "text", content: block.text })}\n\n`)
                  );
                }
              }
            }
          } catch { /* skip */ }
        }
        safeEnqueue(
          encoder.encode(`data: ${JSON.stringify({ type: "done", sessionId })}\n\n`)
        );
        safeClose();
      });

      proc.on("error", (err) => {
        safeEnqueue(
          encoder.encode(`data: ${JSON.stringify({ type: "error", message: err.message })}\n\n`)
        );
        safeClose();
      });
    },
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      Connection: "keep-alive",
    },
  });
}
