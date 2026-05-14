# Replay Compatibility

Status: future implementation guidance.

Replay compatibility is a required boundary for later runtime work. Replay must
never call live systems.

Future runtime proof artifacts should record:

- contract version;
- memory reference IDs;
- content hashes;
- envelope hashes;
- returned ranges;
- byte counts;
- retrieval request and result references; and
- whether the model saw an envelope or a bounded retrieval result.

Phase 0 does not implement Replay verification in this repository.

