from enum import Enum
from typing import List
from flamapy.core.models.variability_model import VariabilityModel
from flamapy.metamodels.fm_metamodel.models.feature_model import FeatureModel, Feature

from flamapy.metamodels.pysat_metamodel.models.pysat_model import PySATModel

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
        self.pysat_metamodel: PySATModel = None 

        self.questions: List[Question] = []
        self.current_question_index = -1
        self.history = []

    def add_question(self, question: 'Question'):
        self.questions.append(question)

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
                        
    def __str__(self) -> str:
        return str(self.questions)
    

