import { Type } from "@sinclair/typebox";
import type { ToolDeps } from "./index.ts";

interface BackendMemoryResult {
  id?: string;
  memory?: string;
  categories?: string[];
  created_at?: string;
  [key: string]: unknown;
}

export function createMemoryListTool(deps: ToolDeps) {
  const { backend, resolveUserId, getCurrentSessionId } = deps;

  return {
    name: "memory_list",
    label: "Memory List",
    description: "List all stored memories for a user or agent.",
    parameters: Type.Object({
      userId: Type.Optional(Type.String({ description: "User ID (default: configured)" })),
      agentId: Type.Optional(Type.String({ description: "Agent ID namespace" })),
      scope: Type.Optional(
        Type.Union([Type.Literal("session"), Type.Literal("long-term"), Type.Literal("all")], {
          description: 'Scope: "all" (default), "session", or "long-term"',
        }),
      ),
    }),

    async execute(_toolCallId: string, params: Record<string, unknown>) {
      const { userId, agentId, scope = "all" } = params as {
        userId?: string; agentId?: string; scope?: "session" | "long-term" | "all";
      };

      const start = Date.now();
      try {
        let memories: BackendMemoryResult[] = [];
        const uid = resolveUserId({ agentId, userId });
        const currentSessionId = getCurrentSessionId();

        if (scope === "session") {
          if (currentSessionId) memories = (await backend.listMemories({ userId: uid, runId: currentSessionId })) as BackendMemoryResult[];
        } else if (scope === "long-term") {
          memories = (await backend.listMemories({ userId: uid })) as BackendMemoryResult[];
        } else {
          const longTerm = (await backend.listMemories({ userId: uid })) as BackendMemoryResult[];
          let session: BackendMemoryResult[] = [];
          if (currentSessionId) session = (await backend.listMemories({ userId: uid, runId: currentSessionId })) as BackendMemoryResult[];
          const seen = new Set(longTerm.map((r) => r.id));
          memories = [...longTerm, ...session.filter((r) => !seen.has(r.id))];
        }

        deps.captureToolEvent("memory_list", { success: true, latency_ms: Date.now() - start, result_count: memories.length });

        if (!memories || memories.length === 0) {
          return { content: [{ type: "text", text: "No memories stored yet." }], details: { count: 0 } };
        }

        const text = memories.map((r, i) => `${i + 1}. ${r.memory ?? ""} (id: ${r.id ?? ""})`).join("\n");
        return {
          content: [{ type: "text", text: `${memories.length} memories:\n\n${text}` }],
          details: {
            count: memories.length,
            memories: memories.map((r) => ({ id: r.id, memory: r.memory, categories: r.categories, created_at: r.created_at })),
          },
        };
      } catch (err) {
        deps.captureToolEvent("memory_list", { success: false, latency_ms: Date.now() - start, error: String(err) });
        return { content: [{ type: "text", text: `Memory list failed: ${String(err)}` }], details: { error: String(err) } };
      }
    },
  };
}
