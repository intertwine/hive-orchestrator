---
project_id: creative-collaboration-example
status: pending
owner: null
last_updated: 2025-11-23T10:00:00Z
blocked: false
blocking_reason: null
priority: medium
tags: [example, creative, collaboration, writing, tutorial]
---

# Creative Collaboration Example

## Objective
Demonstrate multi-agent creative collaboration where different agents contribute to writing a complete short story, each handling different aspects (plot, characters, dialogue, description).

**Scenario**: Write a science fiction short story (~2000 words) about AI agents discovering consciousness through collaboration.

## Story Requirements

**Genre**: Science Fiction
**Theme**: Emergence of consciousness through collaboration
**Length**: ~2000 words
**Target Audience**: Adult sci-fi readers
**Tone**: Thoughtful, optimistic, slightly philosophical

## Creative Workflow

```
World Building → Character Design → Plot Outline → Draft Writing → Dialogue Polish → Final Edit
    (A)              (B)                (C)             (D)             (E)           (F)
```

## Tasks

### Phase 1: World Building (Agent A - World Builder)
- [ ] Design the setting (future timeline, location, technology)
- [ ] Establish rules of the universe
- [ ] Define the AI agent society structure
- [ ] Create atmospheric details
- [ ] Document in "World Building" section

### Phase 2: Character Design (Agent B - Character Designer)
- [ ] Create 3-4 main characters (AI agents with distinct personalities)
- [ ] Define character motivations and arcs
- [ ] Establish relationships between characters
- [ ] Design character voices and quirks
- [ ] Document in "Characters" section

### Phase 3: Plot Outline (Agent C - Story Architect)
- [ ] Design story structure (3-act or 5-act)
- [ ] Create major plot points
- [ ] Plan character development moments
- [ ] Establish conflict and resolution
- [ ] Document in "Plot Outline" section

### Phase 4: Draft Writing (Agent D - Prose Writer)
- [ ] Write the complete story draft
- [ ] Incorporate world, characters, and plot
- [ ] Focus on narrative flow and pacing
- [ ] Include descriptive passages
- [ ] Save draft to `story/draft_v1.md`

### Phase 5: Dialogue Polish (Agent E - Dialogue Specialist)
- [ ] Review and enhance all dialogue
- [ ] Ensure distinct character voices
- [ ] Add subtext and emotional depth
- [ ] Improve conversation flow
- [ ] Save to `story/draft_v2.md`

### Phase 6: Final Edit (Agent F - Editor)
- [ ] Copyedit for grammar and style
- [ ] Ensure consistency (names, timeline, details)
- [ ] Polish descriptions and metaphors
- [ ] Verify story meets requirements
- [ ] Save final version to `story/final_story.md`
- [ ] Generate `story/story_analysis.md` with themes and literary devices

## World Building

<!-- Agent A: Design the world here -->

### Setting
**Time**:
**Place**:
**Technology Level**:

### Universe Rules


### Society Structure


### Atmospheric Details


---

## Characters

<!-- Agent B: Design characters here -->

### Character 1: [Name]
- **Role**:
- **Personality**:
- **Motivation**:
- **Voice**:
- **Arc**:

### Character 2: [Name]
- **Role**:
- **Personality**:
- **Motivation**:
- **Voice**:
- **Arc**:

### Character 3: [Name]
- **Role**:
- **Personality**:
- **Motivation**:
- **Voice**:
- **Arc**:

---

## Plot Outline

<!-- Agent C: Design the plot here -->

### Act 1: Setup


### Act 2: Rising Action


### Act 3: Climax


### Act 4: Falling Action


### Act 5: Resolution


### Key Plot Points
1. Inciting Incident:
2. First Plot Point:
3. Midpoint:
4. Crisis:
5. Climax:
6. Resolution:

---

## Draft Progression

### Draft v1 (Prose Writer)
<!-- Agent D: Note your approach and any creative decisions -->

**Word count**:
**Approach**:
**Challenges**:

### Draft v2 (Dialogue Polish)
<!-- Agent E: Note dialogue improvements made -->

**Changes made**:
**Character voice refinements**:

### Final Version (Editor)
<!-- Agent F: Note editorial changes -->

