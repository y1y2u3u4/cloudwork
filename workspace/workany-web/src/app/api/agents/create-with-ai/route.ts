import { NextRequest } from "next/server";
import { spawn } from "child_process";
import os from "os";
import path from "path";

export async function POST(req: NextRequest) {
  const { description } = await req.json();

  if (!description) {
    return Response.json({ error: "description required" }, { status: 400 });
  }

  const prompt = `You are creating a Claude Code agent. Based on the user's description, generate a complete agent markdown file.

User's request: ${description}

Requirements:
1. Generate a .md file with YAML frontmatter (name, description, model)
2. The name should be lowercase, no spaces (use hyphens)
3. Include detailed system prompt with role, capabilities, workflow, tools to use, and style
4. If the agent needs MCP tools, specify which ones (e.g., mcp__cyberdata__execute_sql, mcp__playwright__browser_navigate)
5. If the agent needs skills, mention which ones (e.g., /web-access, /seo-mining)

Output ONLY the complete markdown file content, nothing else. Start with --- for frontmatter.`;

  const agentsDir = path.join(os.homedir(), ".claude", "agents");

  const encoder = new TextEncoder();
  const stream = new ReadableStream({
    start(controller) {
      const env = { ...process.env };
      delete env.CLAUDECODE;

      const proc = spawn("unbuffer", [
        "claude", "-p", prompt,
        "--model", "sonnet",
        "--output-format", "stream-json",
        "--verbose",
        "--dangerously-skip-permissions",
      ], { env, stdio: ["pipe", "pipe", "pipe"] });

      let lineBuf = "";
      let fullResult = "";

      proc.stdout.on("data", (chunk: Buffer) => {
        lineBuf += chunk.toString("utf-8");
        const lines = lineBuf.split("\n");
        lineBuf = lines.pop() || "";

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed || !trimmed.startsWith("{")) continue;
          try {
            const event = JSON.parse(trimmed);
            if (event.type === "assistant") {
              for (const block of event.message?.content || []) {
                if (block.type === "text") {
                  fullResult += block.text;
                  controller.enqueue(
                    encoder.encode(`data: ${JSON.stringify({ type: "text", content: block.text })}\n\n`)
                  );
                }
              }
            } else if (event.type === "result" && event.result) {
              if (!fullResult) fullResult = event.result;
            }
          } catch { /* skip */ }
        }
      });

      proc.stderr.on("data", (chunk: Buffer) => {
        console.error("[create-agent stderr]", chunk.toString());
      });

      proc.on("close", () => {
        // Parse the generated content and save
        const content = fullResult.replace(/^```markdown\n?/, "").replace(/\n?```$/, "").trim();
        const nameMatch = content.match(/^---\n[\s\S]*?name:\s*(\S+)[\s\S]*?---/);
        const agentName = nameMatch?.[1] || `agent-${Date.now().toString(36)}`;

        try {
          const filePath = path.join(agentsDir, `${agentName}.md`);
          require("fs").mkdirSync(agentsDir, { recursive: true });
          require("fs").writeFileSync(filePath, content, "utf-8");
          controller.enqueue(
            encoder.encode(`data: ${JSON.stringify({ type: "done", agentName, filePath })}\n\n`)
          );
        } catch (err: unknown) {
          const msg = err instanceof Error ? err.message : "Unknown error";
          controller.enqueue(
            encoder.encode(`data: ${JSON.stringify({ type: "error", message: msg })}\n\n`)
          );
        }
        controller.close();
      });

      proc.on("error", (err) => {
        controller.enqueue(
          encoder.encode(`data: ${JSON.stringify({ type: "error", message: err.message })}\n\n`)
        );
        controller.close();
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
