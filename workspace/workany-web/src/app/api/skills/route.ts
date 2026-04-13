import { NextRequest } from "next/server";
import fs from "fs";
import path from "path";
import os from "os";

function parseFrontmatter(content: string): {
  meta: Record<string, string>;
  body: string;
} {
  const match = content.match(/^---\n([\s\S]*?)\n---\n?([\s\S]*)$/);
  if (!match) return { meta: {}, body: content };
  const meta: Record<string, string> = {};
  for (const line of match[1].split("\n")) {
    const idx = line.indexOf(":");
    if (idx > 0) {
      meta[line.slice(0, idx).trim()] = line.slice(idx + 1).trim();
    }
  }
  return { meta, body: match[2].trim() };
}

const COMMANDS_DIR = path.join(os.homedir(), ".claude", "commands");

function scanSkills() {
  const skills: { id: string; name: string; description: string; source: string; filePath: string; content: string }[] = [];

  // Scan ~/.claude/commands/ for user skills
  if (fs.existsSync(COMMANDS_DIR)) {
    for (const file of fs.readdirSync(COMMANDS_DIR).filter(f => f.endsWith(".md"))) {
      try {
        const fullContent = fs.readFileSync(path.join(COMMANDS_DIR, file), "utf-8");
        const { meta, body } = parseFrontmatter(fullContent);
        const name = meta.name || file.replace(".md", "");
        skills.push({
          id: `cmd:${name}`,
          name,
          description: meta.description || body.split("\n")[0].replace(/^#\s*/, "").slice(0, 100),
          source: "commands",
          filePath: path.join(COMMANDS_DIR, file),
          content: body,
        });
      } catch { /* skip */ }
    }
  }

  // Scan project-level .claude/commands/
  const projectDirs = [
    path.resolve(process.cwd(), "..", ".claude", "commands"),
    path.resolve(process.cwd(), ".claude", "commands"),
  ];
  for (const dir of projectDirs) {
    if (!fs.existsSync(dir)) continue;
    for (const file of fs.readdirSync(dir).filter(f => f.endsWith(".md"))) {
      const name = file.replace(".md", "");
      if (skills.some(s => s.name === name)) continue;
      try {
        const fullContent = fs.readFileSync(path.join(dir, file), "utf-8");
        const { meta, body } = parseFrontmatter(fullContent);
        skills.push({
          id: `proj:${name}`,
          name: meta.name || name,
          description: meta.description || body.split("\n")[0].replace(/^#\s*/, "").slice(0, 100),
          source: "project",
          filePath: path.join(dir, file),
          content: body,
        });
      } catch { /* skip */ }
    }
  }

  return skills;
}

export async function GET() {
  return Response.json({ skills: scanSkills() });
}

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { action } = body;

    if (action === "create") {
      const { name, description, content } = body;
      if (!name) return Response.json({ error: "name required" }, { status: 400 });

      fs.mkdirSync(COMMANDS_DIR, { recursive: true });
      const fileName = name.toLowerCase().replace(/\s+/g, "-").replace(/[^a-z0-9-]/g, "");
      const fileContent = `# ${name}\n\n${content || description || ""}`;
      fs.writeFileSync(path.join(COMMANDS_DIR, `${fileName}.md`), fileContent, "utf-8");

      return Response.json({ skill: { name: fileName, description: description || name } });
    }

    if (action === "delete") {
      const { name } = body;
      const filePath = path.join(COMMANDS_DIR, `${name}.md`);
      if (fs.existsSync(filePath)) {
        fs.unlinkSync(filePath);
        return Response.json({ ok: true });
      }
      // Try project-level
      const projectDirs = [
        path.resolve(process.cwd(), "..", ".claude", "commands"),
        path.resolve(process.cwd(), ".claude", "commands"),
      ];
      for (const dir of projectDirs) {
        const fp = path.join(dir, `${name}.md`);
        if (fs.existsSync(fp)) {
          fs.unlinkSync(fp);
          return Response.json({ ok: true });
        }
      }
      return Response.json({ error: "Not found" }, { status: 404 });
    }

    return Response.json({ error: "Unknown action" }, { status: 400 });
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : "Unknown error";
    return Response.json({ error: msg }, { status: 500 });
  }
}
