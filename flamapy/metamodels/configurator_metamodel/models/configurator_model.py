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