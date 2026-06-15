"""Pytest fixtures and markers shared across the configurator_metamodel tests.

This module centralises:

* Resolution of the bundled UVL resource paths (robust to the working
  directory pytest is launched from).
* A ``requires_z3`` skip marker, so the Z3-dependent tests are skipped — not
  failed — when the optional ``flamapy-z3`` package is not installed.
* Reusable fixtures: hand-built ``ConfiguratorModel`` instances and a
  ``Configure`` operation wired to a mock solver backend.
"""
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from flamapy.metamodels.fm_metamodel.models.feature_model import Feature, FeatureType
from flamapy.metamodels.configurator_metamodel.models.configurator_model import (
    ConfiguratorModel,
    Option,
    Question,
)
from flamapy.metamodels.configurator_metamodel.operations.configure import Configure

# ---------------------------------------------------------------------------
# Resource paths
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parent.parent
_MODELS_DIR = _REPO_ROOT / "resources" / "models" / "uvl_models"

PIZZAS_UVL = str(_MODELS_DIR / "Pizzas.uvl")
PIZZAS_TYPED_UVL = str(_MODELS_DIR / "Pizzas_typed.uvl")


# ---------------------------------------------------------------------------
# Optional Z3 backend detection
# ---------------------------------------------------------------------------

try:
    import flamapy.metamodels.z3_metamodel  # noqa: F401
    HAS_Z3 = True
except ImportError:
    HAS_Z3 = False

#: Decorator to skip a test when the optional ``flamapy-z3`` plugin is absent.
requires_z3 = pytest.mark.skipif(
    not HAS_Z3, reason="optional dependency 'flamapy-z3' is not installed"
)


# ---------------------------------------------------------------------------
# Hand-built model fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def simple_model() -> ConfiguratorModel:
    """A minimal model: one question (Root) with a boolean and an integer option.

    Used for the metamodel ``set_state`` tests and the simpler ``Configure``
    unit tests that only need a single question with two undecided options.
    """
    model = ConfiguratorModel()
    f_root = Feature("Root", feature_type=FeatureType.BOOLEAN)
    f_child1 = Feature("Child1", parent=f_root, feature_type=FeatureType.BOOLEAN)
    f_typed = Feature("TypedFeat", parent=f_root, feature_type=FeatureType.INTEGER)
    question = Question(f_root)
    question.add_option(Option(f_child1))
    question.add_option(Option(f_typed))
    model.add_question(question)
    return model


@pytest.fixture
def mock_configure(simple_model: ConfiguratorModel) -> Configure:
    """A ``Configure`` operation bound to ``simple_model`` and a mock backend.

    The mock backend reports no implied features and never signals a
    contradiction, isolating the operation logic from any real solver.
    """
    backend = MagicMock()
    backend.propagate.return_value = {}
    simple_model.solver_backend = backend
    simple_model.current_question_index = 0

    operation = Configure()
    operation.execute(simple_model)
    return operation
