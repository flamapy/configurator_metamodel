import sys
from flamapy.metamodels.configurator_metamodel.transformation.fm_to_configurator import FmToConfigurator
from flamapy.metamodels.fm_metamodel.transformations import UVLReader
from flamapy.metamodels.configurator_metamodel.operations.configure import Configure

def main():
    feature_model_path = './uvl/aquaia.uvl'
    
    print(f"Loading Feature Model from {feature_model_path}...")
    try:
        fm = UVLReader(feature_model_path).transform()
    except Exception as e:
        print(f"Error loading UVL: {e}")
        return

    print("Transforming to Configurator Model...")
    configurator_model = FmToConfigurator(fm).transform()
    
    # Initialize and execute the operation (connects to SAT solver)
    print("Initializing Configuration Operation...")
    configure_op = Configure()
    configure_op.execute(configurator_model)
    
    # Start the configuration process
    configure_op.start()
    
    print("\nStarting Interactive Configuration...")
    print("-----------------------------------")
    
    while not configure_op.is_finished():
        status = configure_op.get_current_status()
        
        print(f"\n[Question {status['currentQuestionIndex'] + 1}] {status['currentQuestion']} ({status['currentQuestionType']})")
        print("Available Options:")
        
        possible_options = status['possibleOptions']
        if not possible_options:
            print("  (No valid options available for this question)")
            # Should probably force next if no options, but logic is in next_question recursion usually
            # If we are here, maybe we are stuck or finished?
            if configure_op.is_finished(): 
                break
        
        for idx, opt in enumerate(possible_options):
            # opt contains: id, name, featureType
            ft_type = opt['featureType'].value if hasattr(opt['featureType'], 'value') else str(opt['featureType'])
            print(f"  {idx}: {opt['name']} [{ft_type}]")
            
        user_input = input("\nEnter option index to select (or 'q' to quit, 'u' to undo): ").strip()
        
        if user_input.lower() == 'q':
            print("Exiting.")
            break
        
        if user_input.lower() == 'u':
            print("Undoing last step...")
            if configure_op.previous_question():
                print("Undo successful.")
            else:
                print("Cannot undo further.")
            continue
            
        try:
            idx = int(user_input)
            if 0 <= idx < len(possible_options):
                selected_opt = possible_options[idx]
                name = selected_opt['name']
                ftype_enum = selected_opt['featureType']
                ftype_name = ftype_enum.name if hasattr(ftype_enum, 'name') else str(ftype_enum)
                
                value = True # Default for BOOLEAN
                
                # Check strict type compatibility
                if ftype_name != 'BOOLEAN':
                    while True:
                        val_str = input(f"  >> Enter value for '{name}' ({ftype_name}): ")
                        try:
                            if ftype_name == 'INTEGER':
                                value = int(val_str)
                            elif ftype_name == 'REAL':
                                value = float(val_str)
                            elif ftype_name == 'STRING':
                                value = str(val_str)
                            else:
                                value = val_str # Fallback
                            break
                        except ValueError:
                            print(f"     Invalid format for {ftype_name}. Please try again.")
                
                # Build dictionary answer
                answer = {name: value}
                print(f"Applying answer: {answer}")
                
                valid = configure_op.answer_question(answer)
                if valid:
                    print("  -> Configuration updated successfully.")
                    configure_op.next_question()
                else:
                    print("  -> CONFLICT: This choice leads to an invalid configuration.")
            else:
                print("Error: Invalid index.")
        except ValueError:
            print("Error: Input must be a number.")
            
    if configure_op.is_finished():
        print("\nConfiguration Complete!")
        # Optional: Print final configuration
        print("Final Configuration:")
        # We can inspect history or model state
        config = configure_op._get_configuration() # Helper to get current
        print(config)
        for k, v in config.items():
            if v is not None:
                print(f"  {k}: {v}")

if __name__ == "__main__":
    main()
