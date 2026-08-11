import os
import re
from graphviz import Digraph

# Configuration: Use absolute paths as requested
PROJECT_DIR = "/home/[...]/CLionProjects/Image and video processing" # Change this to your actual path
OUTPUT_DIR = os.path.join(PROJECT_DIR, "Dependency trees")


class CPPAnalyzer:
    def __init__(self, directory: str, output_dir: str):
        if not os.path.isdir(directory):
            raise FileNotFoundError(f"Directory not found: {directory}")
        os.makedirs(output_dir, exist_ok=True)
        self.directory = directory
        self.output_dir = output_dir
        self.files = [
            f for f in os.listdir(directory)
            if f.endswith(('.cpp', '.h', '.hpp'))
        ]
        self.dependencies = None  # Lazy computation

    # ------------------------------------------------------------
    # Architecture Analysis
    # ------------------------------------------------------------
    def analyze_architecture(self):
        include_pattern = re.compile(r'#include\s*["<]([^">]+)[">]')
        dependencies = {}
        for file in self.files:
            path = os.path.join(self.directory, file)
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                includes = include_pattern.findall(content)
                # Keep only project-local includes
                local_includes = [
                    inc for inc in includes
                    if inc in self.files
                    or inc.replace('.h', '.cpp') in self.files
                ]
                dependencies[file] = local_includes
        self.dependencies = dependencies

    def _ensure_dependencies(self):
        if self.dependencies is None:
            self.analyze_architecture()

    # ------------------------------------------------------------
    # Variable Scope Heuristic
    # ------------------------------------------------------------
    def analyze_variable_scope(self):
        var_pattern = re.compile(
            r'(?:std::|uint8_t|int|double|float|bool|string|size_t)\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*[;=]'
        )
        print(f"{'File':<30} | Variables détectées")
        print("-" * 60)
        for file in self.files:
            path = os.path.join(self.directory, file)
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                vars_found = var_pattern.findall(content)
                unique_vars = sorted(set(vars_found))[:5]
                print(f"{file:<30} | {', '.join(unique_vars)}")

    # ------------------------------------------------------------
    # Graph Generation
    # ------------------------------------------------------------
    def generate_dependency_graph(self, name="dependency_graph", styled=False):
        self._ensure_dependencies()
        output_path = os.path.join(self.output_dir, name)
        dot = Digraph(comment='C++ Project Architecture', format='png')
        if styled:
            dot.attr(
                rankdir='LR',
                bgcolor='#0f172a',
                pad='0.5',
                nodesep='0.6',
                ranksep='1.0',
                splines='spline'
            )
            dot.attr('node',
                     shape='box',
                     style='filled,rounded',
                     fontname='Helvetica',
                     fontsize='10',
                     fontcolor='white',
                     color='#1e293b')
            dot.attr('edge',
                     color='#94a3b8',
                     penwidth='2',
                     arrowsize='0.8')
        else:
            dot.attr(rankdir='LR')
        for file, includes in self.dependencies.items():
            if styled:
                if file.endswith(('.h', '.hpp')):
                    fill = '#2563eb'
                elif file.endswith('.cpp'):
                    fill = '#16a34a'
                else:
                    fill = '#475569'
                dot.node(file, file, fillcolor=fill)
            else:
                dot.node(file, file)
            for inc in includes:
                dot.edge(file, inc)
        dot.render(output_path, view=False)
        print(f"[INFO] Generated: {output_path}.png")

    # ------------------------------------------------------------
    # Detailed Dependency Graph (with object/class references)
    # ------------------------------------------------------------
    def analyze_class_usage(self):
        """
        For each file, extract:
          - declared classes (via 'class ClassName')
          - used identifiers that match a declared class in another file
        Returns: dict[file] -> list of (used_class, source_file)
        """
        # Step 1: map each class name -> the file that declares it
        class_decl_pattern = re.compile(r'\bclass\s+([A-Z][a-zA-Z0-9_]*)')
        class_origins = {}  # ClassName -> filename
        for file in self.files:
            path = os.path.join(self.directory, file)
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            for cls in class_decl_pattern.findall(content):
                class_origins[cls] = file
        # Step 2: for each file, find usages of known classes
        usage_map = {}  # file -> list of (ClassName, origin_file)
        for file in self.files:
            path = os.path.join(self.directory, file)
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            usages = []
            for cls, origin in class_origins.items():
                if origin == file:
                    continue  # Skip self-references
                # Match usage as a type: variable declarations, inheritance, template args
                usage_pattern = re.compile(
                    rf'(?:[:,<\s]|^){re.escape(cls)}(?:[>\s;,{{(]|$)', re.MULTILINE
                )
                if usage_pattern.search(content):
                    usages.append((cls, origin))
            usage_map[file] = usages
        return class_origins, usage_map

    # ------------------------------------------------------------
    # Detailed Object Dependency Graph (Header -> Class -> Header)
    # ------------------------------------------------------------
    def generate_detailed_dependency_graph(self, name="detailed_graph", styled=False):
        """
        Creates a graph showing which objects (classes/structs) used in
        header files come from which header file.
        """
        output_path = os.path.join(self.output_dir, name)
        dot = Digraph(comment="Detailed Header Dependencies", format="png")
        if styled:
            dot.attr(
                rankdir='LR',
                bgcolor='#0f172a',
                pad='0.6',
                nodesep='0.7',
                ranksep='1.2',
                splines='spline'
            )
            dot.attr('node',
                     shape='box',
                     style='filled,rounded',
                     fontname='Helvetica',
                     fontsize='10',
                     fontcolor='white',
                     color='#1e293b')
            dot.attr('edge',
                     color='#94a3b8',
                     penwidth='2',
                     arrowsize='0.8')
        else:
            dot.attr(rankdir='LR')
        # --------------------------------------------------------
        # Step 1: Extract all class/struct definitions
        # --------------------------------------------------------
        class_pattern = re.compile(r'\b(class|struct)\s+([A-Za-z_][A-Za-z0-9_]*)')
        class_to_file = {}
        for file in self.files:
            if not file.endswith(('.h', '.hpp')):
                continue
            path = os.path.join(self.directory, file)
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                matches = class_pattern.findall(content)
                for _, cls in matches:
                    class_to_file[cls] = file
        # --------------------------------------------------------
        # Step 2: Detect usage of those classes in headers
        # --------------------------------------------------------
        for file in self.files:
            if not file.endswith(('.h', '.hpp')):
                continue
            path = os.path.join(self.directory, file)
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            if styled:
                dot.node(file, file, fillcolor='#2563eb')
            else:
                dot.node(file)
            for cls, origin_file in class_to_file.items():
                if cls in content and origin_file != file:
                    class_node = f"{cls}"
                    if styled:
                        dot.node(class_node, cls, fillcolor='#9333ea')
                    else:
                        dot.node(class_node)
                    dot.edge(file, class_node)
                    dot.edge(class_node, origin_file)
        dot.render(output_path, view=False)
        print(f"[INFO] Generated: {output_path}.png")

    # ------------------------------------------------------------
    # Detailed dependency table (Header -> Object -> Origin file)
    # ------------------------------------------------------------
    def generate_detailed_dependency_table(self):
        """
        Prints a table showing which objects used in header files
        are defined in other header files.
        """
        # Regex detecting class or struct definitions
        class_pattern = re.compile(r'\b(class|struct)\s+([A-Za-z_][A-Za-z0-9_]*)')
        class_to_file = {}
        # --------------------------------------------------------
        # Step 1: Map each class/struct to the header where it is defined
        # --------------------------------------------------------
        for file in self.files:
            if not file.endswith(('.h', '.hpp')):
                continue
            path = os.path.join(self.directory, file)
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            matches = class_pattern.findall(content)
            for _, cls in matches:
                class_to_file[cls] = file
        # --------------------------------------------------------
        # Step 2: Detect usage of these objects in headers
        # --------------------------------------------------------
        results = []
        for file in self.files:
            if not file.endswith(('.h', '.hpp')):
                continue
            path = os.path.join(self.directory, file)
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            for cls, origin_file in class_to_file.items():
                if cls in content and origin_file != file:
                    results.append((file, cls, origin_file))
        # --------------------------------------------------------
        # Step 3: Print table
        # --------------------------------------------------------
        print(f"{'Header file':<30} | {'Object used':<25} | {'Defined in'}")
        print("-" * 80)
        for header, obj, origin in sorted(results):
            print(f"{header:<30} | {obj:<25} | {origin}")

    # ------------------------------------------------------------
    # Function Origin Analysis
    # ------------------------------------------------------------
    def analyze_function_origins(self):
        """
        Heuristic mapping of function calls to their declaration/definition files.
        Regex-based (no AST): does not resolve overloads, function pointers,
        or macro-generated functions.
        Returns: dict[caller_file] -> list of (func_name, decl_file, def_file)
        """
        # Keywords to exclude from being treated as function calls
        cpp_keywords = {
            'if', 'for', 'while', 'switch', 'sizeof', 'return', 'catch',
            'static_cast', 'dynamic_cast', 'reinterpret_cast', 'const_cast',
            'new', 'delete', 'throw', 'noexcept', 'decltype', 'typeid'
        }

        # Step 1: map function name -> declaration file (from .h/.hpp prototypes,
        # i.e. a signature ending in ';' rather than '{')
        decl_pattern = re.compile(
            r'^\s*(?:[A-Za-z_][\w:<>,\s\*&]*?)\s+([A-Za-z_]\w*)\s*\([^;{}]*\)\s*;',
            re.MULTILINE
        )
        decl_origins = {}
        for file in self.files:
            if not file.endswith(('.h', '.hpp')):
                continue
            path = os.path.join(self.directory, file)
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            for func in decl_pattern.findall(content):
                if func not in cpp_keywords:
                    decl_origins[func] = file

        # Step 2: map function name -> definition file (from .cpp, or
        # ClassName::func in headers), i.e. a signature ending in '{'
        def_pattern = re.compile(
            r'^\s*(?:[A-Za-z_][\w:<>,\s\*&]*?)\s+(?:[A-Za-z_]\w*::)?([A-Za-z_]\w*)\s*'
            r'\([^;{}]*\)\s*(?:const\s*)?\{',
            re.MULTILINE
        )
        def_origins = {}
        for file in self.files:
            path = os.path.join(self.directory, file)
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            for func in def_pattern.findall(content):
                if func not in cpp_keywords:
                    def_origins[func] = file

        # Step 3: known function names = union of declared + defined
        known_functions = set(decl_origins) | set(def_origins)

        # Step 4: for each file, find call sites and resolve origins
        call_pattern = re.compile(r'\b([a-zA-Z_]\w*)\s*\(')
        origin_map = {}
        for file in self.files:
            path = os.path.join(self.directory, file)
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            calls_found = set(call_pattern.findall(content)) & known_functions
            entries = []
            for func_name in sorted(calls_found):
                decl_file = decl_origins.get(func_name, "N/A")
                def_file = def_origins.get(func_name, decl_file if decl_file != "N/A" else file)
                # Skip references fully local to the file being scanned
                if decl_file == file and def_file == file:
                    continue
                entries.append((func_name, decl_file, def_file))
            if entries:
                origin_map[file] = entries
        return origin_map

    def generate_function_origin_table(self):
        """
        Prints a table: Caller file -> Function -> Declared in -> Defined in
        """
        origin_map = self.analyze_function_origins()
        print(f"{'Caller file':<25} | {'Function':<25} | {'Declared in':<20} | {'Defined in'}")
        print("-" * 100)
        rows = []
        for caller_file, entries in origin_map.items():
            for func_name, decl_file, def_file in entries:
                rows.append((caller_file, func_name, decl_file, def_file))
        for caller_file, func_name, decl_file, def_file in sorted(rows, key=lambda r: r[1]):
            print(f"{caller_file:<25} | {func_name:<25} | {decl_file:<20} | {def_file}")

    def generate_function_origin_graph(self, name="function_origin_graph", styled=False):
        """
        Draws Caller file -> Function -> Declaration file / Definition file.
        Each function is its own node so a single function called from
        several files (or resolving to both a header and a source file)
        fans in/out correctly instead of duplicating file-to-file edges.
        """
        origin_map = self.analyze_function_origins()
        output_path = os.path.join(self.output_dir, name)
        dot = Digraph(comment="Function Origin Graph", format="png")
        if styled:
            dot.attr(
                rankdir='LR',
                bgcolor='#0f172a',
                pad='0.6',
                nodesep='0.6',
                ranksep='1.2',
                splines='spline'
            )
            dot.attr('node',
                     shape='box',
                     style='filled,rounded',
                     fontname='Helvetica',
                     fontsize='10',
                     fontcolor='white',
                     color='#1e293b')
            dot.attr('edge',
                     color='#94a3b8',
                     penwidth='2',
                     arrowsize='0.8')
        else:
            dot.attr(rankdir='LR')

        added_file_nodes = set()
        added_func_nodes = set()

        def ensure_file_node(file):
            if file in added_file_nodes:
                return
            added_file_nodes.add(file)
            if styled:
                fill = '#2563eb' if file.endswith(('.h', '.hpp')) else '#16a34a'
                dot.node(file, file, fillcolor=fill)
            else:
                dot.node(file, file)

        for caller_file, entries in origin_map.items():
            ensure_file_node(caller_file)
            for func_name, decl_file, def_file in entries:
                # Namespace the function node per definition file so that
                # two unrelated functions sharing a name don't merge into
                # a single node.
                func_node = f"{def_file}::{func_name}"
                if func_node not in added_func_nodes:
                    added_func_nodes.add(func_node)
                    if styled:
                        dot.node(func_node, func_name, fillcolor='#9333ea', shape='ellipse')
                    else:
                        dot.node(func_node, func_name, shape='ellipse')
                dot.edge(caller_file, func_node)
                ensure_file_node(def_file)
                dot.edge(func_node, def_file, label="defines" if styled else None)
                if decl_file != "N/A":
                    ensure_file_node(decl_file)
                    dot.edge(func_node, decl_file, label="declares" if styled else None,
                              style="dashed")
        dot.render(output_path, view=False)
        print(f"[INFO] Generated: {output_path}.png")

    # ------------------------------------------------------------
    # External Libraries Report (per file)
    # ------------------------------------------------------------
    def generate_library_report(self, output_name="libraries_report.txt"):
        """
        Generates a text file listing C++ libraries (system/standard includes)
        used in each file.
        Only considers includes of the form: #include <...>
        """
        include_pattern = re.compile(r'#include\s*<([^>]+)>')
        output_path = os.path.join(self.output_dir, output_name)
        report = {}
        for file in self.files:
            path = os.path.join(self.directory, file)
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                libs = include_pattern.findall(content)
                unique_libs = sorted(set(libs))
                report[file] = unique_libs
        # Write to file
        with open(output_path, 'w', encoding='utf-8') as out:
            for file, libs in sorted(report.items()):
                out.write(f"{file}\n")
                out.write("-" * len(file) + "\n")
                if libs:
                    for lib in libs:
                        out.write(f"  - {lib}\n")
                else:
                    out.write("  (no external libraries)\n")
                out.write("\n")
        print(f"[INFO] Library report generated: {output_path}")


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
    except FileNotFoundError as e:
        print(f"[ERROR] {e}")
