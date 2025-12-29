/**
 * Main entry point for the Agent Hive OpenCode Plugin
 */

import type { AgentHiveConfig } from './types/index.js';

/**
 * Agent Hive Plugin for OpenCode
 * 
 * Provides deep integration with Agent Hive's orchestration system:
 * - Automates project discovery and claiming
 * - Enforces ownership before file edits
 * - Injects project context automatically
 * - Tracks all actions in Agent Notes
 * - Ensures clean handoff on session end
 * 
 * @example
 * ```typescript
 * import { AgentHivePlugin } from '@agent-hive/opencode-plugin';
 * 
 * // In your opencode.json:
 * {
 *   "plugins": [
 *     ["@agent-hive/opencode-plugin", {
 *       "basePath": ".",
 *       "autoClaimOnEdit": true,
 *       "enforceOwnership": false,
 *       "injectContext": true,
 *       "logActions": true,
 *       "agentName": "opencode-claude"
 *     }]
 *   ]
 * }
 * ```
 */
export const AgentHivePlugin = async (
  context: unknown,
  config: AgentHiveConfig = {}
): Promise<void> => {
  // Default configuration
  const finalConfig: Required<AgentHiveConfig> = {
    basePath: config.basePath || process.cwd(),
    autoClaimOnEdit: config.autoClaimOnEdit ?? true,
    enforceOwnership: config.enforceOwnership ?? false,
    injectContext: config.injectContext ?? true,
    logActions: config.logActions ?? true,
    coordinatorUrl: config.coordinatorUrl || '',
    agentName: config.agentName || 'opencode-agent',
  };

  // Plugin implementation will be added in subsequent phases
  console.log('🐝 Agent Hive Plugin initialized with config:', finalConfig);
  
  // TODO: Phase 2 - Implement core services
  // TODO: Phase 3 - Implement hooks
  // TODO: Phase 4 - Integrate with MCP
};

// Export types
export * from './types/index.js';

// Export services (to be implemented in Phase 2)
// export * from './services/index.js';

// Export hooks (to be implemented in Phase 3)
// export * from './hooks/index.js';

// Export utilities (to be implemented in Phase 2)
// export * from './utils/index.js';
