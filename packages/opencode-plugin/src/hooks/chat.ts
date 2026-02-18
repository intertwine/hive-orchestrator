/**
 * Chat message hooks
 * 
 * Handles chat message interception:
 * - Inject project context when project is mentioned
 * - Add AGENCY.md content to message context
 */

import type {
  PluginContext,
  AgentHiveConfig,
  ChatMessage,
} from '../types/index.js';

/**
 * Hook called for each chat message
 * 
 * @param message - The chat message
 * @param context - OpenCode plugin context
 * @param config - Agent Hive configuration
 * @returns Modified message with injected context
 */
export const chatMessageHook = async (
  message: ChatMessage,
  context: PluginContext,
  config: Required<AgentHiveConfig>
): Promise<ChatMessage> => {
  // TODO: Implement context injection logic
  // 1. Check if context injection is enabled
  // 2. Discover all projects
  // 3. Find if message mentions any project
  // 4. If project is owned by this agent, inject AGENCY.md content
  // 5. Return modified message
  
  if (!config.injectContext) return message;
  
  // Context injection will be implemented here
  return message;
};
