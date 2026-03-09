"""Integration tests for the configurator_metamodel package."""
import pytest

from flamapy.metamodels.fm_metamodel.transformations import UVLReader
from flamapy.metamodels.configurator_metamodel.transformation.fm_to_configurator import (
    FmToConfigurator,
)
from flamapy.metamodels.configurator_metamodel.operations.configure import Configure


@pytest.mark.parametrize("path", [
    "resources/models/uvl_models/Pizzas.uvl",
])
def test_full_configuration_run(path: str) -> None:
    """Load FM → transform → execute → auto-answer all questions → assert finished."""
    fm = UVLReader(path).transform()
    configurator_model = FmToConfigurator(fm).transform()

    op = Configure()
    op.execute(configurator_model)
    op.start()

    max_steps = 100
    steps = 0
    while not op.is_finished() and steps < max_steps:
        status = op.get_current_status()
        possible = status["possibleOptions"]
        if possible:
            name = possible[0]["name"]
            feature_type = possible[0]["featureType"]
            type_name = feature_type.name if hasattr(feature_type, "name") else str(feature_type)
            if type_name == "INTEGER":
                value: object = 1
            elif type_name == "REAL":
                value = 1.0
            elif type_name == "STRING":
                value = "test"
            else:
                value = True
            op.answer_question({name: value})
        op.next_question()
        steps += 1

    assert op.is_finished(), f"Configuration did not finish after {steps} steps"
