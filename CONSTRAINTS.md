# v0.1 quality constraints

- Architecture gate: docs/architecture.md precedes implementation; routes contain no SQL, db.py no business policy.
- Scope: app v0.1 plus read-only MCP; no chat, payments, ranking, public publication, plugin framework or multi-instance deployment.
- Runtime dependencies: FastAPI, uvicorn, httpx (provider exchange), python-multipart (native uploads), Pillow (safe image decoding). SQLite is standard-library. Versions are recorded from the verified local environment, not claimed latest.
- Trust boundaries: current membership on every private read; pending content and private media cannot leak via detail, search or MCP.
- Identity: provider-scoped identity; default-off demo; no privileged roles accepted from the client; token hashes protect stored sessions, not ornamental release checksums.
- Data: unique registrations and serialized capacity decision; state changes audited where relevant; database transactions roll back on errors.
- Quality gate: API tests, build/static checks and browser/MCP checks. No skipped failing tests, fake benchmark numbers or claim of real-host validation.
- Stop condition: scoped implementation works, final evidence is current, remote push is verified, known release blockers are documented. No automatic deployment/merge.
