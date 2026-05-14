"""Single-tenant local monolith skeleton."""

from __future__ import annotations

from .config import LocalRuntimeConfig
from .phase import (
    ALERTFORGE_STATUS,
    BENCHMARK_STATUS,
    CUSTOMER_READINESS_STATUS,
    INVESTIGATION_MEMORY_STATUS,
    PHASE,
    RUNTIME_IMPLEMENTATION_STATUS,
)


class LocalMonolith:
    """Phase 1 skeleton for the future local monolith runtime.

    The skeleton reports planned and unavailable capabilities only. It does not
    ingest alerts, plan investigations, execute actions, assess findings, store
    investigation memory, retrieve memory ranges, generate proof packages, or
    import AlertForge scenarios.
    """

    def __init__(self, config: LocalRuntimeConfig | None = None) -> None:
        self.config = config or LocalRuntimeConfig()

    def planned_components(self) -> list[str]:
        """Return deterministic planned component names."""

        return [
            "local_monolith_process",
            "single_tenant_config",
            "offline_replay_boundary",
            "proof_package_boundary",
            "context_compaction_boundary",
        ]

    def not_implemented_components(self) -> list[str]:
        """Return deterministic future components absent from this skeleton."""

        return [
            "alertforge_ingest",
            "assessor_runtime",
            "benchmark_harness",
            "customer_readiness_workflow",
            "executor_runtime",
            "investigation_memory_retrieval",
            "investigation_memory_storage",
            "planner_runtime",
            "proof_package_generation",
            "sandbox_execute",
        ]

    def status(self) -> dict[str, object]:
        """Return deterministic skeleton status."""

        return {
            "phase": PHASE,
            "runtime_implementation_status": RUNTIME_IMPLEMENTATION_STATUS,
            "investigation_memory_status": INVESTIGATION_MEMORY_STATUS,
            "alertforge_status": ALERTFORGE_STATUS,
            "benchmark_status": BENCHMARK_STATUS,
            "customer_readiness_status": CUSTOMER_READINESS_STATUS,
            "config": self.config.as_dict(),
            "planned_components": self.planned_components(),
            "not_implemented_components": self.not_implemented_components(),
        }

    def doctor(self) -> dict[str, object]:
        """Return deterministic local skeleton diagnostics."""

        return {
            "phase": PHASE,
            "checks": [
                {
                    "name": "runtime_scope",
                    "status": "ok",
                    "detail": "skeleton-only",
                },
                {
                    "name": "live_integrations",
                    "status": "ok",
                    "detail": "not-configured",
                },
                {
                    "name": "generated_outputs",
                    "status": "ok",
                    "detail": "not-created-by-status-or-doctor",
                },
            ],
            "not_implemented_components": self.not_implemented_components(),
        }

