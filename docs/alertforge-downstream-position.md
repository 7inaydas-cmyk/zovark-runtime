# AlertForge Downstream Position

Status: future integration boundary.

AlertForge is a future upstream synthetic alert/scenario generator. It is not
implemented in this repository and no output contract or ingest path exists in
Phase 0.

Before integration, a future PR must define:

- AlertForge output contract;
- unsafe-field rejection rules;
- deterministic fixture handling;
- proof/Replay expectations; and
- leak checks for prompts, tool arguments, tool outputs, payload bodies,
  messages, notes, hidden reasoning, and chain-of-thought.

