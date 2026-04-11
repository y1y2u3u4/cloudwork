import { NextRequest } from "next/server";
import path from "path";
import fs from "fs";
import { scanDir, readFile, writeFile, getWorkspaceRoot } from "@/lib/workspace";

const TEXT_EXTS = new Set([
  ".md", ".txt", ".py", ".js", ".ts", ".tsx", ".jsx", ".json",
  ".yaml", ".yml", ".toml", ".sh", ".css", ".html", ".sql",
]);

export async function GET(req: NextRequest) {
  const { searchParams } = req.nextUrl;
  const action = searchParams.get("action") || "tree";

  try {
    if (action === "tree") {
      const p = searchParams.get("path") || "";
      const depth = parseInt(searchParams.get("depth") || "1", 10);
      const root = getWorkspaceRoot();
      const target = p ? path.resolve(root, p) : root;
      if (!target.startsWith(root)) {
        return Response.json({ error: "Access denied" }, { status: 403 });
      }
      const entries = scanDir(target, depth);
      return Response.json({ entries, path: p });
    }

    if (action === "read") {
      const p = searchParams.get("path");
      if (!p) return Response.json({ error: "path required" }, { status: 400 });
      const { content, size } = readFile(p);
      return Response.json({ path: p, content, size });
    }

    if (action === "search") {
      const q = searchParams.get("q") || "";
      if (q.length < 2) return Response.json({ results: [] });

      const root = getWorkspaceRoot();
      const results: { path: string; name: string; match: string; preview?: string }[] = [];
      const IGNORED = new Set(["node_modules", ".git", ".next", "__pycache__", ".venv", "dist", ".cache"]);
      const MAX = 30;

      function walk(dir: string) {
        if (results.length >= MAX) return;
        let items: string[];
        try { items = fs.readdirSync(dir); } catch { return; }
        for (const item of items) {
          if (results.length >= MAX) return;
          if (item.startsWith(".") || IGNORED.has(item)) continue;
          const full = path.join(dir, item);
          let stat: fs.Stats;
          try { stat = fs.statSync(full); } catch { continue; }
          const rel = path.relative(root, full);

          if (stat.isDirectory()) {
            if (item.toLowerCase().includes(q.toLowerCase())) {
              results.push({ path: rel, name: item, match: "filename" });
            }
            walk(full);
          } else {
            if (item.toLowerCase().includes(q.toLowerCase())) {
              results.push({ path: rel, name: item, match: "filename" });
              continue;
            }
            const ext = path.extname(item).toLowerCase();
            if (TEXT_EXTS.has(ext) && stat.size < 512 * 1024) {
              try {
                const content = fs.readFileSync(full, "utf-8");
                if (content.toLowerCase().includes(q.toLowerCase())) {
                  const lines = content.split("\n");
                  const line = lines.find((l) => l.toLowerCase().includes(q.toLowerCase()));
                  results.push({
                    path: rel,
                    name: item,
                    match: "content",
                    preview: line?.trim().slice(0, 150),
                  });
                }
              } catch { /* skip */ }
            }
          }
        }
      }

      walk(root);
      return Response.json({ results, query: q });
    }

    return Response.json({ error: "Unknown action" }, { status: 400 });
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : "Unknown error";
    return Response.json({ error: msg }, { status: 500 });
  }
}

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { action, path: filePath, content } = body;

    if (action === "write") {
      if (!filePath) return Response.json({ error: "path required" }, { status: 400 });
      writeFile(filePath, content || "");
      return Response.json({ ok: true, path: filePath });
    }

    return Response.json({ error: "Unknown action" }, { status: 400 });
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : "Unknown error";
    return Response.json({ error: msg }, { status: 500 });
  }
}
