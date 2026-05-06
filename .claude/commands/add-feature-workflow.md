[CRITICAL WORKFLOW TRIGGERED: add-feature-workflow]

The user has requested a feature implementation or refinement. You MUST follow this exact 7-step workflow. Do NOT skip any step. Do NOT start editing files before the user explicitly approves the plan in Step 4.

1. CONFIRM CONTEXT
   - Run `git status` and `pwd` to confirm the current branch and working directory.
   - Report the branch name and any uncommitted changes to the user.

2. UNDERSTAND REQUIREMENT
   - Read the request carefully. Identify ambiguities (UI behavior, data model, edge cases, scope boundaries).
   - Ask clarifying questions if anything is unclear. Do not proceed until the requirement is fully understood.

3. IDENTIFY AFFECTED AREAS
   - Search the codebase for all files that will need changes.
   - Consider: models, serializers, views, URLs, permissions, API clients, React components, pages, routing, tests.
   - List every affected file explicitly.

4. PRODUCE PLAN AND ASK FOR APPROVAL
   - Create a detailed, step-by-step implementation plan.
   - Use EnterPlanMode to present the plan to the user.
   - Wait for explicit user approval before making ANY file edits.
   - If the user rejects or modifies the plan, update it and ask again.

5. IMPLEMENT IN STRICT ORDER
   a. Database schema: models.py -> makemigrations -> migrate
   b. Backend code: serializers -> views -> URLs -> permissions
   c. Frontend code: API methods -> components -> pages -> routing

6. UPDATE TESTS AND VERIFY BEHAVIOR
   - Update existing tests or add new ones for the changed behavior.
   - Run the full test suite:
     - Backend: `cd backend && python manage.py test`
     - Frontend: `cd frontend && npm test`
   - Start dev servers (`python manage.py runserver` + `npm run dev`) and manually verify the feature in the browser.
   - Fix any failures before declaring complete.

7. PREPARE SUMMARY OF CHANGES
   - List every file modified, created, or deleted.
   - Summarize the behavioral changes.
   - Note any testing performed and its results.

End of add-feature-workflow directive.
