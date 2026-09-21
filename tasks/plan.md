# v0.1 implementation plan

Specs and scope: ../docs/architecture.md. Task tracker: todo.md (no duplicate external tracker).

1. Identity and membership: schema + service + API + tests. Prove default-off demo, authenticated sessions and approval-gated access.
2. Content and media: private post creation/read/search, moderation and comments, bounded private upload. Test outsider and pending-content leakage.
3. Events and governance: transactional capacity, cancellation/promotion and two-person handover. Test concurrency, stale rights and duplicate requests.
4. Clients: original sage/forest design, native mini source with two build targets and browser acceptance UI. Test the actual HTTP flows and mobile layout.
5. Read-only MCP: initialize/list/call through the same API; test token expiry/error behavior and unknown methods.
6. Delivery: start commands, CI, verification report, Git branch push and PR. Real-host login and deployment remain clearly unverified.

Every slice: write relevant failing tests → implement → focused green check → commit. Final comprehensive checks once the combined state exists. Correct detected defects and rerun affected checks; do not add verification solely as reassurance.
