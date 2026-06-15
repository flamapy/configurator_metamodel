"""Unit tests for the :class:`Configure` operation.

``Configure`` is the façade that drives an interactive session: navigation
between questions, applying answers, constraint propagation (delegated to the
solver backend), undo, and status reporting.

The solver backend is replaced by a ``MagicMock`` so these tests isolate the
operation's own logic from any real SAT/SMT engine.  End-to-end behaviour with
real solvers lives in ``test_integration.py``.
"""
from unittest.mock import MagicMock

from flamapy.metamodels.fm_metamodel.models.feature_model import FeatureType
from flamapy.metamodels.configurator_metamodel.models.configurator_model import (
    ConfiguratorModel,
    Option,
    OptionStatus,
    Question,
)
from flamapy.metamodels.configurator_metamodel.operations.configure import Configure

from tests._helpers import alternative, feature, mandatory, optional, or_group


# ---------------------------------------------------------------------------
# Local builders
# ---------------------------------------------------------------------------

def _model_with(*questions: Question) -> ConfiguratorModel:
    """Wrap pre-built questions in a model with a mock (no-op) backend."""
    model = ConfiguratorModel()
    for question in questions:
        model.add_question(question)
    backend = MagicMock()
    backend.propagate.return_value = {}
    model.solver_backend = backend
    return model


def _configure(model: ConfiguratorModel, index: int = 0) -> Configure:
    model.current_question_index = index
    operation = Configure()
    operation.execute(model)
    return operation


# ---------------------------------------------------------------------------
# execute / model binding
# ---------------------------------------------------------------------------

def test_execute_binds_model_and_returns_self(simple_model: ConfiguratorModel) -> None:
    operation = Configure()
    returned = operation.execute(simple_model)
    assert returned is operation
    assert operation.configurator_model is simple_model


# ---------------------------------------------------------------------------
# Decisions / configuration snapshots
# ---------------------------------------------------------------------------

def test_get_decisions_only_includes_decided_options(
    mock_configure: Configure, simple_model: ConfiguratorModel
) -> None:
    simple_model.set_state("Child1", True)
    simple_model.set_state("TypedFeat", 7)
    decisions = mock_configure._get_decisions()
    assert decisions == {"Child1": True, "TypedFeat": 7}


def test_get_decisions_maps_deselected_to_false(
    mock_configure: Configure, simple_model: ConfiguratorModel
) -> None:
    simple_model.set_state("Child1", False)
    assert mock_configure._get_decisions() == {"Child1": False}


def test_get_result_includes_undecided_as_none(
    mock_configure: Configure, simple_model: ConfiguratorModel
) -> None:
    simple_model.set_state("Child1", True)
    result = mock_configure.get_result()
    assert result["Child1"] is True
    assert result["TypedFeat"] is None  # undecided surfaces as None


# ---------------------------------------------------------------------------
# answer_question
# ---------------------------------------------------------------------------

def test_answer_question_success(
    mock_configure: Configure, simple_model: ConfiguratorModel
) -> None:
    assert mock_configure.answer_question({"TypedFeat": 42}) is True
    option = simple_model.options_by_name["TypedFeat"]
    assert option.value == 42
    assert option.status is OptionStatus.SELECTED


def test_answer_question_records_history_before_applying(
    mock_configure: Configure, simple_model: ConfiguratorModel
) -> None:
    mock_configure.answer_question({"TypedFeat": 42})
    # The snapshot was taken before the change, so the recorded value is None.
    assert simple_model.history[-1]["TypedFeat"] is None


def test_answer_question_applies_implied_features(
    mock_configure: Configure, simple_model: ConfiguratorModel
) -> None:
    """Features returned by the backend are applied to the model."""
    simple_model.solver_backend.propagate.return_value = {"Child1": True}
    mock_configure.answer_question({"TypedFeat": 5})
    assert simple_model.options_by_name["Child1"].status is OptionStatus.SELECTED


def test_answer_question_contradiction_rolls_back(
    mock_configure: Configure, simple_model: ConfiguratorModel
) -> None:
    """An UNSAT answer (backend returns None) is reverted and reports False."""
    simple_model.solver_backend.propagate.return_value = None
    simple_model.set_state("TypedFeat", 10)

    success = mock_configure.answer_question({"TypedFeat": 99})

    assert success is False
    assert simple_model.options_by_name["TypedFeat"].value == 10


def test_answer_question_on_last_question_advances_to_finished(
    mock_configure: Configure, simple_model: ConfiguratorModel
) -> None:
    """Answering the final question moves the index past the end."""
    assert mock_configure.is_last_question()
    mock_configure.answer_question({"TypedFeat": 1})
    assert mock_configure.is_finished()


def test_answer_question_marks_parent_feature_selected() -> None:
    """When the current question's parent is itself an option, it is selected."""
    root = feature("Topping")
    child = feature("Salami")
    optional(root, child)
    question = Question(root)
    question.add_option(Option(child))

    model = _model_with(question)
    # Register the parent as if it were an option of a higher-level question.
    model.options_by_name["Topping"] = Option(root)
    operation = _configure(model, index=0)

    operation.answer_question({"Salami": True})

    assert model.options_by_name["Topping"].status is OptionStatus.SELECTED


# ---------------------------------------------------------------------------
# undo_answer
# ---------------------------------------------------------------------------

def test_undo_restores_previous_configuration(
    mock_configure: Configure, simple_model: ConfiguratorModel
) -> None:
    simple_model.set_state("TypedFeat", 10)
    simple_model.history.append({"TypedFeat": 10, "Child1": None})
    simple_model.set_state("TypedFeat", 99)

    assert mock_configure.undo_answer() is True
    assert simple_model.options_by_name["TypedFeat"].value == 10


