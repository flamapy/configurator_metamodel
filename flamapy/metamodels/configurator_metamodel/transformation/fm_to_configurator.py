from typing import List, Optional

from flamapy.core.transformations.model_to_model import ModelToModel
from flamapy.metamodels.fm_metamodel.models.feature_model import Feature, FeatureModel
from flamapy.metamodels.fm_metamodel.operations.fm_core_features import FMCoreFeatures
from flamapy.metamodels.configurator_metamodel.models.configurator_model import (
    ConfiguratorModel,
    Option,
    Question,
)


class FmToConfigurator(ModelToModel):
    """Transform a FeatureModel into a ConfiguratorModel.

    The transformation performs an in-order traversal of the feature tree to
    build an ordered list of questions.  Core (always-selected) features are
    pre-selected so the solver starts with a consistent partial assignment.

    Args:
        source_model: The feature model to transform.
        solver: Which backend to use — ``'pysat'`` (default) or ``'z3'``.
                Use ``'z3'`` for models with typed features (INTEGER, REAL,
                STRING) or arithmetic cross-tree constraints.
    """

    @staticmethod
    def get_source_extension() -> str:
        return 'fm'

    @staticmethod
    def get_destination_extension() -> str:
        return 'configurator_metamodel'

    def __init__(self, source_model: FeatureModel, solver: str = 'pysat') -> None:
        self.source_model = source_model
        self.destination_model = ConfiguratorModel()
        self.destination_model.feature_model = source_model

        if solver == 'z3':
            from flamapy.metamodels.z3_metamodel.transformations.fm_to_z3 import FmToZ3  # noqa: PLC0415
            from flamapy.metamodels.configurator_metamodel.solver.z3_backend import Z3Backend  # noqa: PLC0415
            z3_model = FmToZ3(source_model).transform()
            self.destination_model.solver_backend = Z3Backend(z3_model)
        else:
            from flamapy.metamodels.pysat_metamodel.transformations.fm_to_pysat import FmToPysat  # noqa: PLC0415
            from flamapy.metamodels.configurator_metamodel.solver.pysat_backend import PySATBackend  # noqa: PLC0415
            transformation = FmToPysat(source_model)
            transformation.transform()
            self.destination_model.solver_backend = PySATBackend(transformation.destination_model)

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
        """Traverse the feature tree in-order and return an ordered list of features."""
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
