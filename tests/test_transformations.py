"""Unit tests for the FeatureModel -> ConfiguratorModel transformers.

Two transformers exist, differing only in the order they emit questions:

* :class:`FmToConfigurator` — in-order traversal.
* :class:`FmToConfiguratorPreOrder` — pre-order traversal.

These tests use the real ``Pizzas.uvl`` model and assert the documented
question ordering (see ARCHITECTURE.md §5.3), the structural invariants common
to both transformers, and the pre-selection of core features.
"""
from flamapy.metamodels.fm_metamodel.transformations import UVLReader
from flamapy.metamodels.configurator_metamodel.models.configurator_model import OptionStatus
from flamapy.metamodels.configurator_metamodel.solver.pysat_backend import PySATBackend
from flamapy.metamodels.configurator_metamodel.transformation.fm_to_configurator import (
    FmToConfigurator,
)
from flamapy.metamodels.configurator_metamodel.transformation.fm_to_configurator_pre_order import (
    FmToConfiguratorPreOrder,
)

from tests.conftest import PIZZAS_UVL


# ---------------------------------------------------------------------------
# Extension metadata
# ---------------------------------------------------------------------------

def test_inorder_extensions() -> None:
    assert FmToConfigurator.get_source_extension() == "fm"
    assert FmToConfigurator.get_destination_extension() == "configurator_metamodel"


def test_preorder_extensions() -> None:
    assert FmToConfiguratorPreOrder.get_source_extension() == "fm"
    assert FmToConfiguratorPreOrder.get_destination_extension() == "configurator_metamodel"


# ---------------------------------------------------------------------------
# Question ordering (the only behavioural difference between the two)
# ---------------------------------------------------------------------------

def test_inorder_question_ordering() -> None:
    fm = UVLReader(PIZZAS_UVL).transform()
    model = FmToConfigurator(fm, solver="pysat").transform()
    assert [q.name for q in model.questions] == ["Topping", "Pizza", "Size", "Dough"]


def test_preorder_question_ordering() -> None:
    fm = UVLReader(PIZZAS_UVL).transform()
    model = FmToConfiguratorPreOrder(fm, solver="pysat").transform()
    assert [q.name for q in model.questions] == ["Pizza", "Topping", "Size", "Dough"]


def test_traversals_yield_same_question_set() -> None:
    """Order differs, but the set of generated questions is identical."""
    fm_a = UVLReader(PIZZAS_UVL).transform()
    fm_b = UVLReader(PIZZAS_UVL).transform()
    inorder = {q.name for q in FmToConfigurator(fm_a, "pysat").transform().questions}
    preorder = {q.name for q in FmToConfiguratorPreOrder(fm_b, "pysat").transform().questions}
    assert inorder == preorder == {"Pizza", "Topping", "Size", "Dough"}


# ---------------------------------------------------------------------------
# Raw traversal helpers
# ---------------------------------------------------------------------------

def test_inorder_traversal_sequence() -> None:
    fm = UVLReader(PIZZAS_UVL).transform()
    transformer = FmToConfigurator(fm, solver="pysat")
    names = [f.name for f in transformer._inorder_traversal(fm.root)]
    assert names == [
        "Salami", "Topping", "Ham", "Mozzarella", "Pizza",
        "Normal", "Size", "Big", "Neapolitan", "Dough", "Sicilian", "CheesyCrust",
    ]


def test_preorder_traversal_sequence() -> None:
    fm = UVLReader(PIZZAS_UVL).transform()
    transformer = FmToConfiguratorPreOrder(fm, solver="pysat")
    names = [f.name for f in transformer._preorder_traversal(fm.root)]
    assert names == [
        "Pizza", "Topping", "Salami", "Ham", "Mozzarella",
        "Size", "Normal", "Big", "Dough", "Neapolitan", "Sicilian", "CheesyCrust",
    ]


# ---------------------------------------------------------------------------
# Structural invariants
# ---------------------------------------------------------------------------

def test_only_parent_features_become_questions() -> None:
    """Every question corresponds to a feature that actually has children."""
    fm = UVLReader(PIZZAS_UVL).transform()
    model = FmToConfigurator(fm, "pysat").transform()
    for question in model.questions:
        assert question.feature.get_children(), f"{question.name} has no children"
        assert len(question.options) == len(question.feature.get_children())


def test_options_indexed_by_name() -> None:
    fm = UVLReader(PIZZAS_UVL).transform()
    model = FmToConfigurator(fm, "pysat").transform()
    for leaf in ("Salami", "Ham", "Mozzarella", "Normal", "Big", "Neapolitan"):
        assert leaf in model.options_by_name


def test_default_backend_is_pysat() -> None:
    fm = UVLReader(PIZZAS_UVL).transform()
    model = FmToConfigurator(fm).transform()  # default solver
    assert isinstance(model.solver_backend, PySATBackend)


def test_feature_model_reference_is_kept() -> None:
    fm = UVLReader(PIZZAS_UVL).transform()
    model = FmToConfigurator(fm, "pysat").transform()
    assert model.feature_model is fm


# ---------------------------------------------------------------------------
# Core feature pre-selection
# ---------------------------------------------------------------------------

def test_core_boolean_features_are_preselected() -> None:
    """Mandatory features common to every configuration start SELECTED."""
    fm = UVLReader(PIZZAS_UVL).transform()
    model = FmToConfigurator(fm, "pysat").transform()
    for core in ("Topping", "Size", "Dough"):
        assert model.options_by_name[core].status is OptionStatus.SELECTED


def test_non_core_features_remain_undecided() -> None:
    fm = UVLReader(PIZZAS_UVL).transform()
    model = FmToConfigurator(fm, "pysat").transform()
    assert model.options_by_name["CheesyCrust"].status is OptionStatus.UNDECIDED
    assert model.options_by_name["Salami"].status is OptionStatus.UNDECIDED