def test_undo_with_empty_history_returns_false(mock_configure: Configure) -> None:
    assert mock_configure.undo_answer() is False


# ---------------------------------------------------------------------------
# Navigation helpers
# ---------------------------------------------------------------------------

def test_is_first_question(mock_configure: Configure, simple_model: ConfiguratorModel) -> None:
    simple_model.current_question_index = 0
    assert mock_configure.is_first_question()


def test_is_last_question(mock_configure: Configure, simple_model: ConfiguratorModel) -> None:
    simple_model.current_question_index = len(simple_model.questions) - 1
    assert mock_configure.is_last_question()


def test_is_finished(mock_configure: Configure, simple_model: ConfiguratorModel) -> None:
    simple_model.current_question_index = len(simple_model.questions)
    assert mock_configure.is_finished()


def test_next_question_skips_fully_resolved_questions() -> None:
    """A question whose options are already decided must be skipped."""
    # Q0: single boolean option, already selected -> no remaining choice.
    root0 = feature("Group0")
    child0 = feature("A")
    optional(root0, child0)
    q0 = Question(root0)
    q0.add_option(Option(child0))

    # Q1: single optional boolean option, undecided -> needs an answer.
    root1 = feature("Group1")
    child1 = feature("B")
    optional(root1, child1)
    q1 = Question(root1)
    q1.add_option(Option(child1))

    model = _model_with(q0, q1)
    model.set_state("A", True)  # resolve Q0's only option
    operation = _configure(model, index=-1)

    assert operation.next_question() is True
    assert model.current_question_index == 1  # skipped Q0


def test_next_question_returns_false_at_last_question() -> None:
    root = feature("Group")
    child = feature("A")
    optional(root, child)
    question = Question(root)
    question.add_option(Option(child))

    model = _model_with(question)
    operation = _configure(model, index=0)

    assert operation.next_question() is False


def test_previous_question_undoes_and_moves_back() -> None:
    root0 = feature("Group0")
    child0 = feature("A")
    optional(root0, child0)
    q0 = Question(root0)
    q0.add_option(Option(child0))

    root1 = feature("Group1")
    child1 = feature("B")
    optional(root1, child1)
    q1 = Question(root1)
    q1.add_option(Option(child1))

    model = _model_with(q0, q1)
    model.history.append({"A": None, "B": None})  # snapshot to undo into
    operation = _configure(model, index=1)

    assert operation.previous_question() is True
    assert model.current_question_index == 0


# ---------------------------------------------------------------------------
# get_possible_options filtering
# ---------------------------------------------------------------------------

def test_get_possible_options_filters_mandatory_boolean() -> None:
    """Mandatory boolean options are hidden; optional and typed ones remain."""
    parent = feature("Parent")
    opt_bool = feature("OptBool")
    mand_bool = feature("MandBool")
    mand_int = feature("MandInt", FeatureType.INTEGER)
    optional(parent, opt_bool)
    mandatory(parent, mand_bool)
    mandatory(parent, mand_int)

    question = Question(parent)
    for child in (opt_bool, mand_bool, mand_int):
        question.add_option(Option(child))

    model = _model_with(question)
    operation = _configure(model, index=0)

    names = {opt.name for opt in operation.get_possible_options()}
    assert names == {"OptBool", "MandInt"}
    assert "MandBool" not in names  # mandatory + boolean is auto-selected


def test_get_possible_options_excludes_already_decided() -> None:
    parent = feature("Parent")
    opt_a = feature("A")
    opt_b = feature("B")
    optional(parent, opt_a)
    optional(parent, opt_b)
    question = Question(parent)
    question.add_option(Option(opt_a))
    question.add_option(Option(opt_b))

    model = _model_with(question)
    model.set_state("A", True)  # decided -> should drop out
    operation = _configure(model, index=0)

    names = {opt.name for opt in operation.get_possible_options()}
    assert names == {"B"}


# ---------------------------------------------------------------------------
# get_current_question_type
# ---------------------------------------------------------------------------

def test_question_type_alternative() -> None:
    parent = feature("Size")
    alternative(parent, [feature("Normal"), feature("Big")])
    operation = _configure(_model_with(Question(parent)), index=0)
    assert operation.get_current_question_type() == "alternative"


def test_question_type_or() -> None:
    parent = feature("Topping")
    or_group(parent, [feature("Salami"), feature("Ham"), feature("Mozzarella")])
    operation = _configure(_model_with(Question(parent)), index=0)
    assert operation.get_current_question_type() == "or"


def test_question_type_optional_fallback() -> None:
    parent = feature("Pizza")
    optional(parent, feature("CheesyCrust"))
    operation = _configure(_model_with(Question(parent)), index=0)
    assert operation.get_current_question_type() == "optional"


# ---------------------------------------------------------------------------
# get_current_status
# ---------------------------------------------------------------------------

def test_get_current_status_shape(mock_configure: Configure) -> None:
    status = mock_configure.get_current_status()
    for key in (
        "currentQuestion",
        "currentQuestionType",
        "currentQuestionIndex",
        "isLastQuestion",
        "possibleOptions",
    ):
        assert key in status, f"missing key: {key}"
    assert isinstance(status["possibleOptions"], list)


def test_get_current_status_option_entries(mock_configure: Configure) -> None:
    status = mock_configure.get_current_status()
    for entry in status["possibleOptions"]:
        assert set(entry) == {"id", "name", "featureType"}
        assert isinstance(entry["featureType"], FeatureType)
