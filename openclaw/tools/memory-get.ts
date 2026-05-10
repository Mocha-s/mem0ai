import { Type } from "@sinclair/typebox";
import type { ToolDeps } from "./index.ts";

export function createMemoryGetTool(deps: ToolDeps) {
  const { backend } = deps;

  return {
    name: "memory_get",
    label: "Memory Get",
    description: "Retrieve a specific memory by its ID from Mem0.",
    parameters: Type.Object({
      memoryId: Type.String({ description: "The memory ID to retrieve" }),
    }),

    async execute(_toolCallId: string, params: Record<string, unknown>) {
      const { memoryId } = params as { memoryId: string };
      const start = Date.now();
      try {
        const memory = (await backend.get(memoryId)) as {
          id?: string; memory?: string; created_at?: string; updated_at?: string;
        };
        deps.captureToolEvent("memory_get", { success: true, latency_ms: Date.now() - start });
        return {
          content: [{ type: "text", text: `Memory ${memory.id ?? memoryId}:\n${memory.memory ?? ""}\n\nCreated: ${memory.created_at ?? "unknown"}\nUpdated: ${memory.updated_at ?? "unknown"}` }],
          details: { memory },
        };
      } catch (err) {
        deps.captureToolEvent("memory_get", { success: false, latency_ms: Date.now() - start, error: String(err) });
        return { content: [{ type: "text", text: `Memory get failed: ${String(err)}` }], details: { error: String(err) } };
      }
    },
  };
}
