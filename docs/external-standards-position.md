# External Standards Position

Status: documentation only. This file does not implement OCSF, SIEM, EDR,
vendor schema mapping, ingest, export, or runtime behavior.

## OCSF

OCSF is not implemented in `zovark-runtime`.

OCSF may be considered later as a mapping, export, or import surface. It must
not silently become the canonical Zovark schema for Replay, audit, storage,
verdicts, or customer evidence.

Zovark-owned contracts remain canonical unless a future INV-027-compatible
governance decision says otherwise.

## Vendor Schemas

SIEM, EDR, and other vendor formats are mapping/export surfaces only. No vendor
or proprietary schema dependency is canonical in the runtime repository.

Future vendor mapping work must preserve:

- Zovark-owned canonical contracts;
- offline Replay boundaries;
- no raw prompt, tool output, payload, message, note, or hidden reasoning
  leakage;
- explicit valid/invalid fixtures before runtime enforcement claims; and
- INV-027 schema-boundary governance.

## Current Status

No OCSF code, schema, mapper, exporter, importer, or ingest path exists in
`zovark-runtime`.
