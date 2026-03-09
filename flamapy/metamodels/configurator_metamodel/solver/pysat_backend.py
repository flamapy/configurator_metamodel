import logging
from typing import Any, Optional

from flamapy.metamodels.pysat_metamodel.models.pysat_model import PySATModel
from pysat.solvers import Solver

LOGGER = logging.getLogger(__name__)

_DEFAULT_SOLVER = 'glucose3'


class PySATBackend:
    """Solver backend powered by PySAT (glucose3 SAT solver).

    Supports boolean feature selection.  Typed features (INTEGER, REAL, STRING)
    are tracked as boolean selected/deselected; their concrete values are not
    propagated since CNF has no notion of typed arithmetic.
    """

    def __init__(self, pysat_model: PySATModel) -> None:
        self._model = pysat_model
        self._solver: Solver = Solver(name=_DEFAULT_SOLVER)
        for clause in pysat_model.get_all_clauses():
            self._solver.add_clause(clause)

    def propagate(self, decisions: dict[str, Any]) -> Optional[dict[str, Any]]:
        """Run PySAT unit propagation on the current decisions.

        Converts ``{name: value}`` decisions to integer SAT literals, calls
        ``solver.propagate()``, and maps the implied literals back to feature
        names.
        """
        variables = self._model.variables
        assumptions: list[int] = []
        for name, value in decisions.items():
            var = variables.get(name)
            if var is None:
                LOGGER.debug("Feature '%s' not in PySAT variables — skipped.", name)
                continue
            assumptions.append(-var if value is False else var)

        status, implied_lits = self._solver.propagate(assumptions=assumptions)
        if not status:
            return None

        features = self._model.features
        return {
            features[abs(lit)]: lit > 0
            for lit in implied_lits
            if abs(lit) in features
        }
