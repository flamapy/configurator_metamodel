from flamapy.core.operations.abstract_operation import Operation

from flamapy.metamodels.configurator_metamodel.models import ConfiguratorModel, Question, Option, OptionStatus


class Configure(Operation):

    def __init__(self) -> None:
        self.result = 0

    def get_result(self) -> int:
        return self.result

    def execute(self, model: ConfiguratorModel) -> 'Configure':
        self.configurator_model = model
        self.pysat = model.pysat_solver
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
        #values= [available_options[index] for index in selected_indices]
        result = self._propagate()
        if result is None:
            # Undo the changes
            for index in selected_indices:
                # You might want to add checks to ensure valid selection. I.e., call a sat solver and propagate
                available_options[index].status = OptionStatus.UNDECIDED
        return result
    
    def _configure(self, model: ConfiguratorModel) -> None:
        """Configure the model"""
        for question in model.questions:
            implied_values = self._ask_question(question)

            # now, its time to update the values in the confiuartor model
            if implied_values is None:
                print("The assignment leads to a contradiction! you can not configure the product that way. Please try again.")
                implied_values = self._ask_question(question)

            for key, value in implied_values.items():
                feature_name = self.pysat.features[key]
                self.configurator_model.set_state(feature_name, value)
        
        #Now we showld inform the user about the configuration. 
        # it may happen that there are options not fixed by the user. In that case, we can complete the configuration 
        # with a call to the solver or we can ask the user to select the options.
        print("The configuration is process is done! This is the configuration you selected: ")

        return self.configurator_model._get_configuration()
    def _propagate(self):
        from pysat.solvers import Solver
        # get current model assumptions
        # total_assumptions = [assumptions] + self.configurator_model._get_current_assumptions()
        assumptions=self.configurator_model._get_current_assumptions()
       # print(total_assumptions)
        # Create a solver instance and add the formula
        with Solver(name="glucose4", bootstrap_with=self.pysat._cnf.clauses) as solver:
            
            # Perform propagation using the solver's 'propagate' method
            # This will return a list of literals that are implied by the assumption(s)
            # Propagate the assignment
            status, implied_lits = solver.propagate(assumptions=assumptions)

            # If the status is False, the assignment leads to a contradiction
            if status is False:
                return None

            # Extract values from implied literals
            implied_values = {abs(lit): (lit > 0) for lit in implied_lits}

            # Determine non-fixed variables
            #all_vars = set(range(1, self.pysat._cnf.nv + 1))
            #fixed_vars = set(implied_values.keys())
            #non_fixed_vars = all_vars - fixed_vars

            #print("Fixed variables and their values:", implied_values)
            #print("Non-fixed variables:", non_fixed_vars)
            return implied_values