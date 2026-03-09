"""Unit tests for the configurator_metamodel package."""
import unittest
from typing import Any
from unittest.mock import MagicMock

from flamapy.metamodels.fm_metamodel.models.feature_model import Feature, FeatureModel, FeatureType
from flamapy.metamodels.configurator_metamodel.models.configurator_model import (
    ConfiguratorModel,
    Option,
    OptionStatus,
    Question,
)
from flamapy.metamodels.configurator_metamodel.operations.configure import Configure


class TestConfiguratorModel(unittest.TestCase):
    """Tests for ConfiguratorModel and its data classes."""

    def setUp(self):
        self.model = ConfiguratorModel()

        self.f_root = Feature("Root", feature_type=FeatureType.BOOLEAN)
        self.f_child1 = Feature("Child1", parent=self.f_root, feature_type=FeatureType.BOOLEAN)
        self.f_typed = Feature("TypedFeat", parent=self.f_root, feature_type=FeatureType.INTEGER)

        q1 = Question(self.f_root)
        q1.add_option(Option(self.f_child1))
        q1.add_option(Option(self.f_typed))
        self.model.add_question(q1)

    # ------------------------------------------------------------------
    # add_question / options_by_name
    # ------------------------------------------------------------------

    def test_options_by_name_populated(self):
        self.assertIn("Child1", self.model.options_by_name)
        self.assertIn("TypedFeat", self.model.options_by_name)
        self.assertEqual(self.model.options_by_name["Child1"].feature.name, "Child1")

    # ------------------------------------------------------------------
    # set_state – value updates
    # ------------------------------------------------------------------

    def test_set_state_integer_value(self):
        self.model.set_state("TypedFeat", 100)
        option = self.model.options_by_name["TypedFeat"]
        self.assertEqual(option.value, 100)
        self.assertEqual(option.status, OptionStatus.SELECTED)

    def test_set_state_overwrites_existing_value(self):
        """set_state must allow value updates (regression for the original bug)."""
        self.model.set_state("TypedFeat", 100)
        self.model.set_state("TypedFeat", 50)
        self.assertEqual(self.model.options_by_name["TypedFeat"].value, 50)

    def test_set_state_boolean_false(self):
        self.model.set_state("Child1", False)
        option = self.model.options_by_name["Child1"]
        self.assertEqual(option.value, False)
        self.assertEqual(option.status, OptionStatus.DESELECTED)

    def test_set_state_boolean_true(self):
        self.model.set_state("Child1", True)
        option = self.model.options_by_name["Child1"]
        self.assertEqual(option.status, OptionStatus.SELECTED)

    def test_set_state_none_resets_to_undecided(self):
        self.model.set_state("Child1", True)
        self.model.set_state("Child1", None)
        option = self.model.options_by_name["Child1"]
        self.assertIsNone(option.value)
        self.assertEqual(option.status, OptionStatus.UNDECIDED)

    def test_set_state_unknown_feature_does_not_raise(self):
        """Unknown feature names should be silently ignored."""
        try:
            self.model.set_state("NonExistent", True)
        except Exception as exc:
            self.fail(f"set_state raised unexpectedly: {exc}")

    # ------------------------------------------------------------------
    # Option / Question string representations
    # ------------------------------------------------------------------

    def test_option_str(self):
        opt = Option(self.f_child1)
        self.assertIn("Child1", str(opt))

    def test_question_str(self):
        q = Question(self.f_root)
        self.assertIn("Root", str(q))


class _MockedConfigureBase(unittest.TestCase):
    """Base class that sets up a mocked Configure operation."""

    def setUp(self):
        self.model = ConfiguratorModel()

        f_root = Feature("Root", feature_type=FeatureType.BOOLEAN)
        f_child1 = Feature("Child1", parent=f_root, feature_type=FeatureType.BOOLEAN)
        f_typed = Feature("TypedFeat", parent=f_root, feature_type=FeatureType.INTEGER)

        q1 = Question(f_root)
        q1.add_option(Option(f_child1))
        q1.add_option(Option(f_typed))
        self.model.add_question(q1)

        self.model.pysat_metamodel = MagicMock()
        self.model.pysat_metamodel.variables = {"Child1": 1, "TypedFeat": 2}
        self.model.pysat_metamodel.features = {1: "Child1", 2: "TypedFeat"}
        self.model.current_question_index = 0

        self.op = Configure()
        self.op.configurator_model = self.model
        self.op.pysat = MagicMock()
        self.op.pysat.propagate.return_value = (True, [])


class TestConfigureOperation(_MockedConfigureBase):
    """Tests for the Configure operation."""

    # ------------------------------------------------------------------
    # answer_question
    # ------------------------------------------------------------------

    def test_answer_question_success(self):
        success = self.op.answer_question({"TypedFeat": 42})
        self.assertTrue(success)
        self.assertEqual(self.model.options_by_name["TypedFeat"].value, 42)
        self.assertEqual(self.model.options_by_name["TypedFeat"].status, OptionStatus.SELECTED)

    def test_answer_question_saves_history_before_update(self):
        self.op.answer_question({"TypedFeat": 42})
        # History entry was captured before the change, so value was None
        self.assertEqual(self.model.history[-1]["TypedFeat"], None)

    def test_answer_question_conflict_rolls_back(self):
        """A contradicting answer must be rolled back automatically."""
        self.op.pysat.propagate.return_value = (False, [])
        self.model.set_state("TypedFeat", 10)

        success = self.op.answer_question({"TypedFeat": 99})

        self.assertFalse(success)
        # Value should be restored to 10
        self.assertEqual(self.model.options_by_name["TypedFeat"].value, 10)

    # ------------------------------------------------------------------
    # undo_answer
    # ------------------------------------------------------------------

    def test_undo_restores_previous_value(self):
        self.model.set_state("TypedFeat", 10)
        self.model.history.append({"TypedFeat": 10})
        self.model.set_state("TypedFeat", 99)

        result = self.op.undo_answer()

        self.assertTrue(result)
        self.assertEqual(self.model.options_by_name["TypedFeat"].value, 10)

    def test_undo_with_empty_history_returns_false(self):
        self.assertFalse(self.op.undo_answer())

    # ------------------------------------------------------------------
    # Navigation helpers
    # ------------------------------------------------------------------

    def test_is_first_question(self):
        self.model.current_question_index = 0
        self.assertTrue(self.op.is_first_question())

    def test_is_last_question(self):
        self.model.current_question_index = len(self.model.questions) - 1
        self.assertTrue(self.op.is_last_question())

    def test_is_finished(self):
        self.model.current_question_index = len(self.model.questions)
        self.assertTrue(self.op.is_finished())

    # ------------------------------------------------------------------
    # get_current_status
    # ------------------------------------------------------------------

    def test_get_current_status_keys(self):
        status = self.op.get_current_status()
        for key in ('currentQuestion', 'currentQuestionType', 'currentQuestionIndex',
                    'isLastQuestion', 'possibleOptions'):
            self.assertIn(key, status, f"Missing key: {key}")

    def test_get_current_status_no_duplicate_possible_options(self):
        """possibleOptions must appear exactly once."""
        status = self.op.get_current_status()
        # Verify it is a list (not overwritten by accident)
        self.assertIsInstance(status['possibleOptions'], list)


if __name__ == '__main__':
    unittest.main()
