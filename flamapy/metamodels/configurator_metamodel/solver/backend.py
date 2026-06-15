from typing import Any, Optional, runtime_checkable
from typing import Protocol


@runtime_checkable
class SolverBackend(Protocol):
    """Protocol that every solver backend must satisfy to work with Configure.

    Implementations translate the name-based decision dict into solver-specific
    calls and return any additionally implied feature values.
    """

    def propagate(self, decisions: dict[str, Any]) -> Optional[dict[str, Any]]:
        """Check consistency and return forced features.

        Args:
            decisions: Current partial configuration as ``{feature_name: value}``.
                ``True`` (or any non-``False``) means the feature is selected;
                ``False`` means deselected.

        Returns:
            A dict of additionally forced ``{feature_name: value}`` entries that
            follow from the given decisions, or ``None`` if the decisions are
            contradictory (UNSAT).
        """
        ...
