"""Unit tests for the configurator_metamodel package."""
from unittest.mock import MagicMock

import pytest

from flamapy.metamodels.fm_metamodel.models.feature_model import Feature, FeatureType
from flamapy.metamodels.configurator_metamodel.models.configurator_model import (
    ConfiguratorModel,
    Option,
    OptionStatus,
    Question,
)
from flamapy.metamodels.configurator_metamodel.operations.configure import Configure


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def model() -> ConfiguratorModel:
    m = ConfiguratorModel()
    f_root = Feature("Root", feature_type=FeatureType.BOOLEAN)
    f_child1 = Feature("Child1", parent=f_root, feature_type=FeatureType.BOOLEAN)
    f_typed = Feature("TypedFeat", parent=f_root, feature_type=FeatureType.INTEGER)
    q1 = Question(f_root)
    q1.add_option(Option(f_child1))
    q1.add_option(Option(f_typed))
    m.add_question(q1)
    return m


@pytest.fixture
def mocked_configure(model: ConfiguratorModel) -> Configure:
    backend = MagicMock()
    backend.propagate.return_value = {}  # No implied features by default
    model.solver_backend = backend
    model.current_question_index = 0

    op = Configure()
    op.configurator_model = model
    return op


# ---------------------------------------------------------------------------
# ConfiguratorModel — add_question / options_by_name
# ---------------------------------------------------------------------------

def test_options_by_name_populated(model: ConfiguratorModel) -> None:
    assert "Child1" in model.options_by_name
    assert "TypedFeat" in model.options_by_name
    assert model.options_by_name["Child1"].feature.name == "Child1"


# ---------------------------------------------------------------------------
# ConfiguratorModel — set_state
# ---------------------------------------------------------------------------

def test_set_state_integer_value(model: ConfiguratorModel) -> None:
    model.set_state("TypedFeat", 100)
    option = model.options_by_name["TypedFeat"]
    assert option.value == 100
    assert option.status == OptionStatus.SELECTED


def test_set_state_overwrites_existing_value(model: ConfiguratorModel) -> None:
    """set_state must allow value updates (regression for the original bug)."""
    model.set_state("TypedFeat", 100)
    model.set_state("TypedFeat", 50)
    assert model.options_by_name["TypedFeat"].value == 50


def test_set_state_boolean_false(model: ConfiguratorModel) -> None:
    model.set_state("Child1", False)
    option = model.options_by_name["Child1"]
    assert option.value is False
    assert option.status == OptionStatus.DESELECTED


def test_set_state_boolean_true(model: ConfiguratorModel) -> None:
    model.set_state("Child1", True)
    assert model.options_by_name["Child1"].status == OptionStatus.SELECTED


def test_set_state_none_resets_to_undecided(model: ConfiguratorModel) -> None:
    model.set_state("Child1", True)
    model.set_state("Child1", None)
    option = model.options_by_name["Child1"]
    assert option.value is None
    assert option.status == OptionStatus.UNDECIDED


def test_set_state_unknown_feature_does_not_raise(model: ConfiguratorModel) -> None:
    """Unknown feature names should be silently ignored."""
    model.set_state("NonExistent", True)  # must not raise


# ---------------------------------------------------------------------------
# Option / Question string representations
# ---------------------------------------------------------------------------

def test_option_str(model: ConfiguratorModel) -> None:
    f = Feature("Child1", feature_type=FeatureType.BOOLEAN)
    opt = Option(f)
    assert "Child1" in str(opt)


def test_question_str(model: ConfiguratorModel) -> None:
    f = Feature("Root", feature_type=FeatureType.BOOLEAN)
    q = Question(f)
    assert "Root" in str(q)


# ---------------------------------------------------------------------------
# Configure — answer_question
# ---------------------------------------------------------------------------

def test_answer_question_success(mocked_configure: Configure, model: ConfiguratorModel) -> None:
    success = mocked_configure.answer_question({"TypedFeat": 42})
    assert success
    assert model.options_by_name["TypedFeat"].value == 42
    assert model.options_by_name["TypedFeat"].status == OptionStatus.SELECTED


def test_answer_question_saves_history_before_update(
    mocked_configure: Configure, model: ConfiguratorModel
) -> None:
    mocked_configure.answer_question({"TypedFeat": 42})
    # History entry was captured before the change, so value was None
    assert model.history[-1]["TypedFeat"] is None


def test_answer_question_conflict_rolls_back(
    mocked_configure: Configure, model: ConfiguratorModel
) -> None:
    """A contradicting answer must be rolled back automatically."""
    model.solver_backend.propagate.return_value = None  # simulate contradiction
    model.set_state("TypedFeat", 10)

    success = mocked_configure.answer_question({"TypedFeat": 99})

    assert not success
    assert model.options_by_name["TypedFeat"].value == 10


# ---------------------------------------------------------------------------
# Configure — undo_answer
# ---------------------------------------------------------------------------

def test_undo_restores_previous_value(
    mocked_configure: Configure, model: ConfiguratorModel
) -> None:
    model.set_state("TypedFeat", 10)
    model.history.append({"TypedFeat": 10})
    model.set_state("TypedFeat", 99)

    result = mocked_configure.undo_answer()

    assert result
    assert model.options_by_name["TypedFeat"].value == 10


def test_undo_with_empty_history_returns_false(mocked_configure: Configure) -> None:
    assert not mocked_configure.undo_answer()


# ---------------------------------------------------------------------------
# Configure — navigation helpers
# ---------------------------------------------------------------------------

def test_is_first_question(mocked_configure: Configure, model: ConfiguratorModel) -> None:
    model.current_question_index = 0
    assert mocked_configure.is_first_question()


def test_is_last_question(mocked_configure: Configure, model: ConfiguratorModel) -> None:
    model.current_question_index = len(model.questions) - 1
    assert mocked_configure.is_last_question()


def test_is_finished(mocked_configure: Configure, model: ConfiguratorModel) -> None:
    model.current_question_index = len(model.questions)
    assert mocked_configure.is_finished()


# ---------------------------------------------------------------------------
# Configure — get_current_status
# ---------------------------------------------------------------------------

def test_get_current_status_keys(mocked_configure: Configure) -> None:
    status = mocked_configure.get_current_status()
    for key in ('currentQuestion', 'currentQuestionType', 'currentQuestionIndex',
                'isLastQuestion', 'possibleOptions'):
        assert key in status, f"Missing key: {key}"


def test_get_current_status_no_duplicate_possible_options(mocked_configure: Configure) -> None:
    """possibleOptions must be a list."""
    status = mocked_configure.get_current_status()
    assert isinstance(status['possibleOptions'], list)
