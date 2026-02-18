/**
 * Tests for utility modules
 */

import { describe, it, expect } from 'vitest';
import { loadConfig, validateConfig, DEFAULT_CONFIG } from '../src/utils/config';
import { parseAgencyFile, serializeAgencyFile, updateMetadata } from '../src/utils/agency-parser';
import { formatProject } from '../src/utils/logger';
import type { AgentHiveConfig, AgencyMetadata } from '../src/types';

describe('Utilities', () => {
  describe('config', () => {
    describe('loadConfig', () => {
      it('should return default config when no user config provided', () => {
        const config = loadConfig();
        expect(config).toEqual(DEFAULT_CONFIG);
      });

      it('should merge user config with defaults', () => {
        const userConfig: AgentHiveConfig = {
          agentName: 'custom-agent',
          autoClaimOnEdit: false,
        };

        const config = loadConfig(userConfig);

        expect(config.agentName).toBe('custom-agent');
        expect(config.autoClaimOnEdit).toBe(false);
        expect(config.injectContext).toBe(DEFAULT_CONFIG.injectContext);
      });
    });

    describe('validateConfig', () => {
      it('should throw on empty agentName', () => {
        const config = { ...DEFAULT_CONFIG, agentName: '' };
        expect(() => validateConfig(config)).toThrow('agentName must be a non-empty string');
      });

      it('should throw on invalid coordinatorUrl', () => {
        const config = { ...DEFAULT_CONFIG, coordinatorUrl: 'not-a-url' };
        expect(() => validateConfig(config)).toThrow('Invalid coordinatorUrl');
      });

      it('should accept valid config', () => {
        expect(() => validateConfig(DEFAULT_CONFIG)).not.toThrow();
      });
    });
  });

  describe('agency-parser', () => {
    const validAgencyContent = `---
project_id: test-project
status: active
owner: null
last_updated: '2025-01-01T00:00:00Z'
blocked: false
blocking_reason: null
priority: high
tags:
  - test
---
# Test Project

Content here`;

    describe('parseAgencyFile', () => {
      it('should parse valid AGENCY.md', () => {
        const result = parseAgencyFile(validAgencyContent);

        expect(result.metadata.project_id).toBe('test-project');
        expect(result.metadata.status).toBe('active');
        expect(result.metadata.priority).toBe('high');
        expect(result.markdown).toContain('# Test Project');
      });

      it('should throw on missing frontmatter', () => {
        expect(() => parseAgencyFile('# Just markdown')).toThrow('missing frontmatter');
      });

      it('should throw on missing project_id', () => {
        const invalid = `---
status: active
---
# Project`;
        expect(() => parseAgencyFile(invalid)).toThrow('missing project_id');
      });
    });

    describe('serializeAgencyFile', () => {
      it('should serialize metadata and markdown', () => {
        const metadata: AgencyMetadata = {
          project_id: 'test',
          status: 'active',
          owner: null,
          last_updated: '2025-01-01T00:00:00Z',
          blocked: false,
          blocking_reason: null,
          priority: 'high',
          tags: ['test'],
        };
        const markdown = '# Test\n\nContent';

        const result = serializeAgencyFile(metadata, markdown);

        expect(result).toContain('---');
        expect(result).toContain('project_id: test');
        expect(result).toContain('# Test');
      });
    });

    describe('updateMetadata', () => {
      it('should update metadata fields', () => {
        const result = updateMetadata(validAgencyContent, {
          owner: 'test-agent',
          status: 'completed',
        });

        expect(result).toContain('owner: test-agent');
        expect(result).toContain('status: completed');
        expect(result).toContain('# Test Project');
      });

      it('should update last_updated timestamp', () => {
        const result = updateMetadata(validAgencyContent, {});
        const parsed = parseAgencyFile(result);

        expect(parsed.metadata.last_updated).not.toBe('2025-01-01T00:00:00Z');
        expect(new Date(parsed.metadata.last_updated!).getTime()).toBeGreaterThan(0);
      });
    });
  });

  describe('logger', () => {
    describe('formatProject', () => {
      it('should format critical priority with red circle', () => {
        const result = formatProject('project-1', 'critical');
        expect(result).toBe('🔴 project-1 (critical)');
      });

      it('should format high priority with orange circle', () => {
        const result = formatProject('project-2', 'high');
        expect(result).toBe('🟠 project-2 (high)');
      });

      it('should format medium priority with yellow circle', () => {
        const result = formatProject('project-3', 'medium');
        expect(result).toBe('🟡 project-3 (medium)');
      });

      it('should format low priority with green circle', () => {
        const result = formatProject('project-4', 'low');
        expect(result).toBe('🟢 project-4 (low)');
      });
    });
  });
});
