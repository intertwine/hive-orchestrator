/**
 * Session lifecycle hooks
 * 
 * Handles session start and end events:
 * - Display ready work on session start
 * - Show owned projects
 * - Remind about handoff protocol on session end
 */

import type { PluginContext, AgentHiveConfig } from '../types/index.js';

/**
 * Hook called when a session starts
 * 
 * @param context - OpenCode plugin context
 * @param config - Agent Hive configuration
 */
export const sessionStartHook = async (
  context: PluginContext,
  config: Required<AgentHiveConfig>
): Promise<void> => {
  // TODO: Implement session start logic
  // 1. Discover all projects
  // 2. Find ready work (unblocked, unclaimed)
  // 3. Display ready work to user
  // 4. Show currently owned projects
  console.log('🐝 Session started');
};

/**
 * Hook called when a session ends
 * 
 * @param context - OpenCode plugin context
 * @param config - Agent Hive configuration
 */
export const sessionEndHook = async (
  context: PluginContext,
  config: Required<AgentHiveConfig>
): Promise<void> => {
  // TODO: Implement session end logic
  // 1. Find projects owned by this agent
  // 2. Display handoff protocol reminder
  // 3. Add automatic closing note to owned projects
  console.log('🐝 Session ended');
};
