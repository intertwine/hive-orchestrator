/**
 * Logging Utilities
 * 
 * Provides consistent logging for the plugin:
 * - Formatted console output
 * - Log levels
 * - Contextual messages
 */

/**
 * Log levels
 */
export enum LogLevel {
  DEBUG = 0,
  INFO = 1,
  WARN = 2,
  ERROR = 3,
}

/**
 * Current log level (default: INFO)
 */
let currentLogLevel: LogLevel = LogLevel.INFO;

/**
 * Set the log level
 * 
 * @param level - Log level to set
 */
export const setLogLevel = (level: LogLevel): void => {
  currentLogLevel = level;
};

/**
 * Log a debug message
 * 
 * @param message - Message to log
 * @param args - Additional arguments
 */
export const debug = (message: string, ...args: unknown[]): void => {
  if (currentLogLevel <= LogLevel.DEBUG) {
    console.debug(`🐝 [DEBUG] ${message}`, ...args);
  }
};

/**
 * Log an info message
 * 
 * @param message - Message to log
 * @param args - Additional arguments
 */
export const info = (message: string, ...args: unknown[]): void => {
  if (currentLogLevel <= LogLevel.INFO) {
    console.info(`🐝 ${message}`, ...args);
  }
};

/**
 * Log a warning message
 * 
 * @param message - Message to log
 * @param args - Additional arguments
 */
export const warn = (message: string, ...args: unknown[]): void => {
  if (currentLogLevel <= LogLevel.WARN) {
    console.warn(`🐝 [WARN] ${message}`, ...args);
  }
};

/**
 * Log an error message
 * 
 * @param message - Message to log
 * @param args - Additional arguments
 */
export const error = (message: string, ...args: unknown[]): void => {
  if (currentLogLevel <= LogLevel.ERROR) {
    console.error(`🐝 [ERROR] ${message}`, ...args);
  }
};

/**
 * Format a project for display
 * 
 * @param projectId - Project ID
 * @param priority - Project priority
 * @returns Formatted string with emoji
 */
export const formatProject = (
  projectId: string,
  priority: string
): string => {
  const priorityEmoji =
    priority === 'critical' ? '🔴' :
    priority === 'high' ? '🟠' :
    priority === 'medium' ? '🟡' : '🟢';
  
  return `${priorityEmoji} ${projectId} (${priority})`;
};
