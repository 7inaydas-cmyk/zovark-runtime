# Storage Schema

Status: future Phase 2 scope.

No storage schema is implemented in Phase 0.

Future storage work must keep vendor schemas as mapping/export surfaces only.
Canonical runtime storage must use Zovark-owned schemas compatible with the
ADR-0036 schema boundary.

Future investigation_memory storage must record at minimum:

- memory reference ID;
- content hash;
- content size;
- source tool-call reference;
- created record metadata; and
- retention assumptions.

