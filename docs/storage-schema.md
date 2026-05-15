# Storage Schema

Status: Phase 2B storage substrate introduced.

Phase 2B implements local file-backed `investigation_memory` storage metadata.
This is not a retrieval service and does not produce model-visible output.

Future storage work must keep vendor schemas as mapping/export surfaces only.
Canonical runtime storage must use Zovark-owned schemas compatible with the
ADR-0036 schema boundary.

Investigation memory storage records at minimum:

- memory reference ID;
- content hash;
- content size;
- source tool-call reference;
- content encoding; and
- optional source capability, source input/output hashes, execution status, and
  trace refs when supplied.

No wall-clock timestamp or host-local absolute path is stored in memory object
metadata.
