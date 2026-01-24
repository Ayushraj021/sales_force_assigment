# Task Implementation Workflow

1. Fetch the next unassigned/in-progress story from Plane workspace
2. Read the story requirements and acceptance criteria
3. Implement the feature following TDD:
   - Write failing tests first
   - Implement minimal code to pass
   - Refactor if needed
4. Run all tests
5. If tests pass, commit with story ID in message
6. Update story status in Plane to "Done"
7. Output `<promise>`STORY_COMPLETE`</promise>`

If blocked:

- Document blockers in story comments
- Move story to "Blocked" status
- Output `<promise>`STORY_BLOCKED`</promise>`

```

### Step 3: Run the Ralph Loop
```

/ralph-loop "Use Plane MCP to fetch the highest priority story from [YOUR_PROJECT].

Read the story details and acceptance criteria.

Implement the feature:

- Write tests first
- Implement code
- Run tests until green
- Commit with format: 'feat: [STORY-ID] description'

When complete, update story status in Plane to Done.

Output `<promise>`DONE`</promise>` when story is shipped." --max-iterations 30 --completion-promise "DONE"

```

---

## Multi-Story Batch Loop

For processing multiple stories overnight:
```

/ralph-loop "Loop through stories:

1. Use Plane MCP to get next 'Todo' story from [PROJECT]
2. Move story to 'In Progress'
3. Implement the story (TDD approach)
4. Run tests
5. If pass: commit, move story to 'Done'
6. If fail after 5 attempts: move to 'Blocked', add comment
7. Repeat for next story

Stop when no more 'Todo' stories remain.

Output `<promise>`ALL_DONE`</promise>` when queue empty." --max-iterations 100 --completion-promise "ALL_DONE"

```

---

## Practical Tips

**Filter stories smartly:**
- Only pull stories with clear acceptance criteria
- Skip stories tagged "needs-discussion" or "design-required"

**Story format matters:**
Make sure your Plane stories have:
- Clear title
- Acceptance criteria (checkboxes work well)
- Technical notes if needed

**Example good story format in Plane:**
```

Title: Add password reset endpoint

Acceptance Criteria:

- [ ] POST /api/reset-password accepts email
- [ ] Sends reset email with token
- [ ] Token expires in 1 hour
- [ ] Returns 200 on success, 404 if email not found

Tech notes: Use existing email service in /lib/email

```

---

## Prompt Template for Plane + Ralph
```

/ralph-loop "You have access to Plane MCP.

Project: [YOUR_PROJECT_NAME]
Workspace: [YOUR_WORKSPACE]

Workflow:

1. Fetch highest priority story with status 'Todo'
2. Update status to 'In Progress'
3. Read acceptance criteria carefully
4. Implement using TDD
5. Run: npm test
6. If green: git commit, update Plane status to 'Done'
7. If stuck: comment on story, move to 'Blocked'

Output `<promise>`SHIPPED `</promise>` after completing one story." --max-iterations 25 --completion-promise "SHIPPED"