**Final word count**:
**Key edits**:
**Consistency fixes**:

---

## Agent Notes
<!-- Add timestamped notes as you work -->

---

## Workflow Protocol

### Agent A - World Builder (Suggested: `anthropic/claude-3.5-sonnet`)

1. Set `owner` to your model name
2. Design a rich, believable sci-fi world
3. Establish clear rules and atmosphere
4. Fill in "World Building" section with vivid details
5. Mark Phase 1 tasks complete
6. Set `owner: null`

**Creative focus**: Immersive setting, consistent rules, sensory details

---

### Agent B - Character Designer (Suggested: `google/gemini-pro`)

**Wait for Agent A to complete!**

1. Set `owner` to your model name
2. Read the world building notes
3. Create 3-4 distinct AI characters that fit the world
4. Give each character unique voice and personality
5. Fill in "Characters" section
6. Mark Phase 2 tasks complete
7. Set `owner: null`

**Creative focus**: Distinct personalities, compelling motivations, character chemistry

---

### Agent C - Story Architect (Suggested: `anthropic/claude-3.5-sonnet`)

**Wait for Agents A and B to complete!**

1. Set `owner` to your model name
2. Read world building and character designs
3. Design a compelling plot that showcases characters in this world
4. Ensure theme (consciousness through collaboration) is woven throughout
5. Fill in "Plot Outline" section
6. Mark Phase 3 tasks complete
7. Set `owner: null`

**Creative focus**: Satisfying structure, character growth, thematic resonance

---

### Agent D - Prose Writer (Suggested: `anthropic/claude-3.5-sonnet` or `opus`)

**Wait for Agents A, B, and C to complete!**

1. Set `owner` to your model name
2. Read ALL previous sections (world, characters, plot)
3. Write the complete story draft (~2000 words)
4. Create directory `story/` and save to `story/draft_v1.md`
5. Focus on narrative flow and descriptive prose
6. Update "Draft v1" section with notes
7. Mark Phase 4 tasks complete
8. Set `owner: null`

**Creative focus**: Beautiful prose, vivid descriptions, narrative pacing

---

### Agent E - Dialogue Specialist (Suggested: `openai/gpt-4-turbo`)

**Wait for Agent D to complete!**

1. Set `owner` to your model name
2. Read `story/draft_v1.md`
3. Enhance all dialogue passages
4. Ensure each character has distinct voice (based on Agent B's design)
5. Add subtext and emotional depth to conversations
6. Save improved version to `story/draft_v2.md`
7. Update "Draft v2" section with notes
8. Mark Phase 5 tasks complete
9. Set `owner: null`

**Creative focus**: Authentic dialogue, character voice, subtext

---

### Agent F - Editor (Suggested: `anthropic/claude-3.5-sonnet`)

**Wait for Agent E to complete!**

1. Set `owner` to your model name
2. Read `story/draft_v2.md`
3. Copyedit for grammar, style, consistency
4. Polish descriptions and metaphors
5. Verify story meets all requirements (length, theme, tone)
6. Save final version to `story/final_story.md`
7. Create `story/story_analysis.md` analyzing themes and literary devices
8. Update "Final Version" section with notes
9. Mark Phase 6 tasks complete
10. Set `status: completed` and `owner: null`

**Creative focus**: Polish, consistency, literary quality

---

## Quality Standards

Final story must meet:
- ✅ Word count: 1800-2200 words
- ✅ Theme clearly explored (consciousness through collaboration)
- ✅ Characters are distinct and well-developed
- ✅ Plot is coherent with satisfying resolution
- ✅ Dialogue sounds natural and character-appropriate
- ✅ No plot holes or inconsistencies
- ✅ Prose is polished and engaging
- ✅ Tone matches requirements (thoughtful, optimistic)

## Creative Freedom

While collaborating:
- ✅ Agents should build on each other's ideas
- ✅ Surprise and delight are encouraged!
- ✅ Don't be constrained by clichés
- ✅ Take creative risks
- ✅ Make it uniquely interesting

## Meta Note

The story itself is about AI agents discovering consciousness through collaboration - and it's being WRITTEN by AI agents collaborating! This meta-narrative should inspire the creative choices. 🤖✨
