"""QL consumer fencing and gated replacement startup for Product 4 role failover.

Directive C2905: Enforce epoch authorization, control-plane dedup, and credential
isolation for task admission and role replacement launches under RoleAuthority.
"""

from __future__ import annotations

import copy
import inspect
from typing import Any, Callable

from .role_failover import Fenced, RoleAuthority

__all__ = [
    "QLConsumerFencing",
    "Fenced",
    "reject_head_cred_inheritance",
]


def reject_head_cred_inheritance(payload: dict[str, Any], *, reject: bool = True) -> dict[str, Any]:
    """Strip or reject head credential material from payload.

    If reject is True and head credentials or tokens exist, raises ValueError.
    Otherwise returns a cleaned copy with head credentials and tokens stripped.
    """
    if not isinstance(payload, dict):
        return payload

    def _contains_head_cred(obj: Any) -> bool:
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k in ("head.cred", "head_cred", "head_token", "head.token", "cred"):
                    return True
                if k == "head" and isinstance(v, dict):
                    if any(sk in v for sk in ("cred", "token", "head.cred", "head_cred", "head_token", "head.token")):
                        return True
                if k == "token" and isinstance(v, str) and "head" in v.lower():
                    return True
                if isinstance(v, (dict, list)) and _contains_head_cred(v):
                    return True
        elif isinstance(obj, list):
            for item in obj:
                if isinstance(item, (dict, list)) and _contains_head_cred(item):
                    return True
        return False

    if _contains_head_cred(payload) and reject:
        raise ValueError("head_cred_inheritance_rejected: forbidden head credential inheritance in payload")

    def _strip_head_cred(obj: Any) -> Any:
        if isinstance(obj, dict):
            cleaned: dict[str, Any] = {}
            for k, v in obj.items():
                if k in ("head.cred", "head_cred", "head_token", "head.token", "cred"):
                    continue
                if k == "token" and isinstance(v, str) and "head" in v.lower():
                    continue
                if k == "head" and isinstance(v, dict):
                    cleaned[k] = {
                        sk: sv for sk, sv in v.items()
                        if sk not in ("cred", "token", "head.cred", "head_cred", "head_token", "head.token")
                    }
                elif isinstance(v, (dict, list)):
                    cleaned[k] = _strip_head_cred(v)
                else:
                    cleaned[k] = copy.deepcopy(v) if isinstance(v, list) else v
            return cleaned
        elif isinstance(obj, list):
            return [_strip_head_cred(item) for item in obj]
        return obj

    return _strip_head_cred(payload)


def _invoke_launcher(fn: Callable[..., Any], key: str, payload: dict[str, Any]) -> Any:
    try:
        sig = inspect.signature(fn)
        params = [
            p for p in sig.parameters.values()
            if p.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
        ]
        if len(params) == 1:
            return fn(payload)
    except Exception:
        pass
    return fn(key, payload)


class QLConsumerFencing:
    """Fenced task admission and gated replacement startup against RoleAuthority."""

    def __init__(self, authority: RoleAuthority) -> None:
        self.authority = authority

    @staticmethod
    def reject_head_cred_inheritance(payload: dict[str, Any], *, reject: bool = True) -> dict[str, Any]:
        return reject_head_cred_inheritance(payload, reject=reject)

    def admit_and_enqueue_task(
        self,
        project: str,
        role: str,
        actor: str,
        generation: str,
        epoch: int,
        task_id: str,
        payload: dict[str, Any],
        launcher_submit_fn: Callable[..., Any],
    ) -> dict[str, Any]:
        """Admit task under verified role epoch and enqueue via guarded_effect.

        Fails closed with Fenced if actor/epoch is stale.
        Rejects payload if head credentials or tokens are present.
        Deduplicates idempotent submission under f"ql-task:{project}:{role}:{epoch}:{task_id}".
        """
        # 1. Authorize holder and epoch
        if not self.authority.authorize(project, role, actor, generation, epoch):
            raise Fenced(f"Unauthorized: actor {actor} is not current holder for {project}:{role} at epoch {epoch}")

        # 2. Enforce head credential rejection
        sanitized_payload = self.reject_head_cred_inheritance(payload, reject=True)

        # 3. Guarded effect submission
        key = f"ql-task:{project}:{role}:{epoch}:{task_id}"
        outcome = self.authority.guarded_effect(
            project,
            role,
            actor,
            generation,
            epoch,
            key,
            sanitized_payload,
            lambda k, p: _invoke_launcher(launcher_submit_fn, k, p),
        )
        return outcome

    def validate_consumer_epoch(
        self,
        project: str,
        role: str,
        actor: str,
        generation: str,
        expected_epoch: int,
    ) -> bool:
        """Verify current epoch matches expected_epoch and actor/generation is current holder.

        Fails closed (returns False) on any mismatch, stale lease, suspicion, or missing role.
        """
        try:
            state = self.authority.role_state(project, role)
            if state.get("epoch") != expected_epoch:
                return False
            if (state.get("holder"), state.get("generation")) != (actor, generation):
                return False
            return bool(self.authority.authorize(project, role, actor, generation, expected_epoch))
        except (Fenced, ValueError, KeyError):
            return False

    def gated_replacement_startup(
        self,
        project: str,
        role: str,
        caller_actor: str,
        caller_gen: str,
        caller_epoch: int,
        replacement_plan: dict[str, Any],
        launcher_submit_fn: Callable[..., Any],
    ) -> dict[str, Any]:
        """Ensure replacement launch occurs exactly once per epoch with key f"ql-replace:{project}:{role}:{caller_epoch}".

        Fails closed if caller is stale or unactivated.
        """
        # 1. Authorize caller
        if not self.authority.authorize(project, role, caller_actor, caller_gen, caller_epoch):
            raise Fenced(
                f"Unauthorized: caller {caller_actor} is not current holder for {project}:{role} at epoch {caller_epoch}"
            )

        # 2. Fail closed if unactivated
        receipt = self.authority.activation(project, role, caller_actor, caller_gen, caller_epoch)
        if (
            not isinstance(receipt, dict)
            or receipt.get("state") == "pending_role_ack_and_first_action"
            or not receipt.get("role_ack")
            or not receipt.get("first_action")
        ):
            raise Fenced(f"caller {caller_actor} is unactivated at epoch {caller_epoch}: missing role ACK and first action")

        # 3. Enforce head credential rejection on replacement plan
        sanitized_plan = self.reject_head_cred_inheritance(replacement_plan, reject=True)

        # 4. Guarded effect submission ensuring exactly once per epoch
        key = f"ql-replace:{project}:{role}:{caller_epoch}"
        outcome = self.authority.guarded_effect(
            project,
            role,
            caller_actor,
            caller_gen,
            caller_epoch,
            key,
            sanitized_plan,
            lambda k, p: _invoke_launcher(launcher_submit_fn, k, p),
        )
        return outcome
