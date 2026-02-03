"""Debug bundle builder for /v1/debug/asset_targeting/{cluster_id}."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from .schemas import AllocationResult, ClusterPacket, ChannelInferResult, SectorMapResult, TickerSelectResult


@dataclass
class DebugBundle:
    packet: Dict[str, Any]
    call_a: Dict[str, Any]
    call_b: Dict[str, Any]
    call_c: Dict[str, Any]
    allocation: Dict[str, Any]
    diagnostics: Dict[str, Any]


def build_debug_bundle(
    *,
    packet: ClusterPacket,
    call_a: ChannelInferResult,
    call_b: SectorMapResult,
    call_c: TickerSelectResult,
    allocation: AllocationResult,
) -> DebugBundle:
    return DebugBundle(
        packet=packet.model_dump(),
        call_a=call_a.model_dump(),
        call_b=call_b.model_dump(),
        call_c=call_c.model_dump(),
        allocation=allocation.model_dump(),
        diagnostics=allocation.diagnostics,
    )
