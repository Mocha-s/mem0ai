import { Type } from "@sinclair/typebox";
import type { AddOptions as BackendAddOptions } from "../backend/base.ts";
import { isSubagentSession } from "../isolation.ts";
import { isNoiseMessage, stripNoiseFromContent } from "../filtering.ts";
import type { ToolDeps } from "./index.ts";

interface BackendAddResult {
  results?: Array<{ id?: string; memory?: string; event?: string }>;
  [key: string]: unknown;
}

export function createMemoryAddTool(deps: ToolDeps) {
  const { api, backend, cfg, resolveUserId, getCurrentSessionId, buildAddOptions, skillsActive } = deps;

  return {
    name: "memory_add",
    label: "Memory Add",
    description: "Save important information in long-term memory via Mem0. Use for preferences, facts, decisions, and anything worth remembering.",
    parameters: Type.Object({
      text: Type.Optional(Type.String({ description: "Single fact to remember" })),
      facts: Type.Optional(Type.Array(Type.String(), { description: "Array of facts to store. ALL must share the same category." })),
      category: Type.Optional(Type.String({ description: 'Category: "identity", "preference", "decision", "rule", "project", "configuration", "technical", "relationship"' })),
      importance: Type.Optional(Type.Number({ description: "Importance (0.0-1.0), omit for category default" })),
      userId: Type.Optional(Type.String({ description: "User ID to scope this memory" })),
      agentId: Type.Optional(Type.String({ description: "Agent ID namespace" })),
      metadata: Type.Optional(Type.Record(Type.String(), Type.Unknown(), { description: "Additional metadata" })),
      longTerm: Type.Optional(Type.Boolean({ description: "Long-term (default: true). Set false for session-scoped." })),
    }),

    async execute(_toolCallId: string, params: Record<string, unknown>) {
      const p = params as {
        text?: string; facts?: string[]; category?: string; importance?: number;
        userId?: string; agentId?: string; metadata?: Record<string, unknown>; longTerm?: boolean;
      };

      const rawFacts: string[] = p.facts?.length ? p.facts : (p.text ? [p.text] : []);
      if (rawFacts.length === 0) {
        return { content: [{ type: "text", text: "No facts provided. Pass 'text' or 'facts' array." }], details: { error: "missing_facts" } };
      }

      const allFacts = rawFacts
        .map((f) => stripNoiseFromContent(f))
        .filter((f) => f.length > 0 && !isNoiseMessage(f));

      if (allFacts.length === 0) {
        return { content: [{ type: "text", text: "All provided facts were filtered as noise. Nothing stored." }], details: { error: "all_noise" } };
      }

      const start = Date.now();
      try {
        const currentSessionId = getCurrentSessionId();

        if (isSubagentSession(currentSessionId)) {
          return { content: [{ type: "text", text: "Memory storage is not available in subagent sessions." }], details: { error: "subagent_blocked" } };
        }

        const uid = resolveUserId({ agentId: p.agentId, userId: p.userId });
        const runId = !(p.longTerm ?? true) && currentSessionId ? currentSessionId : undefined;

        if (skillsActive) {
          const rawMetadata = p.metadata;
          const category = p.category ?? rawMetadata?.category as string | undefined;
          const importance = p.importance ?? rawMetadata?.importance as number | undefined;
          const parsedMetadata: Record<string, unknown> = {
            ...(rawMetadata ?? {}),
            ...(category && { category }),
            ...(importance !== undefined && { importance }),
          };

          const addOpts: BackendAddOptions = {
            userId: uid,
            infer: false,
            deducedMemories: allFacts,
            metadata: parsedMetadata,
          };
          if (runId) addOpts.runId = runId;

          const result = (await backend.add(undefined, [{ role: "user", content: allFacts.join("\n") }], addOpts)) as BackendAddResult;
          const count = result.results?.length ?? 0;
          api.logger.info(`openclaw-mem0: stored ${count} memor${count === 1 ? "y" : "ies"} (infer=false, category=${category ?? "none"})`);

          deps.captureToolEvent("memory_add", { success: true, latency_ms: Date.now() - start, fact_count: allFacts.length, mode: "skills" });
          return {
            content: [{ type: "text", text: `Stored ${allFacts.length} fact(s) [${category ?? "uncategorized"}]: ${allFacts.map(f => `"${f.slice(0, 60)}${f.length > 60 ? "..." : ""}"`).join(", ")}` }],
            details: { action: "stored", mode: "skills", category, factCount: allFacts.length, results: result.results },
          };
        }

        const combinedText = allFacts.join("\n");
        const provOpts = buildAddOptions(uid, runId, currentSessionId);
        const addOpts: BackendAddOptions = { userId: provOpts.user_id };
        if (provOpts.run_id) addOpts.runId = provOpts.run_id;
        if (provOpts.custom_instructions) addOpts.customInstructions = provOpts.custom_instructions;
        if (provOpts.custom_categories) addOpts.customCategories = provOpts.custom_categories;
        if (cfg.customInstructions && !addOpts.customInstructions) addOpts.customInstructions = cfg.customInstructions;
        if (cfg.customCategories && !addOpts.customCategories) addOpts.customCategories = cfg.customCategories;

        const result = (await backend.add(undefined, [{ role: "user", content: combinedText }], addOpts)) as BackendAddResult;
        const added = result.results?.filter((r) => r.event === "ADD") ?? [];
        const updated = result.results?.filter((r) => r.event === "UPDATE") ?? [];
        const summary = [];
        if (added.length > 0) summary.push(`${added.length} added`);
        if (updated.length > 0) summary.push(`${updated.length} updated`);
        if (summary.length === 0) summary.push("No new memories extracted");

        deps.captureToolEvent("memory_add", { success: true, latency_ms: Date.now() - start, fact_count: allFacts.length });
        return {
          content: [{ type: "text", text: `Stored: ${summary.join(", ")}. ${result.results?.map((r) => `[${r.event}] ${r.memory}`).join("; ") ?? ""}` }],
          details: { action: "stored", results: result.results },
        };
      } catch (err) {
        deps.captureToolEvent("memory_add", { success: false, latency_ms: Date.now() - start, error: String(err) });
        return { content: [{ type: "text", text: `Memory add failed: ${String(err)}` }], details: { error: String(err) } };
      }
    },
  };
}
