import logging
from typing import Any, Dict, List, Optional

from flamapy.core.operations.abstract_operation import Operation
from flamapy.metamodels.configurator_metamodel.models import (
    ConfiguratorModel,
    Option,
    OptionStatus,
    Question,
)

LOGGER = logging.getLogger(__name__)


class Configure(Operation):
    """Interactive configuration operation for a ConfiguratorModel.

    Guides the user through a sequence of questions derived from the feature
    model, propagating constraints after every answer and supporting undo.

    The operation is solver-agnostic: it delegates all satisfiability and
    propagation work to the :class:`SolverBackend` stored on the model.
    Use ``FmToConfigurator(fm, solver='pysat')`` (default) for boolean models
    or ``FmToConfigurator(fm, solver='z3')`` for typed-feature models.
    """

    def __init__(self) -> None:
        self.result: int = 0
        self.configurator_model: Optional[ConfiguratorModel] = None

    # ------------------------------------------------------------------
    # Flamapy Operation interface
    # ------------------------------------------------------------------

    def get_result(self) -> Dict[str, Any]:
        """Return the current configuration as a ``{feature_name: value}`` dict."""
        return self._get_configuration()

    def execute(self, model: ConfiguratorModel) -> 'Configure':
        """Attach the operation to *model*.  The backend is already initialised."""
        self.configurator_model = model
        return self

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @property
    def _model(self) -> ConfiguratorModel:
        assert self.configurator_model is not None
        return self.configurator_model

    def _get_decisions(self) -> Dict[str, Any]:
        """Current decided options as ``{feature_name: value}``."""
        result: Dict[str, Any] = {}
        for question in self._model.questions:
            for option in question.options:
                if option.status == OptionStatus.SELECTED:
                    result[option.feature.name] = option.value if option.value is not None else True
                elif option.status == OptionStatus.DESELECTED:
                    result[option.feature.name] = False
        return result

    def _get_configuration(self) -> Dict[str, Any]:
        """Snapshot the current configuration as a plain dictionary."""
        config: Dict[str, Any] = {}
        for question in self._model.questions:
            for option in question.options:
                if option.status == OptionStatus.SELECTED:
                    config[option.feature.name] = option.value if option.value is not None else True
                elif option.status == OptionStatus.DESELECTED:
                    config[option.feature.name] = False
                else:
                    config[option.feature.name] = None
        return config

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Begin the configuration session by advancing to the first question."""
        self.next_question()

    def get_current_question(self) -> Question:
        """Return the question at the current index."""
        return self._model.questions[self._model.current_question_index]

    def get_possible_options(self) -> List[Option]:
        """Return undecided, non-mandatory options for the current question."""
        return [
            option
            for option in self.get_current_question().options
            if option.status == OptionStatus.UNDECIDED and not option.feature.is_mandatory()
        ]

    def next_question(self) -> bool:
        """Advance to the next question that has at least one possible option.

        Returns:
            ``True`` if a new question was found, ``False`` if the session is complete.
        """
        while True:
            if self.is_last_question() or self.is_finished():
                return False

            self._model.current_question_index += 1

            if self.get_possible_options():
                return True

            # No choices here; record state and keep advancing
            self._model.history.append(self._get_configuration())

    def previous_question(self) -> bool:
        """Retreat to the previous question that has at least one possible option.

        Returns:
            ``True`` if a previous question was found, ``False`` if already at the start.
        """
        while True:
            if self.is_first_question():
                return False

            self.undo_answer()
            self._model.current_question_index -= 1

            if self.get_possible_options():
                return True

    def is_first_question(self) -> bool:
        """Return True if the current question is the first one."""
        return self._model.current_question_index == 0

    def is_last_question(self) -> bool:
        """Return True if the current question is the last one."""
        return (
            len(self._model.questions) - 1
            == self._model.current_question_index
        )

    def is_finished(self) -> bool:
        """Return True if all questions have been answered."""
        return (
            len(self._model.questions)
            == self._model.current_question_index
        )

    # ------------------------------------------------------------------
    # Answering and undoing
    # ------------------------------------------------------------------

    def answer_question(self, answer: Dict[str, Any]) -> bool:
        """Apply *answer* to the model and propagate constraints.

        Args:
            answer: Mapping from option name to its chosen value.

        Returns:
            ``True`` if the answer is consistent with the model constraints,
            ``False`` if it causes a contradiction (the change is rolled back).
        """
        self._model.history.append(self._get_configuration())

        for name, value in answer.items():
            self._model.set_state(name, value)

        assert self._model.solver_backend is not None, "No solver backend — call execute() first."
        implied = self._model.solver_backend.propagate(self._get_decisions())
        if implied is None:
            self.undo_answer()
            LOGGER.debug(
                "Answer leads to a contradiction; change rolled back. Please try again."
            )
            return False

        for name, value in implied.items():
            self._model.set_state(name, value)

        # Ensure the current question's parent feature is also marked selected
        current_q_name = self.get_current_question().name
        if current_q_name in self._model.options_by_name:
            self._model.set_state(current_q_name, True)

        if self.is_last_question():
            self._model.current_question_index += 1

        LOGGER.debug("Answer accepted.")
        return True

    def undo_answer(self) -> bool:
        """Restore the configuration state from before the last answer.

        Returns:
            ``True`` if history was available and state was restored, ``False`` otherwise.
        """
        if not self._model.history:
            return False

        last_config = self._model.history.pop()
        for name, value in last_config.items():
            self._model.set_state(name, value)
        return True

    # ------------------------------------------------------------------
    # Status reporting
    # ------------------------------------------------------------------

    def get_current_question_type(self) -> str:
        """Return the type of the current question: 'alternative', 'or', or 'optional'."""
        feature = self.get_current_question().feature
        if feature.is_alternative_group():
            return 'alternative'
        if feature.is_or_group():
            return 'or'
        return 'optional'

    def get_current_status(self) -> Dict[str, Any]:
        """Return a dictionary describing the current configuration state."""
        possible = self.get_possible_options()
        return {
            'currentQuestion': self.get_current_question().name,
            'currentQuestionType': self.get_current_question_type(),
            'currentQuestionIndex': self._model.current_question_index,
            'isLastQuestion': self.is_last_question(),
            'possibleOptions': [
                {'id': n, 'name': o.name, 'featureType': o.feature.feature_type}
                for n, o in enumerate(possible)
            ],
        }
