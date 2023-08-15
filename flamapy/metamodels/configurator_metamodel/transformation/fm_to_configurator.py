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
        for feature in self._inorder_traversal(self.source_model.root):
            if feature.hasChilds():
                question = Question(feature.name)
                for child in feature.childs:
                    option = Option(child.name)
                self.destination_model.add_question(question)
                
        return self.destination_model

  
    def _inorder_traversal(self, feature=None, result=None):
        if result is None:
            result = []
        if feature is None:
            feature = self.root
        if feature is not None:
            for i, child in enumerate(feature.relations):
                if i == 0:
                    self.inorder_traversal(child, result)
                result.append(feature)  # Add the root (or 'parent' in this context)
                if i != 0:
                    self.inorder_traversal(child, result)
        return result

    def _postorder_traversal(self, feature=None, result=None):
        if result is None:
            result = []
        if feature is None:
            feature = self.root
        if feature is not None:
            for child in feature.relations:
                self.postorder_traversal(child, result)
            result.append(feature)  # Add the root last
        return result

    def _preorder_traversal_iterative(self, feature=None):
        if feature is None:
            feature = self.root
        result = []
        stack = [feature]
        while stack:
            current = stack.pop()
            if current:
                result.append(current)
                for child in reversed(current.relations):  # reversed because we want to visit leftmost child first
                    stack.append(child)
        return result

    def _custom_order(self):
        print("Enter the names of features in the order you want them to be processed:")
        custom_order = []
        while True:
            feature_name = input("Enter a feature name (or 'done' to finish): ")
            if feature_name.lower() == 'done':
                break
            feature = self.get_feature_by_name(feature_name)
            if feature is not None:
                custom_order.append(feature)
            else:
                print(f"No feature found with name '{feature_name}', please try again.")
        return custom_order