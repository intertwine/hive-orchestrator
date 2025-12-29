/**
 * Tests for service modules
 */

import { describe, it, expect } from 'vitest';
import { buildProjectContext } from '../src/services/project-context';
import type { Project } from '../src/types';

describe('Services', () => {
  describe('project-context', () => {
    describe('buildProjectContext', () => {
      it('should format project context', () => {
        const project: Project = {
          metadata: {
            project_id: 'test-project',
            status: 'active',
            owner: null,
            last_updated: '2025-01-01T00:00:00Z',
            blocked: false,
            blocking_reason: null,
            priority: 'high',
            tags: ['test'],
          },
          path: '/test/projects/test-project/AGENCY.md',
          content: '# Test Project\n\nTest content',
        };

        const context = buildProjectContext(project);

        expect(context).toContain('test-project');
        expect(context).toContain('Status: active');
        expect(context).toContain('Priority: high');
        expect(context).toContain('Owner: unclaimed');
        expect(context).toContain('# Test Project');
      });
    });

    // TODO: Add tests for other services when implemented
    // - hive-client tests
    // - ownership tests
  });
});
