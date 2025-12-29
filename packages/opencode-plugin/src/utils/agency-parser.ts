/**
 * AGENCY.md Parser
 * 
 * Utilities for parsing and serializing AGENCY.md files:
 * - Parse YAML frontmatter
 * - Extract metadata
 * - Serialize back to YAML
 */

import { parse as parseYaml, stringify as stringifyYaml } from 'yaml';
import type { AgencyMetadata } from '../types/index.js';

/**
 * Parse AGENCY.md content
 * 
 * @param content - Raw file content
 * @returns Parsed metadata and markdown content
 */
export const parseAgencyFile = (
  content: string
): { metadata: AgencyMetadata; markdown: string } => {
  // TODO: Implement AGENCY.md parsing
  // 1. Extract YAML frontmatter between --- markers
  // 2. Parse YAML to object
  // 3. Validate required fields
  // 4. Extract markdown content
  // 5. Return both parts
  
  const frontmatterRegex = /^---\n([\s\S]*?)\n---\n([\s\S]*)$/;
  const match = content.match(frontmatterRegex);
  
  if (!match) {
    throw new Error('Invalid AGENCY.md format: missing frontmatter');
  }
  
  const [, yamlContent, markdown] = match;
  const metadata = parseYaml(yamlContent) as AgencyMetadata;
  
  // Validate required fields
  if (!metadata.project_id) {
    throw new Error('Invalid AGENCY.md: missing project_id');
  }
  
  return { metadata, markdown };
};

/**
 * Serialize metadata and content back to AGENCY.md format
 * 
 * @param metadata - Project metadata
 * @param markdown - Markdown content
 * @returns Complete AGENCY.md file content
 */
export const serializeAgencyFile = (
  metadata: AgencyMetadata,
  markdown: string
): string => {
  // TODO: Implement AGENCY.md serialization
  // 1. Convert metadata to YAML
  // 2. Wrap in --- markers
  // 3. Append markdown content
  // 4. Return complete file
  
  const yamlContent = stringifyYaml(metadata);
  
  return `---\n${yamlContent}---\n${markdown}`;
};

/**
 * Update specific metadata fields
 * 
 * @param content - Current file content
 * @param updates - Fields to update
 * @returns Updated file content
 */
export const updateMetadata = (
  content: string,
  updates: Partial<AgencyMetadata>
): string => {
  const { metadata, markdown } = parseAgencyFile(content);
  
  // Merge updates
  const updatedMetadata = { ...metadata, ...updates };
  
  // Update timestamp
  updatedMetadata.last_updated = new Date().toISOString();
  
  return serializeAgencyFile(updatedMetadata, markdown);
};
