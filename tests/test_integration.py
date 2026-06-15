"""End-to-end integration tests for the configurator_metamodel plugin.

These exercise the full pipeline against the bundled UVL models with real
solvers:

    UVL file -> UVLReader -> FmToConfigurator -> Configure session

Unlike the unit tests, nothing is mocked here: PySAT (and, when installed, Z3)
perform the actual constraint propagation.  Z3 cases are skipped — not failed —
when the optional ``flamapy-z3`` plugin is absent.
"""
from typing import Any

import pytest

from flamapy.metamodels.fm_metamodel.transformations import UVLReader
from flamapy.metamodels.configurator_metamodel.operations.configure import Configure
from flamapy.metamodels.configurator_metamodel.transformation.fm_to_configurator import (
    FmToConfigurator,
)
from flamapy.metamodels.configurator_metamodel.transformation.fm_to_configurator_pre_order import (
    FmToConfiguratorPreOrder,
)

from tests.conftest import PIZZAS_TYPED_UVL, PIZZAS_UVL, requires_z3


def _value_for(feature_type_name: str) -> Any:
    """Pick a valid sample value for a given feature type."""
    return {"INTEGER": 1, "REAL": 1.0, "STRING": "test"}.get(feature_type_name, True)


def _run_session(operation: Configure, max_steps: int = 100) -> Configure:
    """Drive a session to completion by answering the first option of each question."""
    operation.start()
    steps = 0
    while not operation.is_finished() and steps < max_steps:
        status = operation.get_current_status()
        options = status["possibleOptions"]
        if options:
            first = options[0]
            type_name = getattr(first["featureType"], "name", str(first["featureType"]))
            operation.answer_question({first["name"]: _value_for(type_name)})
        operation.next_question()
        steps += 1
    return operation


# ---------------------------------------------------------------------------
# Full configuration runs
# ---------------------------------------------------------------------------

def test_full_run_pysat_inorder() -> None:
    fm = UVLReader(PIZZAS_UVL).transform()
    model = FmToConfigurator(fm, solver="pysat").transform()
    operation = _run_session(Configure().execute(model))
    assert operation.is_finished()


def test_full_run_pysat_preorder() -> None:
    fm = UVLReader(PIZZAS_UVL).transform()
    model = FmToConfiguratorPreOrder(fm, solver="pysat").transform()
    operation = _run_session(Configure().execute(model))
    assert operation.is_finished()


@requires_z3
@pytest.mark.parametrize("path", [PIZZAS_UVL, PIZZAS_TYPED_UVL])
def test_full_run_z3(path: str) -> None:
    fm = UVLReader(path).transform()
    model = FmToConfigurator(fm, solver="z3").transform()
    operation = _run_session(Configure().execute(model))
    assert operation.is_finished()


# ---------------------------------------------------------------------------
# Result reporting
# ---------------------------------------------------------------------------

def test_result_reports_core_features_selected() -> None:
    fm = UVLReader(PIZZAS_UVL).transform()
    model = FmToConfigurator(fm, solver="pysat").transform()
    operation = _run_session(Configure().execute(model))

    result = operation.get_result()
    # Mandatory (core) features must end up selected in any valid configuration.
    assert result["Topping"] is True
    assert result["Size"] is True
    assert result["Dough"] is True
    # Every option appears in the result mapping.
    assert {"Salami", "Normal", "Big", "Neapolitan", "CheesyCrust"} <= set(result)


# ---------------------------------------------------------------------------
# Constraint enforcement (cross-tree)
# ---------------------------------------------------------------------------

def test_contradiction_is_rejected_and_rolled_back() -> None:
    """CheesyCrust => Big: after picking Normal, CheesyCrust must be refused."""
    fm = UVLReader(PIZZAS_UVL).transform()
    model = FmToConfigurator(fm, solver="pysat").transform()
    operation = Configure().execute(model)
    operation.start()

    assert operation.answer_question({"Normal": True}) is True
    # Choosing Normal deselects Big; by contraposition the solver already forces
    # CheesyCrust to False (CheesyCrust => Big).  Re-asserting CheesyCrust = True
    # is therefore contradictory and must be rejected.
    assert operation.answer_question({"CheesyCrust": True}) is False
    # The rejected answer leaves the model in its previous, consistent state:
    # the user's choice (Normal) survives and CheesyCrust is not selected.
    assert model.options_by_name["Normal"].status.name == "SELECTED"
    assert model.options_by_name["CheesyCrust"].status.name != "SELECTED"


# ---------------------------------------------------------------------------
# Navigation / undo
# ---------------------------------------------------------------------------

def test_previous_question_returns_to_earlier_step() -> None:
    fm = UVLReader(PIZZAS_UVL).transform()
    model = FmToConfigurator(fm, solver="pysat").transform()
    operation = Configure().execute(model)
    operation.start()

    first_index = model.current_question_index
    status = operation.get_current_status()
    first_option = status["possibleOptions"][0]["name"]
    operation.answer_question({first_option: True})
    operation.next_question()
    assert model.current_question_index > first_index

    assert operation.previous_question() is True
    assert model.current_question_index == first_index
