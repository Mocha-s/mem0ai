import { MemoryConfig, MemoryConfigSchema } from "../types";
import { DEFAULT_MEMORY_CONFIG } from "./defaults";

/**
 * Field aliases mapping for backward compatibility
 * Allows custom_instructions and customPrompt to be used interchangeably
 */
const FIELD_ALIASES = {
  'custom_instructions': 'customPrompt',
  'customPrompt': 'custom_instructions'
} as const;

export class ConfigManager {
  static mergeConfig(userConfig: Partial<MemoryConfig> = {}): MemoryConfig {
    // Handle field aliases for backward compatibility
    const processedConfig = { ...userConfig };

    // Handle custom_instructions -> customPrompt mapping
    if ('custom_instructions' in processedConfig && processedConfig.custom_instructions !== undefined) {
      if (!processedConfig.customPrompt) {
        processedConfig.customPrompt = (processedConfig as any).custom_instructions;
      }
      // Remove the alias field to avoid confusion
      delete (processedConfig as any).custom_instructions;
    }
    const mergedConfig = {
      version: processedConfig.version || DEFAULT_MEMORY_CONFIG.version,
      embedder: {
        provider:
          processedConfig.embedder?.provider ||
          DEFAULT_MEMORY_CONFIG.embedder.provider,
        config: (() => {
          const defaultConf = DEFAULT_MEMORY_CONFIG.embedder.config;
          const userConf = processedConfig.embedder?.config;
          let finalModel: string | any = defaultConf.model;

          if (userConf?.model && typeof userConf.model === "object") {
            finalModel = userConf.model;
          } else if (userConf?.model && typeof userConf.model === "string") {
            finalModel = userConf.model;
          }

          return {
            apiKey:
              userConf?.apiKey !== undefined
                ? userConf.apiKey
                : defaultConf.apiKey,
            model: finalModel,
            url: userConf?.url,
            modelProperties:
              userConf?.modelProperties !== undefined
                ? userConf.modelProperties
                : defaultConf.modelProperties,
          };
        })(),
      },
      vectorStore: {
        provider:
          processedConfig.vectorStore?.provider ||
          DEFAULT_MEMORY_CONFIG.vectorStore.provider,
        config: (() => {
          const defaultConf = DEFAULT_MEMORY_CONFIG.vectorStore.config;
          const userConf = processedConfig.vectorStore?.config;

          // Prioritize user-provided client instance
          if (userConf?.client && typeof userConf.client === "object") {
            return {
              client: userConf.client,
              // Include other fields from userConf if necessary, or omit defaults
              collectionName: userConf.collectionName, // Can be undefined
              dimension: userConf.dimension || defaultConf.dimension, // Merge dimension
              ...userConf, // Include any other passthrough fields from user
            };
          } else {
            // If no client provided, merge standard fields
            return {
              collectionName:
                userConf?.collectionName || defaultConf.collectionName,
              dimension: userConf?.dimension || defaultConf.dimension,
              // Ensure client is not carried over from defaults if not provided by user
              client: undefined,
              // Include other passthrough fields from userConf even if no client
              ...userConf,
            };
          }
        })(),
      },
      llm: {
        provider:
          processedConfig.llm?.provider || DEFAULT_MEMORY_CONFIG.llm.provider,
        config: (() => {
          const defaultConf = DEFAULT_MEMORY_CONFIG.llm.config;
          const userConf = processedConfig.llm?.config;
          let finalModel: string | any = defaultConf.model;

          if (userConf?.model && typeof userConf.model === "object") {
            finalModel = userConf.model;
          } else if (userConf?.model && typeof userConf.model === "string") {
            finalModel = userConf.model;
          }

          return {
            baseURL: userConf?.baseURL || defaultConf.baseURL,
            apiKey:
              userConf?.apiKey !== undefined
                ? userConf.apiKey
                : defaultConf.apiKey,
            model: finalModel,
            modelProperties:
              userConf?.modelProperties !== undefined
                ? userConf.modelProperties
                : defaultConf.modelProperties,
          };
        })(),
      },
      historyDbPath:
        processedConfig.historyDbPath || DEFAULT_MEMORY_CONFIG.historyDbPath,
      customPrompt: processedConfig.customPrompt,
      graphStore: {
        ...DEFAULT_MEMORY_CONFIG.graphStore,
        ...processedConfig.graphStore,
      },
      historyStore: {
        ...DEFAULT_MEMORY_CONFIG.historyStore,
        ...processedConfig.historyStore,
      },
      disableHistory:
        processedConfig.disableHistory || DEFAULT_MEMORY_CONFIG.disableHistory,
      enableGraph: processedConfig.enableGraph || DEFAULT_MEMORY_CONFIG.enableGraph,
    };

    // Validate the merged config
    return MemoryConfigSchema.parse(mergedConfig);
  }
}
