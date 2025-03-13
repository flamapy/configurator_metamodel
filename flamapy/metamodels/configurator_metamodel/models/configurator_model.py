from enum import Enum
from typing import List
from flamapy.core.models.variability_model import VariabilityModel
from flamapy.metamodels.fm_metamodel.models.feature_model import FeatureModel, Feature

from flamapy.metamodels.pysat_metamodel.models.pysat_model import PySATModel
from flamapy.metamodels.pysat_metamodel.transformations.fm_to_pysat import FmToPysat
OptionStatus = Enum('OptionStatus', 'SELECTED DESELECTED UNDECIDED')


class Option:
    def __init__(self, feature: Feature):
        self.name = feature.name
        self.status = OptionStatus.UNDECIDED
        self.feature = feature
        
    def __str__(self) -> str:
        return self.name+':'+str(self.status)
    
class Question:
    def __init__(self, feature:Feature) -> None:
        self.name = feature.name
        self.options: List[Option] = []
        self.feature = feature
    
    def add_option(self, option: Option):  
        self.options.append(option)

    def __str__(self) -> str:
        self.name+':'+str(self.options)

class ConfiguratorModel(VariabilityModel):

    @staticmethod
    def get_extension() -> str:
        return 'configurator_metamodel'

    def __init__(self) -> None:
        self.feature_model: 'FeatureModel'
        self.pysat_solver = None

        self.questions: List[Question] = []

    def add_question(self, question: 'Question'):
        self.questions.append(question)

    def __str__(self) -> str:
        return str(self.questions)
    
    def set_state(self, feature_name: str, feature_value: bool):
        for question in self.questions:
            # if question.name == feature_name:
            for option in question.options:
                if option.feature.name == feature_name:
                    if feature_value == True:
                        option.status = OptionStatus.SELECTED
                    elif feature_value == False:
                        option.status = OptionStatus.DESELECTED
                    else:
                        option.status = OptionStatus.UNDECIDED
                        print("Error: feature value is not boolean")

    def _init_pysat_solver(self):
        transformation = FmToPysat(self.feature_model)
        transformation.transform()
        return transformation.destination_model
    
    def _get_current_assumptions(self):
        assumptions = []
        for question in self.questions:
            for option in question.options:
                if option.status == OptionStatus.SELECTED:
                    assumptions.append(self.pysat_solver.variables[option.feature.name])
                elif option.status == OptionStatus.DESELECTED:
                    assumptions.append(-self.pysat_solver.variables[option.feature.name])
        return assumptions
    
    def _get_configuration(self):
        configuration = {}
        for question in self.questions:
            for option in question.options:
                if option.status == OptionStatus.SELECTED:
                    configuration[option.feature.name] = 1
                elif option.status == OptionStatus.DESELECTED:
                    configuration[option.feature.name] = -1
                else:
                    configuration[option.feature.name] = 0
        return configuration
    
    def _propagate(self):
        from pysat.solvers import Solver
        # get current model assumptions
        # total_assumptions = [assumptions] + self.configurator_model._get_current_assumptions()
        assumptions=self._get_current_assumptions()
       # print(total_assumptions)
        # Create a solver instance and add the formula
        with Solver(name="glucose4", bootstrap_with=self.pysat_solver._cnf.clauses) as solver:
            
            # Perform propagation using the solver's 'propagate' method
            # This will return a list of literals that are implied by the assumption(s)
            # Propagate the assignment
            status, implied_lits = solver.propagate(assumptions=assumptions)

            # If the status is False, the assignment leads to a contradiction
            if status is False:
                return None

            implied_values = {abs(lit): (lit > 0) for lit in implied_lits}

            return implied_values
        
    def start(self):
        self.current_question_index = 0
    
    def get_current_question(self):
        return self.questions[self.current_question_index]

    def get_possible_options(self):
        return list(filter(lambda option: option.status == OptionStatus.UNDECIDED, self.get_current_question().options))
    
    def next_question(self):
        if self.is_last_question():
            return False
        else:
            self.current_question_index += 1
            if len(self.get_possible_options()) == 0:
                self.next_question()
        return True

    def is_last_question(self):
        return len(self.questions) - 1 == self.current_question_index
    
    def answer_question(self, answer):
        possible_options = self.get_possible_options()
        for index in answer:
            possible_options[index].status = OptionStatus.SELECTED

        result = self._propagate()
        if result is None:
            # Undo the changes
            for index in answer:
                # You might want to add checks to ensure valid selection. I.e., call a sat solver and propagate
                possible_options[index].status = OptionStatus.UNDECIDED
            print("The assignment leads to a contradiction! you can not configure the product that way. Please try again.")
            return False
        else:
            for key, value in result.items():
                feature_name = self.pysat_solver.features[key]
                print(feature_name, value)
                self.set_state(feature_name, value)
            self.set_state(self.get_current_question().name, True)
            print("The assignment is valid.")
            return True 
    
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

        return status
