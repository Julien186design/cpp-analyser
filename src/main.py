import os
import re
from graphviz import Digraph

# Configuration: Use absolute paths as requested
PROJECT_DIR = f"/home/[...]/CLion Projects/Image Processing"  # Change this to your actual path
OUTPUT_IMAGE = f"{PROJECT_DIR}/dependency tree"


class CPPAnalyzer:
    def __init__(self, directory):
        self.directory = directory
        self.files = [f for f in os.listdir(directory) if f.endswith(('.cpp', '.h', '.hpp'))]
        self.dependencies = {}

    def analyze_architecture(self):
        """Extracts #include dependencies to map project architecture."""
        include_pattern = re.compile(r'#include\s*["<]([^">]+)[">]')

        for file in self.files:
            path = os.path.join(self.directory, file)
            self.dependencies[file] = []
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                includes = include_pattern.findall(content)
                self.dependencies[file] = includes

    def analyze_variable_scope(self):
        """Simple heuristic to detect global vs local variables (member variables in headers)."""
        print(f"{'File':<25} | {'Global/Member Variables'}")
        print("-" * 60)

        # Pattern for basic variable declarations (simplified)
        var_pattern = re.compile(
            r'(?:std::|uint8_t|int|double|float|bool|string|size_t)\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*[;=]')

        for file in self.files:
            path = os.path.join(self.directory, file)
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                # Find matches outside of functions (rough estimation for architecture relevance)
                vars_found = var_pattern.findall(content)
                unique_vars = sorted(list(set(vars_found)))[:5]  # Limit output for readability
                print(f"{file:<25} | {', '.join(unique_vars)}")

    def generate_dependency_graph(self, output_path):
        """Creates a visual PDF/PNG of the project's include architecture."""
        dot = Digraph(comment='C++ Project Architecture', format='png')
        dot.attr(rankdir='LR', size='10,10')

        for file, includes in self.dependencies.items():
            # Clean node name for internal files
            dot.node(file, file, shape='box', color='lightblue', style='filled')
            for inc in includes:
                # Only link to project files to keep the graph clean
                if inc in self.files or inc.replace('.h', '.cpp') in self.files:
                    dot.edge(file, inc)

        dot.render(output_path, view=False)
        print(f"\n[INFO] Dependency tree saved at: {output_path}.png")

    def generate_dependency_graph_v2(self, output_path):
        """Creates a visually enhanced dependency graph."""

        dot = Digraph(comment='C++ Project Architecture', format='png')

        # Global graph style
        dot.attr(
            rankdir='LR',
            bgcolor='#0f172a',  # dark navy background
            pad='0.5',
            nodesep='0.6',
            ranksep='1.0',
            splines='spline'
        )

        # Default node style
        dot.attr('node',
                 shape='box',
                 style='filled,rounded',
                 fontname='Helvetica',
                 fontsize='10',
                 fontcolor='white',
                 color='#1e293b'
                 )

        # Default edge style
        dot.attr('edge',
                 color='#94a3b8',
                 penwidth='3',
                 arrowsize='0.8'
                 )

        for file, includes in self.dependencies.items():

            # Differentiate headers and source files
            if file.endswith('.h'):
                fill = '#2563eb'  # blue
            elif file.endswith('.cpp'):
                fill = '#16a34a'  # green
            else:
                fill = '#475569'  # neutral

            dot.node(file, file, fillcolor=fill)

            for inc in includes:
                if inc in self.files or inc.replace('.h', '.cpp') in self.files:
                    dot.edge(file, inc)

        dot.render(output_path, view=False)
        print(f"\n[INFO] Dependency tree saved at: {output_path}.png")


if __name__ == "__main__":
    # Check if directory exists
    if not os.path.exists(PROJECT_DIR):
        print(f"[ERROR] Directory not found: {PROJECT_DIR}")
    else:
        analyzer = CPPAnalyzer(PROJECT_DIR)

        print("--- 1. Architecture Analysis (Includes) ---")
        analyzer.analyze_architecture()

        print("\n--- 2. Variable Scope Analysis (Heuristic) ---")
        analyzer.analyze_variable_scope()

        print("\n--- 3. Generating Visualization ---")
        analyzer.generate_dependency_graph(OUTPUT_IMAGE)

        analyzer.generate_dependency_graph_v2(f"{OUTPUT_IMAGE}-v2")
