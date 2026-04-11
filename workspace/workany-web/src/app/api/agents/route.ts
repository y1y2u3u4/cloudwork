import { NextRequest } from "next/server";
import { getAllAgents, createAgent, updateAgent, deleteAgent } from "@/lib/agents";

export async function GET() {
  return Response.json({ agents: getAllAgents() });
}

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { action } = body;

    if (action === "create") {
      const agent = createAgent({
        name: body.name || "New Agent",
        icon: body.icon || "🤖",
        project_path: body.project_path || "",
        model: body.model || "sonnet",
        system_prompt: body.system_prompt || "",
        claude_md: body.claude_md || "",
      });
      return Response.json({ agent });
    }

    if (action === "update") {
      const agent = updateAgent(body.id, body.data);
      if (!agent) return Response.json({ error: "Not found" }, { status: 404 });
      return Response.json({ agent });
    }

    if (action === "delete") {
      const ok = deleteAgent(body.id);
      if (!ok) return Response.json({ error: "Not found" }, { status: 404 });
      return Response.json({ ok: true });
    }

    return Response.json({ error: "Unknown action" }, { status: 400 });
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : "Unknown error";
    return Response.json({ error: msg }, { status: 500 });
  }
}
