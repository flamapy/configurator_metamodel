from enum import Enum
from typing import List, Any
from flamapy.core.models.variability_model import VariabilityModel
from flamapy.metamodels.fm_metamodel.models.feature_model import FeatureModel, Feature

from flamapy.metamodels.pysat_metamodel.models.pysat_model import PySATModel

OptionStatus = Enum('OptionStatus', 'SELECTED DESELECTED UNDECIDED')


class Option:
    def __init__(self, feature: Feature):
        self.name = feature.name
        self.status = OptionStatus.UNDECIDED
        self.value: Any = None
        self.feature = feature
        
    def __str__(self) -> str:
        return f'{self.name}: {self.status} ({self.value})'
    
class Question:
    def __init__(self, feature: Feature) -> None:
        self.name = feature.name
        self.options: List[Option] = []
        self.feature = feature
    
    def add_option(self, option: Option):  
        self.options.append(option)

    def __str__(self) -> str:
        return f'{self.name}: {self.options}'

class ConfiguratorModel(VariabilityModel):

    @staticmethod
    def get_extension() -> str:
        return 'configurator_metamodel'

    def __init__(self) -> None:
        self.feature_model: 'FeatureModel'
        self.pysat_metamodel: PySATModel = None 

        self.questions: List[Question] = []
        self.options_by_name: dict[str, Option] = {}
        self.current_question_index = -1
        self.history = []

    def add_question(self, question: 'Question'):
        self.questions.append(question)
        for option in question.options:
            self.options_by_name[option.name] = option

    def set_state(self, feature_name: str, feature_value: Any):
        if feature_name in self.options_by_name:
            option = self.options_by_name[feature_name]
            option.value = feature_value if option.value is None else option.value # Store the specific value
            
            # Logic for status based on value presence/correctness could go here.
            # For now, we assume setting a value implies selection if it's truthy or explicit True/False for booleans.
            if feature_value is True:
                 option.status = OptionStatus.SELECTED
            elif feature_value is False:
                 option.status = OptionStatus.DESELECTED
            elif feature_value is not None:
                 option.status = OptionStatus.SELECTED # Non-boolean values imply selection?
            else:
                 option.status = OptionStatus.UNDECIDED
        else:
            print(f"Warning: Feature {feature_name} not found in options (possibly root or hidden feature).")
            pass
                        
    def __str__(self) -> str:
        return str(self.questions)
    

