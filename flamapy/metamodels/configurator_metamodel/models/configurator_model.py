from flamapy.core.models.variability_model import VariabilityModel
from flamapy.metamodels.fm_metamodel.models.feature_model import FeatureModel, Feature

class ConfiguratorModel(VariabilityModel):

    @staticmethod
    def get_extension() -> str:
        return 'configurator_metamodel'

    def __init__(self) -> None:
        feature_model: 'FeatureModel'
        questions=list['Question']

class Question():
    def __init__(self) -> None:
        name = str
        options = list['Option']

class Option():
    def __init__(self) -> None:
        name = str
        selected = bool
        feature = 'Feature'