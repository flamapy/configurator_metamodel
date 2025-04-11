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
        self.pysat= Solver(name='glucose3')
        print(self.configurator_model.pysat_metamodel)
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
                    configuration[option.feature.name] = True
                elif option.status == OptionStatus.DESELECTED:
                    configuration[option.feature.name] = False
                else:
                    configuration[option.feature.name] = None
        return configuration
    
    def _propagate(self):
        # get current model assumptions
        # total_assumptions = [assumptions] + self.configurator_model._get_current_assumptions()
        assumptions=self._get_current_assumptions()
        # Create a solver instance and add the formula
        # with Solver(name="glucose4", bootstrap_with=self.pysat_solver._cnf.clauses) as solver:
            
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
        if self.is_last_question() or self.is_finished():
            return False
        else:
            self.configurator_model.current_question_index += 1
            if len(self.get_possible_options()) == 0:
                self.configurator_model.history.append(self._get_configuration())  # Save state before propagation
                return self.next_question()
        return True

    def previous_question(self):
        if self.is_first_question():
            return False
        else:
            self.undo_answer()
            self.current_question_index -= 1
            if len(self.get_possible_options()) == 0:
                return self.previous_question()
        return True

    def is_first_question(self):
        return self.configurator_model.current_question_index == 0
    
    def is_last_question(self):
        return len(self.configurator_model.questions) - 1 == self.configurator_model.current_question_index
    
    def is_finished(self):
        return len(self.configurator_model.questions) == self.configurator_model.current_question_index

    
    def answer_question(self, answer):
        possible_options = self.get_possible_options()
        self.configurator_model.history.append(self._get_configuration())  # Save state before propagation
        for index in answer:
            possible_options[index].status = OptionStatus.SELECTED

        result = self._propagate()
        if result is None:
            # Undo the changes
            for index in answer:
                # You might want to add checks to ensure valid selection. I.e., call a sat solver and propagate
                possible_options[index].status = OptionStatus.UNDECIDED
            LOGGER.debug("The assignment leads to a contradiction! you can not configure the product that way. Please try again.")
            self.configurator_model.history.pop()
            return False
        else:
            for key, value in result.items():
                feature_name = self.configurator_model.pysat_metamodel.features[key]
                self.configurator_model.set_state(feature_name, value)
            self.configurator_model.set_state(self.get_current_question().name, True)
            if self.is_last_question():
                self.configurator_model.current_question_index += 1
            LOGGER.debug("The assignment is valid.")
            return True 
    
    def undo_answer(self):
        if self.configurator_model.history:
            last_config = self.configurator_model.history.pop()
            for question in self.configurator_model.questions:
                for option in question.options:
                    if last_config[option.feature.name] == True:
                        option.status = OptionStatus.SELECTED
                    elif last_config[option.feature.name] == False:
                        option.status = OptionStatus.DESELECTED
                    else:
                        option.status = OptionStatus.UNDECIDED
            return True
        return False
    
    def get_current_question_type(self):
        current_question = self.configurator_model.get_current_question()

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

        return status