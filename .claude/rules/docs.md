---
paths:
  - "docs/**/*.md"
  - "README.md"
  - "**/CLAUDE.md"
---

# Documentation rules

- Describe the system **as it is now**. Never write "previously", "we used to", "migrated from" or similar.
- Use short bullets and tables, not long paragraphs. One idea per bullet.
- Give an example for every rule (real numbers, real JSON, real commands).
- Use Mermaid diagrams for flows (`sequenceDiagram`), structure (`flowchart`), states (`stateDiagram-v2`) and data (`erDiagram`).
- Link code as `[file.py](relative/path#L42)`.
- `docs/api/*.md` (except README) and `docs/database.md` are generated. Change the code, then run `scripts/gen-docs.sh`.
- When features or gaps change, update `docs/project-status.md` and its date.
