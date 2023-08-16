from flamapy.core.operations.abstract_operation import Operation

from flamapy.metamodels.configurator_metamodel.models import ConfiguratorModel, Question, Option, OptionStatus


class Configure(Operation):

    def __init__(self) -> None:
        self.result = 0

    def get_result(self) -> int:
        return self.result

    def execute(self, model: ConfiguratorModel) -> 'Configure':
        print(model.questions)
        self.result = self._configure(model)
        return self

    
    def _ask_question(self, question: Question) -> list[Option]:
        """Ask the question and return the selected options."""
        print(question.name)
        available_options = list(filter(lambda option: option.status == OptionStatus.UNDECIDED, question.options))

        # Display available options with a number
        for i, option in enumerate(available_options, 1):
            print(f"{i}. {option.name}")

        answer = input("Please enter the numbers of the options you want to choose, separated by commas (e.g. '1,3,4'): ")

        # Splitting the input by commas and stripping spaces to get indices
        selected_indices = [int(x.strip()) - 1 for x in answer.split(",")]

        # Change the status for the selected options
        for index in selected_indices:
            # You might want to add checks to ensure valid selection. I.e., call a sat solver and propagate
            available_options[index].status = OptionStatus.SELECTED

        # Return the selected options
        return [available_options[index] for index in selected_indices]

    def _configure(self, model: ConfiguratorModel) -> None:
        """Configure the model"""
        for question in model.questions:
            question.answer = self._ask_question(question)