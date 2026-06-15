"""Unit tests for the solver backends and the SolverBackend protocol.

The backends are the only components that talk to a real solver:

* :class:`PySATBackend` — boolean unit propagation via Glucose3 (always
  available).
* :class:`Z3Backend` — SMT-based backbone detection with typed-value support
  (requires the optional ``flamapy-z3`` plugin; those tests are skipped when it
  is not installed).

Both must honour the same contract: return a dict of implied features when the
decisions are satisfiable, or ``None`` when they are contradictory (UNSAT).
"""
import pytest

from flamapy.metamodels.fm_metamodel.transformations import UVLReader
from flamapy.metamodels.pysat_metamodel.transformations.fm_to_pysat import FmToPysat
from flamapy.metamodels.configurator_metamodel.solver.backend import SolverBackend
from flamapy.metamodels.configurator_metamodel.solver.pysat_backend import PySATBackend

from tests.conftest import PIZZAS_TYPED_UVL, PIZZAS_UVL, requires_z3


# ---------------------------------------------------------------------------
# Backend fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def pysat_backend() -> PySATBackend:
    fm = UVLReader(PIZZAS_UVL).transform()
    transformation = FmToPysat(fm)
    transformation.transform()
    return PySATBackend(transformation.destination_model)


@pytest.fixture
def z3_backend():  # type: ignore[no-untyped-def]
    from flamapy.metamodels.z3_metamodel.transformations.fm_to_z3 import FmToZ3
    from flamapy.metamodels.configurator_metamodel.solver.z3_backend import Z3Backend

    fm = UVLReader(PIZZAS_TYPED_UVL).transform()
    return Z3Backend(FmToZ3(fm).transform())


# ---------------------------------------------------------------------------
# SolverBackend protocol
# ---------------------------------------------------------------------------

def test_pysat_backend_satisfies_protocol(pysat_backend: PySATBackend) -> None:
    assert isinstance(pysat_backend, SolverBackend)


def test_object_without_propagate_is_not_a_backend() -> None:
    class NotABackend:
        pass

    assert not isinstance(NotABackend(), SolverBackend)


def test_duck_typed_object_satisfies_protocol() -> None:
    class DuckBackend:
        def propagate(self, decisions):  # noqa: ANN001, ANN201
            return {}

    assert isinstance(DuckBackend(), SolverBackend)


# ---------------------------------------------------------------------------
# PySATBackend.propagate
# ---------------------------------------------------------------------------

def test_pysat_empty_decisions_are_satisfiable(pysat_backend: PySATBackend) -> None:
    assert pysat_backend.propagate({}) is not None


def test_pysat_contradiction_returns_none(pysat_backend: PySATBackend) -> None:
    """Selecting both members of an alternative group is UNSAT."""
    assert pysat_backend.propagate({"Normal": True, "Big": True}) is None


def test_pysat_cross_tree_constraint_is_propagated(pysat_backend: PySATBackend) -> None:
    """CheesyCrust => Big, so choosing CheesyCrust forces Big and rules out Normal."""
    implied = pysat_backend.propagate({"CheesyCrust": True})
    assert implied is not None
    assert implied["Big"] is True
    assert implied["Normal"] is False


def test_pysat_unknown_feature_is_skipped(pysat_backend: PySATBackend) -> None:
    """Unknown names are ignored rather than raising."""
    assert pysat_backend.propagate({"DoesNotExist": True}) is not None


# ---------------------------------------------------------------------------
# Z3Backend.propagate (optional dependency)
# ---------------------------------------------------------------------------

@requires_z3
def test_z3_empty_decisions_are_satisfiable(z3_backend) -> None:  # type: ignore[no-untyped-def]
    assert z3_backend.propagate({}) is not None


@requires_z3
def test_z3_contradiction_returns_none(z3_backend) -> None:  # type: ignore[no-untyped-def]
    assert z3_backend.propagate({"Normal": True, "Big": True}) is None


@requires_z3
def test_z3_typed_value_within_range_is_satisfiable(z3_backend) -> None:  # type: ignore[no-untyped-def]
    """SpicyLevel is constrained to [1, 5]; a value of 3 is valid."""
    assert z3_backend.propagate({"SpicyLevel": 3}) is not None


@requires_z3
def test_z3_typed_value_out_of_range_returns_none(z3_backend) -> None:  # type: ignore[no-untyped-def]
    """A value of 10 violates SpicyLevel <= 5 and must be reported as UNSAT."""
    assert z3_backend.propagate({"SpicyLevel": 10}) is None
