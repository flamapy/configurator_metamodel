import sys
import unittest
from typing import Any
from unittest.mock import MagicMock

# Import modules to test
# Adjust python path if necessary
sys.path.append('/home/zebax/flamapy/configurator_metamodel')

# Mocking dependencies for isolation
from flamapy.metamodels.fm_metamodel.models.feature_model import Feature, FeatureModel, FeatureType
from flamapy.metamodels.configurator_metamodel.models.configurator_model import ConfiguratorModel, Question, Option, OptionStatus
from flamapy.metamodels.configurator_metamodel.operations.configure import Configure

class TestConfiguratorRefactor(unittest.TestCase):

    def setUp(self):
        self.model = ConfiguratorModel()
        
        # Create features
        self.f_root = Feature("Root", feature_type=FeatureType.BOOLEAN)
        self.f_child1 = Feature("Child1", parent=self.f_root, feature_type=FeatureType.BOOLEAN)
        self.f_typed = Feature("TypedFeat", parent=self.f_root, feature_type=FeatureType.INTEGER)
        
        # Create questions
        q1 = Question(self.f_root)
        o1 = Option(self.f_child1)
        o2 = Option(self.f_typed)
        q1.add_option(o1)
        q1.add_option(o2)
        
        self.model.add_question(q1)

    def test_options_by_name(self):
        """Verify O(1) lookup dictionary is populated."""
        self.assertIn("Child1", self.model.options_by_name)
        self.assertIn("TypedFeat", self.model.options_by_name)
        self.assertEqual(self.model.options_by_name["Child1"].feature.name, "Child1")

    def test_set_state_typed_value(self):
        """Verify set_state stores typed values."""
        self.model.set_state("TypedFeat", 100)
        option = self.model.options_by_name["TypedFeat"]
        self.assertEqual(option.value, 100)
        self.assertEqual(option.status, OptionStatus.SELECTED)
        
        self.model.set_state("Child1", False)
        option_bool = self.model.options_by_name["Child1"]
        self.assertEqual(option_bool.value, False)
        self.assertEqual(option_bool.status, OptionStatus.DESELECTED)

    def test_configure_answer_dict(self):
        """Test answer_question with dictionary input."""
        config_op = Configure()
        config_op.configurator_model = self.model
        config_op.pysat = MagicMock()
        config_op.pysat.propagate.return_value = (True, []) # Mock successful propagation
        
        # Setup model state for execution
        self.model.pysat_metamodel = MagicMock()
        self.model.pysat_metamodel.variables = {"Child1": 1, "TypedFeat": 2}
        self.model.pysat_metamodel.features = {1: "Child1", 2: "TypedFeat"}
        
        self.model.current_question_index = 0
        
        # Answer with dict
        answer = {"TypedFeat": 42}
        success = config_op.answer_question(answer)
        
        self.assertTrue(success)
        self.assertEqual(self.model.options_by_name["TypedFeat"].value, 42)
        self.assertEqual(self.model.options_by_name["TypedFeat"].status, OptionStatus.SELECTED)
        
        # Check history
        last_config = self.model.history[-1] # Note: history saved BEFORE update in code
        # History stores pre-change state, which was empty/undecided
        self.assertEqual(last_config["TypedFeat"], None)
        
    def test_undo_restores_values(self):
         # Set initial state
        self.model.set_state("TypedFeat", 10)
        config_op = Configure()
        config_op.configurator_model = self.model
        
        # Save history manually as we are testing undo isolated
        self.model.history.append({"TypedFeat": 10})
        
        # Change state
        self.model.set_state("TypedFeat", 99)
        
        
        config_op.undo_answer()
        
        self.assertEqual(self.model.options_by_name["TypedFeat"].value, 10)


if __name__ == '__main__':
    unittest.main()
