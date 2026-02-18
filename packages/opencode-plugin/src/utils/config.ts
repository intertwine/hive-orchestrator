/**
 * Configuration Management
 * 
 * Handles plugin configuration:
 * - Load configuration
 * - Validate settings
 * - Provide defaults
 */

import type { AgentHiveConfig } from '../types/index.js';

/**
 * Default configuration values
 */
export const DEFAULT_CONFIG: Required<AgentHiveConfig> = {
  basePath: process.cwd(),
  autoClaimOnEdit: true,
  enforceOwnership: false,
  injectContext: true,
  logActions: true,
  coordinatorUrl: '',
  agentName: 'opencode-agent',
};

/**
 * Merge user configuration with defaults
 * 
 * @param userConfig - User-provided configuration
 * @returns Complete configuration with defaults
 */
export const loadConfig = (
  userConfig: AgentHiveConfig = {}
): Required<AgentHiveConfig> => {
  return {
    basePath: userConfig.basePath || DEFAULT_CONFIG.basePath,
    autoClaimOnEdit: userConfig.autoClaimOnEdit ?? DEFAULT_CONFIG.autoClaimOnEdit,
    enforceOwnership: userConfig.enforceOwnership ?? DEFAULT_CONFIG.enforceOwnership,
    injectContext: userConfig.injectContext ?? DEFAULT_CONFIG.injectContext,
    logActions: userConfig.logActions ?? DEFAULT_CONFIG.logActions,
    coordinatorUrl: userConfig.coordinatorUrl || DEFAULT_CONFIG.coordinatorUrl,
    agentName: userConfig.agentName || DEFAULT_CONFIG.agentName,
  };
};

/**
 * Validate configuration values
 * 
 * @param config - Configuration to validate
 * @throws Error if configuration is invalid
 */
export const validateConfig = (config: Required<AgentHiveConfig>): void => {
  // Validate basePath exists
  if (!config.basePath) {
    throw new Error('basePath must be specified');
  }
  
  // Validate agentName is not empty
  if (!config.agentName || config.agentName.trim() === '') {
    throw new Error('agentName must be a non-empty string');
  }
  
  // Validate coordinatorUrl format if provided
  if (config.coordinatorUrl) {
    try {
      new URL(config.coordinatorUrl);
    } catch (error) {
      throw new Error(`Invalid coordinatorUrl: ${config.coordinatorUrl}`);
    }
  }
};
