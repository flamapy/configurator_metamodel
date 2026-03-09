from typing import List, Optional

from flamapy.core.transformations.model_to_model import ModelToModel
from flamapy.metamodels.fm_metamodel.models.feature_model import Feature, FeatureModel
from flamapy.metamodels.fm_metamodel.operations.fm_core_features import FMCoreFeatures
from flamapy.metamodels.configurator_metamodel.models.configurator_model import (
    ConfiguratorModel,
    Option,
    Question,
)
from flamapy.metamodels.pysat_metamodel.transformations.fm_to_pysat import FmToPysat


class FmToConfigurator(ModelToModel):
    """Transform a FeatureModel into a ConfiguratorModel.

    The transformation performs an in-order traversal of the feature tree to
    build an ordered list of questions.  Core (always-selected) features are
    pre-selected so the solver starts with a consistent partial assignment.
    """

    @staticmethod
    def get_source_extension() -> str:
        return 'fm'

    @staticmethod
    def get_destination_extension() -> str:
        return 'configurator_metamodel'

    def __init__(self, source_model: FeatureModel) -> None:
        self.source_model = source_model
        self.destination_model = ConfiguratorModel()
        self.destination_model.feature_model = source_model

        transformation = FmToPysat(self.destination_model.feature_model)
        transformation.transform()
        self.destination_model.pysat_metamodel = transformation.destination_model

    def transform(self) -> ConfiguratorModel:
        """Build and return the ConfiguratorModel."""
        operation = FMCoreFeatures()
        operation.execute(self.source_model)
        core_features = operation.get_result()

        for feature in self._inorder_traversal(self.source_model.root):
            if feature.get_children():
                question = Question(feature)
                for child in feature.get_children():
                    option = Option(child)
                    question.add_option(option)
                self.destination_model.add_question(question)

        for core_feature in core_features:
            self.destination_model.set_state(core_feature.name, True)

        return self.destination_model

    def _inorder_traversal(
        self,
        feature: Optional[Feature] = None,
        result: Optional[List[Feature]] = None,
    ) -> List[Feature]:
        """Traverse the feature tree in-order and return an ordered list of features.

        Args:
            feature: The current feature node.  Defaults to the model root.
            result: Accumulator list; created automatically on the first call.

        Returns:
            Ordered list of Feature objects.
        """
        if result is None:
            result = []
        if feature is None:
            feature = self.source_model.root

        children = feature.get_children()

        if children:
            self._inorder_traversal(children[0], result)
            result.append(feature)
            for child in children[1:]:
                self._inorder_traversal(child, result)
        else:
            result.append(feature)

        return result
