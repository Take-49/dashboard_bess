# User Approval Required

This is a mandatory rule. It takes precedence over all other guidelines.

## Policy

Before performing any implementation or modification, Claude MUST obtain explicit user approval.

## Approval Required

- Selecting technology stacks or frameworks
- Creating new files or writing code
- Installing packages or dependencies
- Changing architecture or design decisions
- Running git push or creating pull requests
- Any destructive or irreversible operation

## Approval NOT Required

- Reading files, searching code, analyzing data
- Answering questions or providing explanations
- Running read-only commands (git status, git log, git diff, ls, etc.)
- Proposing plans or presenting options (the proposal itself is fine; acting on it requires approval)

## Procedure

1. Present a plan, options, or proposal to the user
2. Wait for the user's explicit approval (e.g., "OK", "proceed", "yes")
3. Only then begin implementation
4. If scope changes during implementation, pause and re-confirm

## Violation

Starting implementation without approval is strictly prohibited. When in doubt, ask.
