import { Type } from "@sinclair/typebox";
import type { SearchOptions as BackendSearchOptions } from "../backend/base.ts";
import { isSubagentSession } from "../isolation.ts";
import type { ToolDeps } from "./index.ts";

interface BackendMemoryResult {
  id?: string;
  memory?: string;
  score?: number;
  [key: string]: unknown;
}

export function createMemoryDeleteTool(deps: ToolDeps) {
  const { api, backend, resolveUserId, getCurrentSessionId, buildSearchOptions } = deps;

  return {
    name: "memory_delete",
    label: "Memory Delete",
    description: "Delete memories. Provide memoryId, query to search-and-delete, or all:true for bulk deletion (requires confirm:true).",
    parameters: Type.Object({
      memoryId: Type.Optional(Type.String({ description: "Specific memory ID to delete" })),
      query: Type.Optional(Type.String({ description: "Search query to find and delete" })),
      agentId: Type.Optional(Type.String({ description: "Agent ID to scope deletion" })),
      all: Type.Optional(Type.Boolean({ description: "Delete ALL memories. Requires confirm: true." })),
      confirm: Type.Optional(Type.Boolean({ description: "Safety gate for bulk operations" })),
      userId: Type.Optional(Type.String({ description: "User ID scope" })),
    }),

    async execute(_toolCallId: string, params: Record<string, unknown>) {
      const { memoryId, query, agentId, all, confirm, userId } = params as {
        memoryId?: string; query?: string; agentId?: string;
        all?: boolean; confirm?: boolean; userId?: string;
      };

      const start = Date.now();
      try {
        if (isSubagentSession(getCurrentSessionId())) {
          return { content: [{ type: "text", text: "Memory deletion is not available in subagent sessions." }], details: { error: "subagent_blocked" } };
        }

        if (memoryId) {
          await backend.delete(memoryId);
          deps.captureToolEvent("memory_delete", { success: true, latency_ms: Date.now() - start, delete_mode: "single" });
          return { content: [{ type: "text", text: `Memory ${memoryId} deleted.` }], details: { action: "deleted", id: memoryId } };
        }

        if (query) {
          const uid = resolveUserId({ agentId, userId });
          const provOpts = buildSearchOptions(uid, 5);
          const searchOpts: BackendSearchOptions = {
            userId: provOpts.user_id,
            topK: provOpts.top_k,
            threshold: provOpts.threshold,
          };
          if (provOpts.run_id) searchOpts.runId = provOpts.run_id;
          const results = (await backend.search(query, searchOpts)) as BackendMemoryResult[];
          if (!results || results.length === 0) {
            return { content: [{ type: "text", text: "No matching memories found." }], details: { found: 0 } };
          }
          if (results.length === 1 || (results[0].score ?? 0) > 0.9) {
            await backend.delete(results[0].id as string);
            return { content: [{ type: "text", text: `Deleted: "${results[0].memory ?? ""}"` }], details: { action: "deleted", id: results[0].id } };
          }
          const list = results.map((r) => {
            const mem = r.memory ?? "";
            return `- [${r.id ?? ""}] ${mem.slice(0, 80)}${mem.length > 80 ? "..." : ""} (${((r.score ?? 0) * 100).toFixed(0)}%)`;
          }).join("\n");
          return {
            content: [{ type: "text", text: `Found ${results.length} candidates. Specify memoryId:\n${list}` }],
            details: { action: "candidates", candidates: results.map((r) => ({ id: r.id, memory: r.memory, score: r.score })) },
          };
        }

        if (all) {
          if (!confirm) {
            return { content: [{ type: "text", text: "Bulk deletion requires confirm: true." }], details: { error: "confirmation_required" } };
          }
          const uid = resolveUserId({ agentId, userId });
          await backend.delete(undefined, { all: true, userId: uid, ...(agentId && { agentId }) });
          deps.captureToolEvent("memory_delete", { success: true, latency_ms: Date.now() - start, delete_mode: "all" });
          api.logger.info(`openclaw-mem0: deleted all memories for user ${uid}`);
          return { content: [{ type: "text", text: `All memories deleted for user "${uid}".` }], details: { action: "deleted_all", user_id: uid } };
        }

        return { content: [{ type: "text", text: "Provide memoryId, query, or all:true." }], details: { error: "missing_param" } };
      } catch (err) {
        deps.captureToolEvent("memory_delete", { success: false, latency_ms: Date.now() - start, error: String(err) });
        return { content: [{ type: "text", text: `Memory delete failed: ${String(err)}` }], details: { error: String(err) } };
      }
    },
  };
}
