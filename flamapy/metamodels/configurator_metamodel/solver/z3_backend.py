import logging
from typing import Any, Optional

import z3

from flamapy.metamodels.fm_metamodel.models.feature_model import FeatureType
from flamapy.metamodels.z3_metamodel.models.z3_model import Z3Model

LOGGER = logging.getLogger(__name__)


class Z3Backend:
    """Solver backend powered by Z3 SMT solver.

    Supports all UVL feature types: BOOLEAN, INTEGER, REAL, STRING.

    For boolean features, propagation detects features that are *forced*
    (selecting or deselecting them would be UNSAT given current decisions).
    For typed features, the selection status is propagated the same way;
    concrete values are not propagated — the user must supply them when the
    question is reached.
    """

    def __init__(self, z3_model: Z3Model) -> None:
        self._z3_model = z3_model
        self._solver = z3.Solver(ctx=z3_model.ctx)
        self._solver.add(z3_model.constraints)

    def propagate(self, decisions: dict[str, Any]) -> Optional[dict[str, Any]]:
        """Check satisfiability and return forced features.

        Builds Z3 assumptions from *decisions*, calls ``solver.check()``, then
        for each undecided feature tests whether forcing it in either direction
        would be UNSAT (backbone detection).
        """
        assumptions = self._build_assumptions(decisions)

        if self._solver.check(*assumptions) != z3.sat:
            return None

        implied: dict[str, Any] = {}
        for name, fi in self._z3_model.features.items():
            if name in decisions:
                continue
            if self._solver.check(*assumptions, z3.Not(fi.sel)) == z3.unsat:
                implied[name] = True
            elif self._solver.check(*assumptions, fi.sel) == z3.unsat:
                implied[name] = False

        return implied

    def _build_assumptions(self, decisions: dict[str, Any]) -> list[Any]:
        """Translate ``{name: value}`` decisions into Z3 Boolean expressions."""
        ctx = self._z3_model.ctx
        assumptions: list[Any] = []
        for name, value in decisions.items():
            fi = self._z3_model.features.get(name)
            if fi is None:
                LOGGER.debug("Feature '%s' not in Z3 model — skipped.", name)
                continue
            if value is False:
                assumptions.append(fi.sel == z3.BoolVal(False, ctx=ctx))
            else:
                assumptions.append(fi.sel == z3.BoolVal(True, ctx=ctx))
                # For typed features with a concrete value, also pin the value
                if (
                    fi.ftype != FeatureType.BOOLEAN
                    and value is not True
                    and value is not None
                    and fi.val is not None
                ):
                    z3_val = Z3Model.get_z3_value(value, fi.ftype, ctx)
                    assumptions.append(fi.val == z3_val)
        return assumptions
