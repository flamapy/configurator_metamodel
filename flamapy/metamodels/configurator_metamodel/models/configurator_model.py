import logging
from enum import Enum
from typing import Any, Dict, List, Optional

from flamapy.core.models.variability_model import VariabilityModel
from flamapy.metamodels.fm_metamodel.models.feature_model import Feature, FeatureModel

LOGGER = logging.getLogger(__name__)

OptionStatus = Enum('OptionStatus', 'SELECTED DESELECTED UNDECIDED')


class Option:
    """Represents a selectable option in a configuration question.

    Each option corresponds to a child feature in the feature model.
    """

    def __init__(self, feature: Feature) -> None:
        self.name = feature.name
        self.status = OptionStatus.UNDECIDED
        self.value: Any = None
        self.feature = feature

    def __str__(self) -> str:
        return f'{self.name}: {self.status} ({self.value})'


class Question:
    """Represents a configuration question derived from a parent feature.

    A question contains the options (child features) the user must choose from.
    """

    def __init__(self, feature: Feature) -> None:
        self.name = feature.name
        self.options: List[Option] = []
        self.feature = feature

    def add_option(self, option: Option) -> None:
        """Add an option to this question."""
        self.options.append(option)

    def __str__(self) -> str:
        return f'{self.name}: {self.options}'


class ConfiguratorModel(VariabilityModel):
    """A variability model that drives an interactive configuration session.

    Wraps a FeatureModel and a solver backend to guide users through a sequence
    of questions, enforcing constraints at every step.  The backend is
    solver-agnostic: pass a :class:`PySATBackend` for boolean models or a
    :class:`Z3Backend` for models with typed features (INTEGER, REAL, STRING).
    """

    @staticmethod
    def get_extension() -> str:
        return 'configurator_metamodel'

    def __init__(self) -> None:
        self.feature_model: FeatureModel
        self.solver_backend: Optional[Any] = None  # SolverBackend

        self.questions: List[Question] = []
        self.options_by_name: Dict[str, Option] = {}
        self.current_question_index = -1
        self.history: List[Dict[str, Any]] = []

    def add_question(self, question: Question) -> None:
        """Register a question and index all of its options by name."""
        self.questions.append(question)
        for option in question.options:
            self.options_by_name[option.name] = option

    def set_state(self, feature_name: str, feature_value: Any) -> None:
        """Update the status and value of an option by feature name.

        Args:
            feature_name: The name of the feature whose option should be updated.
            feature_value: The new value.  ``True``/``False`` set SELECTED/DESELECTED;
                any other non-None value sets SELECTED; ``None`` resets to UNDECIDED.
        """
        if feature_name not in self.options_by_name:
            LOGGER.debug(
                "Feature '%s' not found in options (possibly root or hidden feature).",
                feature_name,
            )
            return

        option = self.options_by_name[feature_name]
        option.value = feature_value  # Always update so undo / re-configuration works

        if feature_value is True:
            option.status = OptionStatus.SELECTED
        elif feature_value is False:
            option.status = OptionStatus.DESELECTED
        elif feature_value is not None:
            option.status = OptionStatus.SELECTED
        else:
            option.status = OptionStatus.UNDECIDED

    def __str__(self) -> str:
        return str(self.questions)
