import { ProjectOptions, ProjectResponse, PromptUpdatePayload } from "./mem0.types";

/**
 * APIError class for handling project-related API errors
 */
class APIError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "APIError";
  }
}

/**
 * Interface for project update options with custom_instructions support
 */
export interface ProjectUpdateOptions {
  custom_instructions?: string;
  custom_categories?: any[];
  [key: string]: any;
}

/**
 * Interface for project get options
 */
export interface ProjectGetOptions {
  fields?: string[];
}

/**
 * Project class providing unified API for project management operations.
 * This class provides a consistent interface with the Python client for
 * managing project-level configurations including custom instructions.
 */
export class Project {
  private client: any;

  /**
   * Initialize the Project instance
   * @param client - The MemoryClient instance to use for API calls
   */
  constructor(client: any) {
    this.client = client;
  }

  /**
   * Validate custom_instructions parameter format
   * @param customInstructions - Custom instructions string to validate
   * @throws {APIError} If the format is invalid
   */
  private validateCustomInstructions(customInstructions?: string): void {
    if (customInstructions !== undefined) {
      if (typeof customInstructions !== "string") {
        throw new APIError("custom_instructions must be a string");
      }
      
      if (!customInstructions.trim()) {
        throw new APIError("custom_instructions cannot be empty or whitespace-only");
      }
      
      if (customInstructions.length > 10000) {
        throw new APIError("custom_instructions too long (max 10000 characters)");
      }
    }
  }

  /**
   * Get project configuration
   * @param options - Options for retrieving project data
   * @returns Promise resolving to project configuration
   * 
   * @example
   * ```typescript
   * const project = client.project;
   * const config = await project.get({ fields: ["custom_instructions"] });
   * console.log(config.custom_instructions);
   * ```
   */
  async get(options?: ProjectGetOptions): Promise<ProjectResponse> {
    const projectOptions: ProjectOptions = options || {};
    return this.client.getProject(projectOptions);
  }

  /**
   * Update project configuration
   * @param options - Update options including custom_instructions
   * @returns Promise resolving to update response
   * 
   * @example
   * ```typescript
   * const project = client.project;
   * const response = await project.update({
   *   custom_instructions: "Extract key facts from conversations"
   * });
   * console.log(response.message);
   * ```
   */
  async update(options: ProjectUpdateOptions): Promise<{ message: string }> {
    // Validate custom_instructions if provided
    this.validateCustomInstructions(options.custom_instructions);

    // Convert to PromptUpdatePayload format for backward compatibility
    const payload: PromptUpdatePayload = {
      custom_instructions: options.custom_instructions,
      custom_categories: options.custom_categories,
      ...options
    };

    return this.client.updateProject(payload);
  }
}

export default Project;
