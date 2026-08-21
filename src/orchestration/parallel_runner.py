"""Run extraction agents concurrently and capture timing evidence."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
from time import perf_counter

from config.settings import Settings, load_settings
from src.agents.account_agent import extract_account_metadata
from src.agents.identity_agent import extract_customer_identity
from src.agents.transaction_agent import extract_transaction_table
from src.models.schemas import AccountMetadata, CustomerIdentity, TransactionTable


@dataclass(frozen=True)
class AgentTiming:
    """Timing details for one agent run."""

    agent_name: str
    started_at: str
    ended_at: str
    duration_seconds: float


@dataclass(frozen=True)
class ParallelExtractionResult:
    """Fork/join result for the three extraction agents."""

    account_metadata: AccountMetadata
    customer_identity: CustomerIdentity
    transaction_table: TransactionTable
    prompt_versions: dict[str, str]
    timings: list[AgentTiming]


async def _run_single_agent(agent_name: str, fn, *args, **kwargs):
    started = datetime.now(UTC)
    start_perf = perf_counter()
    result = await asyncio.to_thread(fn, *args, **kwargs)
    ended = datetime.now(UTC)
    duration = perf_counter() - start_perf

    timing = AgentTiming(
        agent_name=agent_name,
        started_at=started.isoformat(),
        ended_at=ended.isoformat(),
        duration_seconds=round(duration, 4),
    )
    return result, timing


async def run_parallel_extraction(
    document_text: str,
    memory_context: str = "",
    settings: Settings | None = None,
) -> ParallelExtractionResult:
    """Run account, identity, and transaction extraction concurrently."""
    runtime_settings = settings or load_settings()

    tasks = [
        _run_single_agent(
            "account_metadata",
            extract_account_metadata,
            document_text,
            memory_context,
            runtime_settings,
        ),
        _run_single_agent(
            "customer_identity",
            extract_customer_identity,
            document_text,
            memory_context,
            runtime_settings,
        ),
        _run_single_agent(
            "transaction_table",
            extract_transaction_table,
            document_text,
            memory_context,
            runtime_settings,
        ),
    ]

    results = await asyncio.gather(*tasks)

    outputs: dict[str, object] = {}
    versions: dict[str, str] = {}
    timings: list[AgentTiming] = []

    for (payload, prompt_version), timing in results:
        outputs[timing.agent_name] = payload
        versions[timing.agent_name] = prompt_version
        timings.append(timing)

    return ParallelExtractionResult(
        account_metadata=outputs["account_metadata"],
        customer_identity=outputs["customer_identity"],
        transaction_table=outputs["transaction_table"],
        prompt_versions=versions,
        timings=timings,
    )
