# Superpowers working files

Superpowers writes its session artifacts here:

- `specs/YYYY-MM-DD-<topic>-design.md` — output of the `brainstorming` skill
  (design decisions for an open question, before a plan exists)
- `plans/YYYY-MM-DD-<topic>.md` — output of `writing-plans`; `executing-plans`
  works through it task by task

These are session-level. The feature-level source of truth is the Spec Kit
spec in `specs/NNN-<feature>/` (`spec.md`, `plan.md`, `tasks.md`). A Superpowers
plan should link the Spec Kit task IDs it implements.
