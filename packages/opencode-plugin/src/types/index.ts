/**
 * Type definitions for the Agent Hive OpenCode Plugin
 */

/**
 * Configuration options for the Agent Hive plugin
 */
export interface AgentHiveConfig {
  /**
   * Path to hive root directory
   * @default process.cwd()
   */
  basePath?: string;

  /**
   * Automatically claim projects when editing files
   * @default true
   */
  autoClaimOnEdit?: boolean;

  /**
   * Block file edits if project is not owned by current agent
   * @default false
   */
  enforceOwnership?: boolean;

  /**
   * Inject AGENCY.md context on session start
   * @default true
   */
  injectContext?: boolean;

  /**
   * Log actions to Agent Notes section
   * @default true
   */
  logActions?: boolean;

  /**
   * Optional coordinator server URL for real-time conflict prevention
   */
  coordinatorUrl?: string;

  /**
   * Agent identifier (e.g., "opencode-claude")
   * @default "opencode-{model}"
   */
  agentName?: string;
}

/**
 * Project status values
 */
export type ProjectStatus = 'active' | 'pending' | 'blocked' | 'completed';

/**
 * Project priority levels
 */
export type ProjectPriority = 'low' | 'medium' | 'high' | 'critical';

/**
 * Project dependencies structure
 */
export interface ProjectDependencies {
  blocked_by: string[];
  blocks: string[];
  parent: string | null;
  related: string[];
}

/**
 * AGENCY.md frontmatter structure
 */
export interface AgencyMetadata {
  project_id: string;
  status: ProjectStatus;
  owner: string | null;
  last_updated: string | null;
  blocked: boolean;
  blocking_reason: string | null;
  priority: ProjectPriority;
  tags: string[];
  dependencies?: ProjectDependencies;
  relevant_files?: string[];
  target_repo?: {
    url: string;
    branch: string;
  };
}

/**
 * Complete project information including file path and content
 */
export interface Project {
  metadata: AgencyMetadata;
  path: string;
  content: string;
}

/**
 * Plugin context provided by OpenCode
 */
export interface PluginContext {
  // Add OpenCode-specific context fields as they become available
  workingDirectory: string;
  model?: string;
}

/**
 * Tool input structure
 */
export interface ToolInput {
  tool: string;
  args: Record<string, unknown>;
}

/**
 * Tool output structure
 */
export interface ToolOutput {
  success: boolean;
  result?: unknown;
  error?: string;
}

/**
 * Chat message structure
 */
export interface ChatMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
}
