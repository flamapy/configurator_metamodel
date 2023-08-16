from flamapy.core.transformations.model_to_model import ModelToModel
from flamapy.metamodels.fm_metamodel.models.feature_model import FeatureModel
from flamapy.metamodels.configurator_metamodel.models.configurator_model import ConfiguratorModel, Question, Option

class FmToConfigurator(ModelToModel):
    @staticmethod
    def get_source_extension() -> str:
        return 'fm'

    @staticmethod
    def get_destination_extension() -> str:
        return 'configurator_metamodel'

    def __init__(self, source_model: FeatureModel) -> None:
        self.source_model = source_model
        self.counter = 1
        self.destination_model = ConfiguratorModel()
    
    def transform(self) -> ConfiguratorModel:
        for feature in self._inorder_traversal(self.source_model.root): # this requires some work to generalize the use of different traversal strategies
            print(feature.name)
            if len(feature.get_children()) > 0:
                question = Question(feature)
                for child in feature.get_children():
                    option = Option(child)
                    question.add_option(option)
                self.destination_model.add_question(question)
                
        return self.destination_model

  
    def _inorder_traversal(self, feature=None, result=None):
        if result is None:
            result = []
        if feature is None:
            feature = self.root
            
        children = feature.get_children()

        if children:
            # Traverse the first child (like the left child in binary trees)
            self._inorder_traversal(children[0], result)
            
            # Add the feature (parent) itself
            result.append(feature)
            
            # Traverse the remaining children (if any)
            for child in children[1:]:
                self._inorder_traversal(child, result)
        else:
            # If no children, just add the feature
            result.append(feature)
            
        return result
