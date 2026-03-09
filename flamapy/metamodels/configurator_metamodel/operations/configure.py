import logging
from typing import Any, Dict, List, Optional

from flamapy.core.operations.abstract_operation import Operation
from flamapy.metamodels.configurator_metamodel.models import (
    ConfiguratorModel,
    Option,
    OptionStatus,
    Question,
)
from pysat.solvers import Solver

LOGGER = logging.getLogger(__name__)

_DEFAULT_SOLVER = 'glucose3'


class Configure(Operation):
    """Interactive configuration operation for a ConfiguratorModel.

    Guides the user through a sequence of questions derived from the feature
    model, propagating SAT constraints after every answer and supporting undo.
    """

    def __init__(self) -> None:
        self.result = 0
        self.pysat: Optional[Solver] = None
        self.configurator_model: Optional[ConfiguratorModel] = None

    # ------------------------------------------------------------------
    # Flamapy Operation interface
    # ------------------------------------------------------------------

    def get_result(self) -> List[int]:
        """Return the current SAT assumptions (selected / deselected literals)."""
        return self._get_current_assumptions()

    def execute(self, model: ConfiguratorModel) -> 'Configure':
        """Attach the operation to *model* and initialise the SAT solver."""
        self.configurator_model = model

        if self.pysat is None:
            self.pysat = Solver(name=_DEFAULT_SOLVER)
            for clause in self.configurator_model.pysat_metamodel.get_all_clauses():
                self.pysat.add_clause(clause)

        return self

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_current_assumptions(self) -> List[int]:
        """Build the list of SAT literals for every decided option."""
        assumptions: List[int] = []
        variables = self.configurator_model.pysat_metamodel.variables
        for question in self.configurator_model.questions:
            for option in question.options:
                var = variables[option.feature.name]
                if option.status == OptionStatus.SELECTED:
                    assumptions.append(var)
                elif option.status == OptionStatus.DESELECTED:
                    assumptions.append(-var)
        return assumptions

    def _get_configuration(self) -> Dict[str, Any]:
        """Snapshot the current configuration as a plain dictionary."""
        config: Dict[str, Any] = {}
        for question in self.configurator_model.questions:
            for option in question.options:
                if option.status == OptionStatus.SELECTED:
                    config[option.feature.name] = option.value if option.value is not None else True
                elif option.status == OptionStatus.DESELECTED:
                    config[option.feature.name] = False
                else:
                    config[option.feature.name] = None
        return config

    def _propagate(self) -> Optional[Dict[int, bool]]:
        """Run unit propagation and return implied literals, or None on conflict."""
        assumptions = self._get_current_assumptions()
        status, implied_lits = self.pysat.propagate(assumptions=assumptions)

        if status is False:
            return None

        return {abs(lit): lit > 0 for lit in implied_lits}

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Begin the configuration session by advancing to the first question."""
        self.next_question()

    def get_current_question(self) -> Question:
        """Return the question at the current index."""
        return self.configurator_model.questions[self.configurator_model.current_question_index]

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

            self.configurator_model.current_question_index += 1

            if self.get_possible_options():
                return True

            # No choices here; record state and keep advancing
            self.configurator_model.history.append(self._get_configuration())

    def previous_question(self) -> bool:
        """Retreat to the previous question that has at least one possible option.

        Returns:
            ``True`` if a previous question was found, ``False`` if already at the start.
        """
        while True:
            if self.is_first_question():
                return False

            self.undo_answer()
            self.configurator_model.current_question_index -= 1

            if self.get_possible_options():
                return True

    def is_first_question(self) -> bool:
        """Return True if the current question is the first one."""
        return self.configurator_model.current_question_index == 0

    def is_last_question(self) -> bool:
        """Return True if the current question is the last one."""
        return (
            len(self.configurator_model.questions) - 1
            == self.configurator_model.current_question_index
        )

    def is_finished(self) -> bool:
        """Return True if all questions have been answered."""
        return (
            len(self.configurator_model.questions)
            == self.configurator_model.current_question_index
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
        self.configurator_model.history.append(self._get_configuration())

        for name, value in answer.items():
            self.configurator_model.set_state(name, value)

        result = self._propagate()
        if result is None:
            self.undo_answer()
            LOGGER.debug(
                "Answer leads to a contradiction; change rolled back. Please try again."
            )
            return False

        features = self.configurator_model.pysat_metamodel.features
        for var_id, value in result.items():
            self.configurator_model.set_state(features[var_id], value)

        # Ensure the current question's parent feature is also marked selected
        current_q_name = self.get_current_question().name
        if current_q_name in self.configurator_model.options_by_name:
            self.configurator_model.set_state(current_q_name, True)

        if self.is_last_question():
            self.configurator_model.current_question_index += 1

        LOGGER.debug("Answer accepted.")
        return True

    def undo_answer(self) -> bool:
        """Restore the configuration state from before the last answer.

        Returns:
            ``True`` if history was available and state was restored, ``False`` otherwise.
        """
        if not self.configurator_model.history:
            return False

        last_config = self.configurator_model.history.pop()
        for name, value in last_config.items():
            self.configurator_model.set_state(name, value)
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
            'currentQuestionIndex': self.configurator_model.current_question_index,
            'isLastQuestion': self.is_last_question(),
            'possibleOptions': [
                {'id': n, 'name': o.name, 'featureType': o.feature.feature_type}
                for n, o in enumerate(possible)
            ],
        }
