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
    
    def _init_pysat_solver(self):
        transformation = FmToPysat(self.feature_model)
        transformation.transform()
        return transformation.destination_model