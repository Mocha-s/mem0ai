// OpenMemory Legacy Types - Maintained for backward compatibility

export type Category = "personal" | "work" | "health" | "finance" | "travel" | "education" | "preferences" | "relationships"
export type Client = "chrome" | "chatgpt" | "cursor" | "windsurf" | "terminal" | "api"

// Legacy Memory interface for OpenMemory system
export interface Memory {
  id: string
  memory: string
  metadata: any
  client: Client
  categories: Category[]
  created_at: number
  app_name: string
  state: "active" | "paused" | "archived" | "deleted"
}

// Extended categories to support Mem0 custom categories
export type ExtendedCategory = Category | string;

// Memory state types
export type MemoryState = "active" | "paused" | "archived" | "deleted";

// Client types extended for new integrations
export type ExtendedClient = Client | "mem0" | "mcp" | "custom";

// Legacy type aliases for backward compatibility
export type OpenMemoryMemory = Memory;
export type OpenMemoryCategory = Category;
export type OpenMemoryClient = Client;