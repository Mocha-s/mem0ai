import { Type } from "@sinclair/typebox";
import type { SearchOptions as BackendSearchOptions } from "../backend/base.ts";
import type { ToolDeps } from "./index.ts";

interface BackendMemoryResult {
  id?: string;
  memory?: string;
  score?: number;
  categories?: string[];
  created_at?: string;
  updated_at?: string;
  [key: string]: unknown;
}

export function createMemorySearchTool(deps: ToolDeps) {
  const { cfg, backend, resolveUserId, buildSearchOptions, getCurrentSessionId } = deps;

  return {
    name: "memory_search",
    label: "Memory Search",
    description: "Search through long-term memories stored in Mem0.",
    parameters: Type.Object({
      query: Type.String({ description: "Search query" }),
      limit: Type.Optional(Type.Number({ description: `Max results (default: ${cfg.topK})` })),
      userId: Type.Optional(Type.String({ description: "User ID to scope search" })),
      agentId: Type.Optional(Type.String({ description: "Agent ID to search a specific agent's memories" })),
      scope: Type.Optional(
        Type.Union([Type.Literal("session"), Type.Literal("long-term"), Type.Literal("all")], {
          description: 'Scope: "all" (default), "session", or "long-term"',
        }),
      ),
      categories: Type.Optional(Type.Array(Type.String(), { description: "Filter by category" })),
      filters: Type.Optional(Type.Record(Type.String(), Type.Unknown(), { description: "Advanced filters" })),
    }),

    async execute(_toolCallId: string, params: Record<string, unknown>) {
      const {
        query, limit, userId, agentId, scope = "all",
        categories: filterCategories, filters: agentFilters,
      } = params as {
        query: string; limit?: number; userId?: string; agentId?: string;
        scope?: "session" | "long-term" | "all"; categories?: string[];
        filters?: Record<string, unknown>;
      };

      const start = Date.now();
      try {
        let results: BackendMemoryResult[] = [];
        const uid = resolveUserId({ agentId, userId });
        const currentSessionId = getCurrentSessionId();

        const toBackendOpts = (sessionKey?: string): BackendSearchOptions => {
          const provOpts = buildSearchOptions(uid, limit, undefined, sessionKey);
          const opts: BackendSearchOptions = {
            userId: provOpts.user_id,
            topK: provOpts.top_k,
            threshold: provOpts.threshold,
          };
          if (provOpts.run_id) opts.runId = provOpts.run_id;
          if (filterCategories?.length) opts.categories = filterCategories;
          if (agentFilters) opts.filters = agentFilters;
          return opts;
        };

        if (scope === "session") {
          if (currentSessionId) {
            results = (await backend.search(query, toBackendOpts(currentSessionId))) as BackendMemoryResult[];
          }
        } else if (scope === "long-term") {
          results = (await backend.search(query, toBackendOpts())) as BackendMemoryResult[];
        } else {
          const longTerm = (await backend.search(query, toBackendOpts())) as BackendMemoryResult[];
          let session: BackendMemoryResult[] = [];
          if (currentSessionId) {
            session = (await backend.search(query, toBackendOpts(currentSessionId))) as BackendMemoryResult[];
          }
          const seen = new Set(longTerm.map((r) => r.id));
          results = [...longTerm, ...session.filter((r) => !seen.has(r.id))];
        }

        deps.captureToolEvent("memory_search", { success: true, latency_ms: Date.now() - start, result_count: results.length });

        if (!results || results.length === 0) {
          return { content: [{ type: "text", text: "No relevant memories found." }], details: { count: 0 } };
        }

        const text = results.map((r, i) =>
          `${i + 1}. ${r.memory ?? ""} (score: ${((r.score ?? 0) * 100).toFixed(0)}%, id: ${r.id ?? ""})`
        ).join("\n");

        return {
          content: [{ type: "text", text: `Found ${results.length} memories:\n\n${text}` }],
          details: {
            count: results.length,
            memories: results.map((r) => ({ id: r.id, memory: r.memory, score: r.score, categories: r.categories, created_at: r.created_at })),
          },
        };
      } catch (err) {
        deps.captureToolEvent("memory_search", { success: false, latency_ms: Date.now() - start, error: String(err) });
        return { content: [{ type: "text", text: `Memory search failed: ${String(err)}` }], details: { error: String(err) } };
      }
    },
  };
}
