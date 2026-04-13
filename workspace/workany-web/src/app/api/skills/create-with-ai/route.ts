import { NextRequest } from "next/server";
import { spawn } from "child_process";
import os from "os";
import path from "path";
import fs from "fs";

export async function POST(req: NextRequest) {
  const { description } = await req.json();

  if (!description) {
    return Response.json({ error: "description required" }, { status: 400 });
  }

  const prompt = `You are creating a Claude Code slash command (skill). Based on the user's description, generate a complete markdown file that will be used as a reusable command.

User's request: ${description}

Requirements:
1. The file should start with a markdown heading (# Title)
2. Include clear instructions for what Claude should do when this command is invoked
3. If the skill involves structured output, include a detailed template/format
4. If the skill needs specific tools (MCP, web search, etc.), mention them
5. Include examples of how to use the skill
6. The command name should be lowercase with hyphens, suitable for a filename like "command-name.md"

Output format - first line must be a comment with the suggested filename:
<!-- filename: command-name -->
Then the full markdown content.

Output ONLY the file content, nothing else.`;

  const commandsDir = path.join(os.homedir(), ".claude", "commands");

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
        console.error("[create-skill stderr]", chunk.toString());
      });

      proc.on("close", () => {
        const content = fullResult.replace(/^```markdown\n?/, "").replace(/\n?```$/, "").trim();

        // Extract filename from comment
        const filenameMatch = content.match(/<!--\s*filename:\s*(\S+)\s*-->/);
        let skillName = filenameMatch?.[1]?.replace(".md", "") || `skill-${Date.now().toString(36)}`;
        const cleanContent = content.replace(/<!--\s*filename:.*?-->\n?/, "").trim();

        try {
          fs.mkdirSync(commandsDir, { recursive: true });
          const filePath = path.join(commandsDir, `${skillName}.md`);
          fs.writeFileSync(filePath, cleanContent, "utf-8");
          controller.enqueue(
            encoder.encode(`data: ${JSON.stringify({ type: "done", skillName, filePath })}\n\n`)
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
