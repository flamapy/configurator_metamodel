import logging
from flamapy.core.operations.abstract_operation import Operation

from flamapy.metamodels.configurator_metamodel.models import ConfiguratorModel, Question, Option, OptionStatus

from pysat.solvers import Solver

LOGGER = logging.getLogger('Configure')


class Configure(Operation):

    def __init__(self) -> None:
        self.result = 0

    def get_result(self) -> int:
        return self._get_current_assumptions()

    def execute(self, model: ConfiguratorModel) -> 'Configure':
        self.configurator_model = model
        
        # Optimize: Only initialize solver if it doesn't exist or if model changed significantly (simplified check)
        # Assuming model structure doesn't change mid-operation for existing use cases.
        if not hasattr(self, 'pysat') or self.pysat is None:
            self.pysat = Solver(name='glucose3')
            for clause in self.configurator_model.pysat_metamodel.get_all_clauses():
                self.pysat.add_clause(clause)
        
        return self


    def _get_current_assumptions(self):
        assumptions = []
        for question in self.configurator_model.questions:
            for option in question.options:
                if option.status == OptionStatus.SELECTED:
                    assumptions.append(self.configurator_model.pysat_metamodel.variables[option.feature.name])
                elif option.status == OptionStatus.DESELECTED:
                    assumptions.append(-self.configurator_model.pysat_metamodel.variables[option.feature.name])
        return assumptions
    
    def _get_configuration(self):
        configuration = dict()
        for question in self.configurator_model.questions:
            for option in question.options:
                if option.status == OptionStatus.SELECTED:
                     # Use the specific value if available, otherwise True
                    configuration[option.feature.name] = option.value if option.value is not None else True
                elif option.status == OptionStatus.DESELECTED:
                    configuration[option.feature.name] = False
                else:
                    configuration[option.feature.name] = None
        return configuration
    
    def _propagate(self):
        assumptions = self._get_current_assumptions()
            
        # Perform propagation using the solver's 'propagate' method
        # This will return a list of literals that are implied by the assumption(s)
        # Propagate the assignment
        status, implied_lits = self.pysat.propagate(assumptions=assumptions)

        # If the status is False, the assignment leads to a contradiction
        if status is False:
            return None

        implied_values = {abs(lit): (lit > 0) for lit in implied_lits}

        return implied_values
        
    def start(self):
        self.next_question()
    
    def get_current_question(self):
        return self.configurator_model.questions[self.configurator_model.current_question_index]

    def get_possible_options(self):
        return list(filter(lambda option: option.status == OptionStatus.UNDECIDED and not option.feature.is_mandatory(), self.get_current_question().options))
    
    def next_question(self):
        # Refactored to use iteration instead of recursion
        while True:
            if self.is_last_question() or self.is_finished():
                return False
            
            self.configurator_model.current_question_index += 1
            
            if len(self.get_possible_options()) > 0:
                # Found a question with options, stop advancing
                return True
                
            # If no possible options, save state and continue loop (equivalent to recursive call)
            self.configurator_model.history.append(self._get_configuration())

    def previous_question(self):
        # Refactored to use iteration instead of recursion
        while True:
            if self.is_first_question():
                return False
            
            self.undo_answer()
            self.configurator_model.current_question_index -= 1
            
            if len(self.get_possible_options()) > 0:
                return True
            # If no possible options, continue loop (equivalent to recursive call)

    def is_first_question(self):
        return self.configurator_model.current_question_index == 0
    
    def is_last_question(self):
        return len(self.configurator_model.questions) - 1 == self.configurator_model.current_question_index
    
    def is_finished(self):
        return len(self.configurator_model.questions) == self.configurator_model.current_question_index

    
    def answer_question(self, answer: dict):
        # Answer is now a dictionary {option_name: value}
        self.configurator_model.history.append(self._get_configuration())  # Save state before propagation
        # Apply the answers
        for name, value in answer.items():
            self.configurator_model.set_state(name, value)

        result = self._propagate()
        if result is None:
            # Undo the changes
            self.undo_answer() 
            LOGGER.debug("The assignment leads to a contradiction! you can not configure the product that way. Please try again.")
            return False
        else:
            for key, value in result.items():
                feature_name = self.configurator_model.pysat_metamodel.features[key]
                self.configurator_model.set_state(feature_name, value)
            
            # Keeping it safe: if the question name is in options, set it.
            current_q_name = self.get_current_question().name
            if current_q_name in self.configurator_model.options_by_name:
                 self.configurator_model.set_state(current_q_name, True)
                 
            if self.is_last_question():
                self.configurator_model.current_question_index += 1
            LOGGER.debug("The assignment is valid.")
            return True 
    
    def undo_answer(self):
        if self.configurator_model.history:
            last_config = self.configurator_model.history.pop()
            # Restore state from the dictionary
            for name, value in last_config.items():
                self.configurator_model.set_state(name, value)
            return True
        return False
    
    def get_current_question_type(self):
        current_question = self.get_current_question()

        if current_question.feature.is_alternative_group():
            current_question_type = 'alternative'
        elif current_question.feature.is_or_group():
            current_question_type = 'or'
        else:
            current_question_type = 'optional'
        return current_question_type

        
    def get_current_status(self):
        status = dict()

        status['currentQuestion'] = self.get_current_question().name
        status['currentQuestionType'] = self.get_current_question_type()
        status['possibleOptions'] = [{'id':n, 'name': o.name} for n, o in enumerate(self.get_possible_options())]
        status['currentQuestionIndex'] = self.configurator_model.current_question_index
        status['questionNumber'] = self.is_last_question()
        status['possibleOptions'] = [{'id':n, 'name': o.name, 'featureType': o.feature.feature_type} for n, o in enumerate(self.get_possible_options())]

        return status