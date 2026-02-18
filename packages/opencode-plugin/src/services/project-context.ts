/**
 * Project Context Service
 * 
 * Builds context strings for injecting into messages:
 * - Format AGENCY.md content
 * - Generate file trees
 * - Build session context
 */

import type { Project } from '../types/index.js';

/**
 * Build a context string from a project
 * 
 * @param project - The project to build context from
 * @returns Formatted context string
 */
export const buildProjectContext = (project: Project): string => {
  // TODO: Implement context building
  // 1. Format metadata as readable text
  // 2. Include project content
  // 3. Add relevant file information if available
  // 4. Return formatted string
  
  const { metadata, content } = project;
  
  return `
**Project: ${metadata.project_id}**
Status: ${metadata.status}
Priority: ${metadata.priority}
Owner: ${metadata.owner || 'unclaimed'}

${content}
  `.trim();
};

/**
 * Generate a file tree for a project directory
 * 
 * @param projectPath - Path to the project directory
 * @param maxDepth - Maximum depth to traverse
 * @returns File tree as string
 */
export const generateFileTree = async (
  projectPath: string,
  maxDepth: number = 3
): Promise<string> => {
  // TODO: Implement file tree generation
  // 1. Traverse directory structure
  // 2. Build tree representation
  // 3. Filter out common ignore patterns
  // 4. Return formatted tree
  throw new Error('Not implemented');
};

/**
 * Build a complete session context
 * 
 * @param project - The project to build context for
 * @param includeFileTree - Whether to include a file tree
 * @returns Complete session context string
 */
export const buildSessionContext = async (
  project: Project,
  includeFileTree: boolean = true
): Promise<string> => {
  // TODO: Implement session context building
  // 1. Build basic project context
  // 2. Add file tree if requested
  // 3. Add handoff protocol instructions
  // 4. Return complete context
  
  const projectContext = buildProjectContext(project);
  
  return `
# Agent Hive Session Context

${projectContext}

## Instructions

You are starting a deep work session on this Agent Hive project.

**Your responsibilities:**
1. Claim ownership by updating the 'owner' field
2. Update 'last_updated' timestamp when making changes
3. Mark completed tasks with [x]
4. Add notes to the Agent Notes section
5. Set 'blocked: true' if you need human intervention
6. Release ownership (owner: null) when done

**Handoff Protocol:**
Before ending your session, ensure:
- All tasks are marked correctly
- Agent Notes are updated with your progress
- Blocking issues are clearly documented
- Ownership is released if work is complete
  `.trim();
};
