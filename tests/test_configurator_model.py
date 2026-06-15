"""Unit tests for the configurator metamodel data structures.

Covers :class:`ConfiguratorModel`, :class:`Question`, :class:`Option` and the
:data:`OptionStatus` enumeration defined in
``flamapy.metamodels.configurator_metamodel.models.configurator_model``.

The metamodel is a passive, stateful data structure: it holds questions and
options and exposes ``set_state`` as the single mutation entry point.  These
tests pin down that contract.
"""
from flamapy.metamodels.fm_metamodel.models.feature_model import Feature, FeatureType
from flamapy.metamodels.configurator_metamodel.models.configurator_model import (
    ConfiguratorModel,
    Option,
    OptionStatus,
    Question,
)


# ---------------------------------------------------------------------------
# OptionStatus enumeration
# ---------------------------------------------------------------------------

def test_option_status_members() -> None:
    """The enum must expose exactly the three documented states."""
    assert {s.name for s in OptionStatus} == {"SELECTED", "DESELECTED", "UNDECIDED"}


# ---------------------------------------------------------------------------
# Option
# ---------------------------------------------------------------------------

def test_option_initial_state() -> None:
    """A fresh option starts UNDECIDED with no value and keeps its feature ref."""
    feat = Feature("Salami", feature_type=FeatureType.BOOLEAN)
    option = Option(feat)
    assert option.name == "Salami"
    assert option.status is OptionStatus.UNDECIDED
    assert option.value is None
    assert option.feature is feat


def test_option_str_contains_name_status_and_value() -> None:
    option = Option(Feature("Big", feature_type=FeatureType.BOOLEAN))
    text = str(option)
    assert "Big" in text
    assert "UNDECIDED" in text


# ---------------------------------------------------------------------------
# Question
# ---------------------------------------------------------------------------

def test_question_initial_state() -> None:
    feat = Feature("Size", feature_type=FeatureType.BOOLEAN)
    question = Question(feat)
    assert question.name == "Size"
    assert question.options == []
    assert question.feature is feat


def test_question_add_option_appends() -> None:
    question = Question(Feature("Size", feature_type=FeatureType.BOOLEAN))
    opt_a = Option(Feature("Normal", feature_type=FeatureType.BOOLEAN))
    opt_b = Option(Feature("Big", feature_type=FeatureType.BOOLEAN))
    question.add_option(opt_a)
    question.add_option(opt_b)
    assert question.options == [opt_a, opt_b]


def test_question_str_contains_name() -> None:
    assert "Size" in str(Question(Feature("Size", feature_type=FeatureType.BOOLEAN)))


# ---------------------------------------------------------------------------
# ConfiguratorModel — construction / extension
# ---------------------------------------------------------------------------

def test_get_extension() -> None:
    assert ConfiguratorModel.get_extension() == "configurator_metamodel"


def test_initial_model_state() -> None:
    model = ConfiguratorModel()
    assert model.questions == []
    assert model.options_by_name == {}
    assert model.current_question_index == -1
    assert model.history == []
    assert model.solver_backend is None


# ---------------------------------------------------------------------------
# ConfiguratorModel — add_question / options_by_name index
# ---------------------------------------------------------------------------

def test_add_question_indexes_every_option(simple_model: ConfiguratorModel) -> None:
    assert "Child1" in simple_model.options_by_name
    assert "TypedFeat" in simple_model.options_by_name
    assert simple_model.options_by_name["Child1"].feature.name == "Child1"


def test_add_question_appends_to_questions_list() -> None:
    model = ConfiguratorModel()
    question = Question(Feature("Root", feature_type=FeatureType.BOOLEAN))
    model.add_question(question)
    assert model.questions == [question]


# ---------------------------------------------------------------------------
# ConfiguratorModel — set_state semantics
# ---------------------------------------------------------------------------

def test_set_state_true_marks_selected(simple_model: ConfiguratorModel) -> None:
    simple_model.set_state("Child1", True)
    option = simple_model.options_by_name["Child1"]
    assert option.status is OptionStatus.SELECTED
    assert option.value is True


def test_set_state_false_marks_deselected(simple_model: ConfiguratorModel) -> None:
    simple_model.set_state("Child1", False)
    option = simple_model.options_by_name["Child1"]
    assert option.status is OptionStatus.DESELECTED
    assert option.value is False


def test_set_state_typed_value_marks_selected(simple_model: ConfiguratorModel) -> None:
    """A non-bool, non-None value selects the option and stores the value."""
    simple_model.set_state("TypedFeat", 100)
    option = simple_model.options_by_name["TypedFeat"]
    assert option.status is OptionStatus.SELECTED
    assert option.value == 100


def test_set_state_none_resets_to_undecided(simple_model: ConfiguratorModel) -> None:
    simple_model.set_state("Child1", True)
    simple_model.set_state("Child1", None)
    option = simple_model.options_by_name["Child1"]
    assert option.status is OptionStatus.UNDECIDED
    assert option.value is None


def test_set_state_overwrites_existing_value(simple_model: ConfiguratorModel) -> None:
    """Re-assigning must update the value (needed for undo / re-configuration)."""
    simple_model.set_state("TypedFeat", 100)
    simple_model.set_state("TypedFeat", 50)
    assert simple_model.options_by_name["TypedFeat"].value == 50


def test_set_state_unknown_feature_is_silently_ignored(
    simple_model: ConfiguratorModel,
) -> None:
    """Unknown names (e.g. the abstract root) must not raise."""
    simple_model.set_state("NonExistent", True)  # must not raise
    assert "NonExistent" not in simple_model.options_by_name


def test_model_str_renders_questions(simple_model: ConfiguratorModel) -> None:
    # __str__ delegates to the questions list repr.
    assert str(simple_model) == str(simple_model.questions)
