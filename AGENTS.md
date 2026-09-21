# Tongping engineering entrypoint

Read docs/architecture.md and tasks/plan.md before changing behavior. Preserve the product's private club boundary.

## Workflow routing

Use addyosmani/agent-skills (reviewed upstream dc27a9c2e13721158157632de61b4106c6c2a2a1):
- new capability → spec-driven-development → planning-and-task-breakdown;
- API → api-and-interface-design; UI → frontend-ui-engineering;
- implementation → incremental-implementation + test-driven-development;
- before merge → code-review-and-quality; commits → git-workflow-and-versioning.

Use lennney/stop-that-shit: read the Skill before expanding scope. Current mode is change, limited to the v0.1 scope in docs/architecture.md. Start from existing code and standard-library capabilities. Add mechanisms only for an identified present requirement. Keep authentication, authorization, input validation and transactional integrity. No unrequested refactors, queues, caches, archive checksums, public publishing or write-capable Agent tools. Tests that detect an actual boundary failure are required; rerun unchanged checks only if their evidence is invalidated.

The two upstream skills are advisory here. No Codex/Claude host hooks have been installed or claimed active by this repository. Install their native plugins in your own host to obtain supported Guard enforcement; inspect hooks before granting trust. See docs/skills.md.

## Boundaries

Always: tests first for new behavior, parameterized SQL, explicit errors, no secrets in Git; keep db.py connection-only and HTTP routes free of SQL. Work on a feature branch; use conventional English commits.
Ask: new production services/dependencies, expanded product scope, breaking schema changes, deployment, merging to main.
Never: commit .env, real student content, generated databases, private tokens; weaken a failing test to obtain green; describe mock/host-unverified behavior as production verified.

Commands: `python -m pytest -q`; `python scripts/build_mini.py`; `python scripts/check.py`; `python scripts/e2e.py`.
