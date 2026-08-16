import os
from analyser import CPPAnalyzer

# Configuration: Use absolute paths as requested
PROJECT_DIR = "[...]/Image and video processing" # Change this to your actual path
OUTPUT_DIR = os.path.join(PROJECT_DIR, "Dependency trees")


# ------------------------------------------------------------------
# Entry Point
# ------------------------------------------------------------------
if __name__ == "__main__":

    try:
        analyzer = CPPAnalyzer(PROJECT_DIR, OUTPUT_DIR)
        print("1. Architecture analysis")
        analyzer.analyze_architecture()
        print("\n2. Variable scope heuristic")
        analyzer.analyze_variable_scope()
        print("\n3. Graph generation")
        analyzer.generate_dependency_graph("v1_basic", styled=False)
        analyzer.generate_dependency_graph("v2_styled", styled=True)
        print("\n4. Detailed object graph")
        analyzer.generate_detailed_dependency_graph("Detailed_styled", styled=True)
        print("\n5. Detailed dependency table")
        analyzer.generate_detailed_dependency_table()
        print("\n6. Function origin table")
        analyzer.generate_function_origin_table()
        print("\n7. Function origin graph")
        analyzer.generate_function_origin_graph("function_origin_styled", styled=True)
        print("\n8. External libraries report")
        analyzer.generate_library_report()
        print("\n9. Code quality analysis")
        analyzer.analyze_code_quality()
    except FileNotFoundError as e:
        print(f"[ERROR] {e}")
