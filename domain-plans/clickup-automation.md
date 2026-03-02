# Domain Plan: ClickUp Automation

## Purpose
Automate task creation, field population, and status management in Maya's ClickUp Master Task List. Reduces manual data entry while preserving the meticulous custom-field tagging that makes ClickUp function as external memory.

## Inputs
- knowledge/conventions.md — ClickUp naming conventions, status flow, Approach field semantics
- knowledge/tools.md — ClickUp architecture (workspace/space/list IDs), usage patterns
- data/clickup-fields.yaml — All 6 custom fields with complete option IDs, status definitions
- data/client-registry.yaml — Project field values mapped to client names

## System Overview
Maya manages a single Master Task List (ID `901318968458`) in Space "Task Dashboard" (ID `90139879792`), Workspace `90132317650`. She uses ClickUp almost daily.

**Task creation:** Manual. Task names start with a lowercase verb, kept short and actionable. Due dates are always set. Descriptions are optional (used for meeting notes, zoom links, addresses).

**Custom fields:** All 6 fields are populated on every task — Project (16 options mapping to clients/business lines), Effort (Tiny through Very Big), Revenue (None through Direct High), Scope (Internal/External), Approach (Dread through Excited), Readiness (Prepared/Upskilling). The Approach field is an emotional energy metric tied to the Zeigarnik effect — it's structural, not decorative.

**Status flow:** Not Started → Begun → Complete is typical. On Hold and Waiting are parking states. Scratch is for abandoned tasks. Maya's one inconsistency: sometimes a few days pass before she marks tasks complete.

**Checklists:** Not used. **Labels/tags:** Not used.

**Key constraint:** The Approach field ideally requires Maya's subjective input. If she doesn't respond, the default is Indifferent.

## Automation Requirements

### Task Creation
- Accept task input via natural language or structured request
- Format task name: lowercase verb first, short and actionable (e.g., "review song librarian job description from Vicki")
- Set due date (mandatory — reject task creation without one)
- Auto-populate custom fields using defaults and inference:
  - **Project:** Infer from context (client name, topic, conversation context). Map to the 16 options in `data/clickup-fields.yaml`. No default — must be inferred or asked.
  - **Effort:** Default "Small" (`91613c05-d60f-4da0-afa4-9ddbd27bb9b8`). Adjust based on task complexity. Maya confirms or overrides.
  - **Revenue:** Infer from Project (client tasks = Direct; internal tasks = None or Indirect). Maya confirms.
  - **Scope:** Default "External" (`e06f82ab-ba76-4a87-8583-0b4d54caf938`). Override to "Internal" for internal ops tasks.
  - **Approach:** Default "Indifferent" (`c5f38d05-209f-4525-9b69-e14af13552c8`). Always ask Maya — this is subjective emotional data — but if she doesn't respond, apply the default rather than blocking task creation.
  - **Readiness:** Default "Prepared" (`f297da50-a58f-41a3-8124-f588cf1fe6cc`). Override to "Upskilling" if task involves learning a new tool or skill.
- Set status to "Not Started" on creation.
- Add description only if context warrants it (meeting notes, zoom link, address).

### Task Querying
- Support queries like: "What's on my plate for Devon this week?", "Show me all Dread tasks", "What tasks are overdue?"
- Filter by: Project, Status, Effort, Revenue, Scope, Approach, Readiness, due date range
- Sort by: due date, Approach (surface Dread tasks for awareness), Effort

### Status Management
- Update status on Maya's instruction (never auto-advance)
- Support bulk status updates (e.g., "mark all Sulima tasks from last week complete")
- Flag tasks with "Not Started" status past their due date

### Reporting
- Weekly summary: tasks completed, tasks overdue, time allocation by Project
- Revenue visibility: tasks tagged Direct High/Direct Low by Project
- Emotional load: distribution of Approach values across active tasks

## Edge Cases & Constraints
- **Approach is subjective.** Always prompt Maya. If she doesn't respond, default to "Indifferent" rather than blocking. Never infer emotional state from task content.
- **Task naming must match Maya's style.** No Title Case, no full sentences, no bullet-style formatting. Lowercase verb phrases only.
- **No checklists.** Even if a task has sub-steps, ClickUp checklists are not used.
- **Project field mapping requires relationship knowledge.** "Nicole" maps to "Dalton Law." "Lynn's book" maps to "Lynn Haller." "Newsletter" likely maps to "Raging Grannies." See `data/client-registry.yaml` for the full mapping.
- **Daniela vs. Wren Cavanagh.** ClickUp project is "Daniela Morescalchi" (real name), not the pen name.
- **Free Cohort vs. Lingua Ink Cohorts.** Two separate ClickUp projects. Free Cohort is the current twice-weekly group; Lingua Ink Cohorts is the planned paid offering.
- **Single list architecture.** All tasks live in one list. No folders, no spaces, no multi-list workflows. Any automation must respect this flat structure.

## Implementation Notes

### API Details
- **Base URL:** `https://api.clickup.com/api/v2/`
- **Workspace ID:** `90132317650`
- **Space ID:** `90139879792`
- **List ID:** `901318968458`
- **API Token:** Not yet provided. Must be obtained from Maya during SL setup.

### Key Endpoints
- Create task: `POST /list/901318968458/task`
- Get tasks: `GET /list/901318968458/task` (supports filters)
- Update task: `PUT /task/{task_id}`
- Get task: `GET /task/{task_id}`

### Custom Field IDs (for API calls)
All from `data/clickup-fields.yaml`:
- **Project:** `9f921ca1-1b45-4b49-a463-a550287cc5b2` (dropdown, 16 options)
- **Effort:** `5db96854-9117-4857-8306-6f740ec31c3e` (dropdown, 5 options)
- **Revenue:** `44470f88-d8e2-4e14-9f39-c63b30e6aede` (dropdown, 5 options)
- **Scope:** `1e4539b4-0525-4b2e-9223-a3eef644f91f` (dropdown, 2 options)
- **Approach:** `b977f131-3c07-4b5d-935b-6a872c2cc0b6` (dropdown, 5 options)
- **Readiness:** `3b795a7d-728c-49ae-b00e-82a6dbd28431` (dropdown, 2 options)

### Custom Field Setting Format
ClickUp API requires custom fields as an array:
```json
{
  "custom_fields": [
    {"id": "9f921ca1-...", "value": "6a62e5e9-..."},
    {"id": "5db96854-...", "value": "eeb46716-..."}
  ]
}
```
Each `value` is the option UUID from clickup-fields.yaml, not the option name.

### Status Values (exact strings)
`"Not Started"`, `"On Hold"`, `"Waiting"`, `"Begun"`, `"Scratch"`, `"Complete"`

### Project → Option ID Quick Reference
See `data/clickup-fields.yaml` for the complete mapping. Key examples:
- Sulima Malzin → `6a62e5e9-0dc5-4f5c-b11e-0fabbb917105`
- Dalton Law → `848daa77-22e1-48d1-9156-f692b966d244`
- Devon Ervin → `04b61649-4b90-4525-a8fe-7b4654baf4b6`
- Raging Grannies → `48dfc203-1c7a-4fbd-8d3b-4ef845159629`
- Maya Bairey → `d721cedf-c9b5-4375-8bcd-1201711fe58a`

## Open Questions
- ClickUp API token: needed during SL setup
- Time tracking configuration: is the built-in ClickUp timer used, or is time tracked manually?
- Views and filters: does Maya use saved views? If so, automation should respect them.
- Rate of task creation: how many tasks per week on average? (Affects API rate limits)
