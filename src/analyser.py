import os
import re
import csv
from graphviz import Digraph


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
            r'(?:std::|uint8_t|int|double|float|bool|string|size_t)\s+'
            r'([a-zA-Z_][a-zA-Z0-9_]*)\s*[;=]'
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

        dot = Digraph(
            comment='C++ Project Architecture',
            format='png'
        )

        if styled:
            dot.attr(
                rankdir='LR',
                bgcolor='#0f172a',
                pad='0.5',
                nodesep='0.6',
                ranksep='1.0',
                splines='spline'
            )

            dot.attr(
                'node',
                shape='box',
                style='filled,rounded',
                fontname='Helvetica',
                fontsize='10',
                fontcolor='white',
                color='#1e293b'
            )

            dot.attr(
                'edge',
                color='#94a3b8',
                penwidth='2',
                arrowsize='0.8'
            )
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

        Returns:
            dict[file] -> list of (used_class, source_file)
        """

        # Step 1: map each class name -> the file that declares it
        class_decl_pattern = re.compile(
            r'\bclass\s+([A-Z][a-zA-Z0-9_]*)'
        )

        class_origins = {}

        for file in self.files:
            path = os.path.join(self.directory, file)

            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            for cls in class_decl_pattern.findall(content):
                class_origins[cls] = file

        # Step 2: for each file, find usages of known classes
        usage_map = {}

        for file in self.files:
            path = os.path.join(self.directory, file)

            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            usages = []

            for cls, origin in class_origins.items():
                if origin == file:
                    continue

                usage_pattern = re.compile(
                    rf'(?:[:,<\s]|^){re.escape(cls)}'
                    rf'(?:[>\s;,{{(]|$)',
                    re.MULTILINE
                )

                if usage_pattern.search(content):
                    usages.append((cls, origin))

            usage_map[file] = usages

        return class_origins, usage_map

    # ------------------------------------------------------------
    # Detailed Object Dependency Graph (Header -> Class -> Header)
    # ------------------------------------------------------------
    def generate_detailed_dependency_graph(
            self,
            name="detailed_graph",
            styled=False
    ):
        """
        Creates a graph showing which objects (classes/structs) used in
        header files come from which header file.
        """

        output_path = os.path.join(self.output_dir, name)

        dot = Digraph(
            comment="Detailed Header Dependencies",
            format="png"
        )

        if styled:
            dot.attr(
                rankdir='LR',
                bgcolor='#0f172a',
                pad='0.6',
                nodesep='0.7',
                ranksep='1.2',
                splines='spline'
            )

            dot.attr(
                'node',
                shape='box',
                style='filled,rounded',
                fontname='Helvetica',
                fontsize='10',
                fontcolor='white',
                color='#1e293b'
            )

            dot.attr(
                'edge',
                color='#94a3b8',
                penwidth='2',
                arrowsize='0.8'
            )
        else:
            dot.attr(rankdir='LR')

        # --------------------------------------------------------
        # Step 1: Extract all class/struct definitions
        # --------------------------------------------------------
        class_pattern = re.compile(
            r'\b(class|struct)\s+([A-Za-z_][A-Za-z0-9_]*)'
        )

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
                        dot.node(
                            class_node,
                            cls,
                            fillcolor='#9333ea'
                        )
                    else:
                        dot.node(class_node)

                    dot.edge(file, class_node)
                    dot.edge(class_node, origin_file)

        dot.render(output_path, view=False)

        print(f"[INFO] Generated: {output_path}.png")

    # ------------------------------------------------------------
    # Detailed Dependency Table (Header -> Object -> Origin file)
    # ------------------------------------------------------------
    def generate_detailed_dependency_table(self):
        """
        Prints a table showing which objects used in header files
        are defined in other header files.
        """

        class_pattern = re.compile(
            r'\b(class|struct)\s+([A-Za-z_][A-Za-z0-9_]*)'
        )

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
        print(
            f"{'Header file':<30} | "
            f"{'Object used':<25} | "
            f"{'Defined in'}"
        )

        print("-" * 80)

        for header, obj, origin in sorted(results):
            print(
                f"{header:<30} | "
                f"{obj:<25} | "
                f"{origin}"
            )

    # ------------------------------------------------------------
    # Function Origin Analysis
    # ------------------------------------------------------------
    def analyze_function_origins(self):
        """
        Heuristic mapping of function calls to their declaration/definition files.

        Regex-based (no AST):
        - does not resolve overloads
        - does not resolve function pointers
        - does not resolve macro-generated functions

        Returns:
            dict[caller_file] -> list of
            (func_name, decl_file, def_file)
        """

        cpp_keywords = {
            'if', 'for', 'while', 'switch', 'sizeof', 'return',
            'catch', 'static_cast', 'dynamic_cast',
            'reinterpret_cast', 'const_cast', 'new', 'delete',
            'throw', 'noexcept', 'decltype', 'typeid'
        }

        # Step 1: map function name -> declaration file
        decl_pattern = re.compile(
            r'^\s*(?:[A-Za-z_][\w:<>,\s\*&]*?)\s+'
            r'([A-Za-z_]\w*)\s*\([^;{}]*\)\s*;',
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

        # Step 2: map function name -> definition file
        def_pattern = re.compile(
            r'^\s*(?:[A-Za-z_][\w:<>,\s\*&]*?)\s+'
            r'(?:[A-Za-z_]\w*::)?([A-Za-z_]\w*)\s*'
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

        # Step 3: known function names
        known_functions = set(decl_origins) | set(def_origins)

        # Step 4: find call sites and resolve origins
        call_pattern = re.compile(
            r'\b([a-zA-Z_]\w*)\s*\('
        )

        origin_map = {}

        for file in self.files:
            path = os.path.join(self.directory, file)

            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            calls_found = (
                set(call_pattern.findall(content))
                & known_functions
            )

            entries = []

            for func_name in sorted(calls_found):
                decl_file = decl_origins.get(func_name, "N/A")

                def_file = def_origins.get(
                    func_name,
                    decl_file if decl_file != "N/A" else file
                )

                # Skip references fully local to the file being scanned
                if decl_file == file and def_file == file:
                    continue

                entries.append(
                    (func_name, decl_file, def_file)
                )

            if entries:
                origin_map[file] = entries

        return origin_map

    def generate_function_origin_table(
            self,
            name="function_origin_table.txt"
    ):
        """
        Writes a table to a TXT file:
        Caller file -> Function -> Declared in -> Defined in

        Also writes a CSV file with the same data.

        Column headers include counts:
            Caller file (N files) |
            Function (M functions) |
            Declared in |
            Defined in
        """

        output_path = os.path.join(self.output_dir, name)

        csv_path = os.path.join(
            self.output_dir,
            name.replace(".txt", ".csv")
        )

        origin_map = self.analyze_function_origins()

        rows = []
        unique_functions = set()

        for caller_file, entries in origin_map.items():
            for func_name, decl_file, def_file in entries:
                rows.append(
                    (
                        caller_file,
                        func_name,
                        decl_file,
                        def_file
                    )
                )

                unique_functions.add(func_name)

        # Statistics
        nb_caller_files = len(origin_map)
        nb_functions = len(unique_functions)

        # --------------------------------------------------------
        # TXT
        # --------------------------------------------------------
        with open(output_path, "w", encoding="utf-8") as f:
            header = (
                f"{'Caller file : ' + str(nb_caller_files):<30} | "
                f"{'Function : ' + str(nb_functions):<30} | "
                f"{'Declared in':<20} | "
                f"{'Defined in'}\n"
            )

            f.write(header)
            f.write("-" * 110 + "\n")

            for caller_file, func_name, decl_file, def_file in sorted(
                    rows,
                    key=lambda r: r[1]
            ):
                f.write(
                    f"{caller_file:<30} | "
                    f"{func_name:<30} | "
                    f"{decl_file:<20} | "
                    f"{def_file}\n"
                )

        # --------------------------------------------------------
        # CSV
        # --------------------------------------------------------
        with open(
                csv_path,
                "w",
                encoding="utf-8",
                newline=""
        ) as f:
            writer = csv.writer(f)

            writer.writerow([
                f"Caller file ({nb_caller_files} files)",
                f"Function ({nb_functions} functions)",
                "Declared in",
                "Defined in"
            ])

            for caller_file, func_name, decl_file, def_file in sorted(
                    rows,
                    key=lambda r: r[1]
            ):
                writer.writerow([
                    caller_file,
                    func_name,
                    decl_file,
                    def_file
                ])

    # ------------------------------------------------------------
    # Function Origin Graph
    # ------------------------------------------------------------
    def generate_function_origin_graph(
            self,
            name="function_origin_graph",
            styled=False
    ):
        """
        Draws:

            Caller file -> Function -> Declaration file
                                      -> Definition file

        Each function is its own node so a single function called from
        several files (or resolving to both a header and a source file)
        fans in/out correctly instead of duplicating file-to-file edges.
        """

        origin_map = self.analyze_function_origins()

        output_path = os.path.join(self.output_dir, name)

        dot = Digraph(
            comment="Function Origin Graph",
            format="png"
        )

        if styled:
            dot.attr(
                rankdir='LR',
                bgcolor='#0f172a',
                pad='0.6',
                nodesep='0.6',
                ranksep='1.2',
                splines='spline'
            )

            dot.attr(
                'node',
                shape='box',
                style='filled,rounded',
                fontname='Helvetica',
                fontsize='10',
                fontcolor='white',
                color='#1e293b'
            )

            dot.attr(
                'edge',
                color='#94a3b8',
                penwidth='2',
                arrowsize='0.8'
            )
        else:
            dot.attr(rankdir='LR')

        added_file_nodes = set()
        added_func_nodes = set()

        def ensure_file_node(file):
            if file in added_file_nodes:
                return

            added_file_nodes.add(file)

            if styled:
                fill = (
                    '#2563eb'
                    if file.endswith(('.h', '.hpp'))
                    else '#16a34a'
                )

                dot.node(
                    file,
                    file,
                    fillcolor=fill
                )
            else:
                dot.node(file, file)

        for caller_file, entries in origin_map.items():
            ensure_file_node(caller_file)

            for func_name, decl_file, def_file in entries:

                # Namespace the function node per definition file
                # so unrelated functions sharing a name do not merge.
                func_node = f"{def_file}::{func_name}"

                if func_node not in added_func_nodes:
                    added_func_nodes.add(func_node)

                    if styled:
                        dot.node(
                            func_node,
                            func_name,
                            fillcolor='#9333ea',
                            shape='ellipse'
                        )
                    else:
                        dot.node(
                            func_node,
                            func_name,
                            shape='ellipse'
                        )

                dot.edge(
                    caller_file,
                    func_node
                )

                ensure_file_node(def_file)

                dot.edge(
                    func_node,
                    def_file,
                    label="defines" if styled else None
                )

                if decl_file != "N/A":
                    ensure_file_node(decl_file)

                    dot.edge(
                        func_node,
                        decl_file,
                        label="declares" if styled else None,
                        style="dashed"
                    )

        dot.render(output_path, view=False)

        print(f"[INFO] Generated: {output_path}.png")

    # ------------------------------------------------------------
    # External Libraries Report
    # ------------------------------------------------------------
    def generate_library_report(
            self,
            output_name="libraries_report.txt"
    ):
        """
        Generates a text file listing C++ libraries
        (system/standard includes) used in each file.

        Only considers includes of the form:
            #include <...>
        """

        include_pattern = re.compile(
            r'#include\s*<([^>]+)>'
        )

        output_path = os.path.join(
            self.output_dir,
            output_name
        )

        report = {}

        for file in self.files:
            path = os.path.join(self.directory, file)

            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            libs = include_pattern.findall(content)
            unique_libs = sorted(set(libs))

            report[file] = unique_libs

        with open(
                output_path,
                'w',
                encoding='utf-8'
        ) as out:

            for file, libs in sorted(report.items()):
                out.write(f"{file}\n")
                out.write("-" * len(file) + "\n")

                if libs:
                    for lib in libs:
                        out.write(f"  - {lib}\n")
                else:
                    out.write("  (no external libraries)\n")

                out.write("\n")

        print(
            f"[INFO] Library report generated: {output_path}"
        )

    # ------------------------------------------------------------
    # Code Quality Analysis
    # ------------------------------------------------------------


    def analyze_code_quality(
            self,
            name="code_quality_report.txt"
    ):
        """
        Heuristic static analysis of C++ source files.

        Generates both:
            - TXT report
            - CSV report

        The CSV filename is automatically derived from the TXT filename.
        """

        output_path = os.path.join(
            self.output_dir,
            name
        )

        csv_output_path = os.path.join(
            self.output_dir,
            name.replace(".txt", ".csv")
        )

        findings = []
        functions = []

        # --------------------------------------------------------
        # Configuration
        # --------------------------------------------------------
        primitive_types = (
            r'(?:bool|char|signed|unsigned|short|int|long|float|double|'
            r'size_t|uint8_t|uint16_t|uint32_t|uint64_t|int8_t|int16_t|'
            r'int32_t|int64_t|string|std::string)'
        )

        control_keywords = {
            'if',
            'for',
            'while',
            'switch',
            'catch'
        }

        weak_names = {
            'tmp',
            'temp',
            'data',
            'value',
            'val',
            'result',
            'res',
            'obj',
            'object',
            'item',
            'thing',
            'foo',
            'bar',
            'var',
            'x',
            'y',
            'z',
            'i',
            'j',
            'k'
        }

        # --------------------------------------------------------
        # Helper functions
        # --------------------------------------------------------
        def add_finding(
                file,
                category,
                severity,
                message,
                line=None
        ):
            findings.append({
                "file": file,
                "category": category,
                "severity": severity,
                "line": line,
                "message": message
            })

        def get_line_number(content, position):
            return content.count(
                '\n',
                0,
                position
            ) + 1

        # --------------------------------------------------------
        # Load all source files
        # --------------------------------------------------------
        contents = {}

        for file in self.files:
            path = os.path.join(
                self.directory,
                file
            )

            with open(
                    path,
                    'r',
                    encoding='utf-8',
                    errors='ignore'
            ) as f:
                contents[file] = f.read()

        all_content = "\n".join(contents.values())

        # --------------------------------------------------------
        # 1. Function analysis
        # --------------------------------------------------------
        function_pattern = re.compile(
            r'''
            (?P<return_type>[A-Za-z_][\w:<>,\s*&]*?)
            \s+
            (?P<name>[A-Za-z_]\w*)
            \s*
            \(
                (?P<args>[^;{}]*)
            \)
            \s*
            (?:
                const\s*
            )?
            \{
            ''',
            re.VERBOSE
        )

        for file, content in contents.items():

            for match in function_pattern.finditer(content):

                function_name = match.group("name")

                if function_name in control_keywords:
                    continue

                start = match.start()

                line = get_line_number(
                    content,
                    start
                )

                brace_start = content.find(
                    '{',
                    match.end() - 1
                )

                if brace_start == -1:
                    continue

                depth = 0
                end = brace_start

                for index in range(
                        brace_start,
                        len(content)
                ):
                    if content[index] == '{':
                        depth += 1

                    elif content[index] == '}':
                        depth -= 1

                        if depth == 0:
                            end = index
                            break

                body = content[
                    brace_start:end + 1
                ]

                body_lines = body.count('\n') + 1

                functions.append({
                    "file": file,
                    "name": function_name,
                    "line": line,
                    "body": body,
                    "body_lines": body_lines
                })

                # KISS: long function
                if body_lines > 80:
                    add_finding(
                        file,
                        "KISS",
                        "HIGH",
                        (
                            f"Function '{function_name}' is very long "
                            f"({body_lines} lines). Consider splitting it."
                        ),
                        line
                    )

                elif body_lines > 40:
                    add_finding(
                        file,
                        "KISS",
                        "MEDIUM",
                        (
                            f"Function '{function_name}' is relatively long "
                            f"({body_lines} lines)."
                        ),
                        line
                    )

                # KISS: nesting depth
                max_depth = 0
                current_depth = 0

                for char in body:
                    if char == '{':
                        current_depth += 1
                        max_depth = max(
                            max_depth,
                            current_depth
                        )

                    elif char == '}':
                        current_depth -= 1

                if max_depth >= 5:
                    add_finding(
                        file,
                        "KISS",
                        "HIGH",
                        (
                            f"Function '{function_name}' has a high "
                            f"nesting depth ({max_depth})."
                        ),
                        line
                    )

                elif max_depth >= 4:
                    add_finding(
                        file,
                        "KISS",
                        "MEDIUM",
                        (
                            f"Function '{function_name}' has a nesting "
                            f"depth of {max_depth}."
                        ),
                        line
                    )

                # KISS: excessive condition count
                condition_count = len(
                    re.findall(
                        r'\b(if|else\s+if|switch|for|while)\b',
                        body
                    )
                )

                if condition_count >= 10:
                    add_finding(
                        file,
                        "KISS",
                        "HIGH",
                        (
                            f"Function '{function_name}' contains "
                            f"{condition_count} control structures."
                        ),
                        line
                    )

                elif condition_count >= 6:
                    add_finding(
                        file,
                        "KISS",
                        "MEDIUM",
                        (
                            f"Function '{function_name}' contains "
                            f"{condition_count} control structures."
                        ),
                        line
                    )

        # --------------------------------------------------------
        # 2. Potential unused variables
        # --------------------------------------------------------
        variable_pattern = re.compile(
            rf'\b{primitive_types}\s+'
            rf'([A-Za-z_]\w*)\s*[=;,)]'
        )

        for file, content in contents.items():

            for match in variable_pattern.finditer(content):

                variable_name = match.group(1)

                occurrences = len(
                    re.findall(
                        rf'\b{re.escape(variable_name)}\b',
                        content
                    )
                )

                if occurrences == 1:
                    line = get_line_number(
                        content,
                        match.start()
                    )

                    add_finding(
                        file,
                        "Dead code",
                        "MEDIUM",
                        (
                            f"Variable '{variable_name}' "
                            f"appears unused."
                        ),
                        line
                    )

        # --------------------------------------------------------
        # 3. Potential unused functions
        # --------------------------------------------------------
        function_names = {}

        for function in functions:
            name = function["name"]

            function_names.setdefault(
                name,
                []
            ).append(function)

        for name, definitions in function_names.items():

            if name in {
                "main",
                "operator",
                "begin",
                "end"
            }:
                continue

            occurrences = len(
                re.findall(
                    rf'\b{re.escape(name)}\s*\(',
                    all_content
                )
            )

            if occurrences <= 1:

                for definition in definitions:
                    add_finding(
                        definition["file"],
                        "Dead code",
                        "MEDIUM",
                        (
                            f"Function '{name}' may be unused."
                        ),
                        definition["line"]
                    )

        # --------------------------------------------------------
        # 4. Suspicious names
        # --------------------------------------------------------
        identifier_pattern = re.compile(
            r'\b(?:'
            r'int|float|double|bool|size_t|'
            r'uint8_t|uint16_t|uint32_t|uint64_t|'
            r'std::string|string'
            r')\s+([A-Za-z_]\w*)'
        )

        for file, content in contents.items():

            for match in identifier_pattern.finditer(content):

                name = match.group(1)

                if name.lower() in weak_names:
                    line = get_line_number(
                        content,
                        match.start()
                    )

                    add_finding(
                        file,
                        "Naming",
                        "LOW",
                        (
                            f"Variable '{name}' has a vague "
                            f"or non-descriptive name."
                        ),
                        line
                    )

                elif len(name) == 1:
                    line = get_line_number(
                        content,
                        match.start()
                    )

                    add_finding(
                        file,
                        "Naming",
                        "LOW",
                        (
                            f"Variable '{name}' is only "
                            f"one character long."
                        ),
                        line
                    )

        # --------------------------------------------------------
        # 5. Possible unnecessary copies
        # --------------------------------------------------------
        copy_patterns = [
            r'\bstd::vector<[^>]+>\s+\w+\s*=\s*\w+\s*;',
            r'\bstd::string\s+\w+\s*=\s*\w+\s*;',
            r'\bauto\s+\w+\s*=\s*\w+\s*;'
        ]

        for file, content in contents.items():

            for pattern in copy_patterns:

                for match in re.finditer(
                        pattern,
                        content
                ):
                    line = get_line_number(
                        content,
                        match.start()
                    )

                    add_finding(
                        file,
                        "Performance",
                        "LOW",
                        (
                            "Possible unnecessary copy detected. "
                            "Consider const reference, move semantics, "
                            "or a direct construction."
                        ),
                        line
                    )

        # --------------------------------------------------------
        # 6. Nested loops
        # --------------------------------------------------------
        for file, content in contents.items():

            nested_loop_pattern = re.compile(
                r'\bfor\s*\([^)]*\)\s*\{'
                r'(?:(?!}).)*'
                r'\bfor\s*\([^)]*\)',
                re.DOTALL
            )

            for match in nested_loop_pattern.finditer(content):

                line = get_line_number(
                    content,
                    match.start()
                )

                add_finding(
                    file,
                    "Performance",
                    "MEDIUM",
                    (
                        "Nested loop detected. Review algorithmic "
                        "complexity and consider whether the inner "
                        "loop can be optimized."
                    ),
                    line
                )

        # --------------------------------------------------------
        # 7. Expensive operations inside loops
        # --------------------------------------------------------
        expensive_calls = (
            r'\b(?:std::pow|pow|std::sqrt|sqrt|'
            r'std::regex|regex|std::string)\b'
        )

        loop_pattern = re.compile(
            r'\b(?:for|while)\s*\([^)]*\)\s*\{'
            r'(.*?)'
            r'}',
            re.DOTALL
        )

        for file, content in contents.items():

            for match in loop_pattern.finditer(content):

                loop_body = match.group(1)

                if re.search(
                        expensive_calls,
                        loop_body
                ):
                    line = get_line_number(
                        content,
                        match.start()
                    )

                    add_finding(
                        file,
                        "Performance",
                        "MEDIUM",
                        (
                            "Potentially expensive operation inside "
                            "a loop. Consider moving invariant work "
                            "outside the loop."
                        ),
                        line
                    )

        # --------------------------------------------------------
        # 8. DRY: duplicated code blocks
        # --------------------------------------------------------
        normalized_blocks = {}

        for file, content in contents.items():

            lines = content.splitlines()
            cleaned_lines = []

            for line in lines:

                stripped = line.strip()

                if not stripped:
                    continue

                if stripped.startswith("//"):
                    continue

                stripped = re.sub(
                    r'\s+',
                    ' ',
                    stripped
                )

                cleaned_lines.append(stripped)

            block_size = 5

            for i in range(
                    len(cleaned_lines) - block_size + 1
            ):
                block = tuple(
                    cleaned_lines[
                        i:i + block_size
                    ]
                )

                normalized_blocks.setdefault(
                    block,
                    []
                ).append(
                    (file, i + 1)
                )

        for block, locations in normalized_blocks.items():

            if len(locations) < 2:
                continue

            unique_files = {
                location[0]
                for location in locations
            }

            severity = (
                "HIGH"
                if len(unique_files) >= 2
                else "MEDIUM"
            )

            first_file, first_line = locations[0]

            add_finding(
                first_file,
                "DRY",
                severity,
                (
                    f"Code block appears duplicated "
                    f"{len(locations)} times "
                    f"({len(unique_files)} file(s))."
                ),
                first_line
            )

        # --------------------------------------------------------
        # 9. Sort findings
        # --------------------------------------------------------
        severity_order = {
            "HIGH": 0,
            "MEDIUM": 1,
            "LOW": 2
        }

        findings.sort(
            key=lambda item: (
                severity_order[item["severity"]],
                item["category"],
                item["file"],
                (
                    item["line"]
                    if item["line"] is not None
                    else 0
                )
            )
        )

        # --------------------------------------------------------
        # 10. Statistics
        # --------------------------------------------------------
        stats = {
            "HIGH": sum(
                1
                for finding in findings
                if finding["severity"] == "HIGH"
            ),
            "MEDIUM": sum(
                1
                for finding in findings
                if finding["severity"] == "MEDIUM"
            ),
            "LOW": sum(
                1
                for finding in findings
                if finding["severity"] == "LOW"
            )
        }

        # --------------------------------------------------------
        # 11. Write TXT report
        # --------------------------------------------------------
        with open(
                output_path,
                "w",
                encoding="utf-8"
        ) as out:

            out.write(
                "C++ CODE QUALITY ANALYSIS\n"
            )

            out.write(
                "=" * 100 + "\n\n"
            )

            out.write(
                f"Files analyzed : {len(self.files)}\n"
                f"Functions found: {len(functions)}\n"
                f"Findings       : {len(findings)}\n"
                f"HIGH           : {stats['HIGH']}\n"
                f"MEDIUM         : {stats['MEDIUM']}\n"
                f"LOW            : {stats['LOW']}\n\n"
            )

            if not findings:
                out.write(
                    "No potential issues detected.\n"
                )

            else:
                for finding in findings:

                    line_text = (
                        f"line {finding['line']}"
                        if finding["line"] is not None
                        else "unknown line"
                    )

                    out.write(
                        f"[{finding['severity']:<6}] "
                        f"{finding['category']:<13} "
                        f"{finding['file']:<30} "
                        f"{line_text:<12} "
                        f"{finding['message']}\n"
                    )

        # --------------------------------------------------------
        # 12. Write CSV report
        # --------------------------------------------------------
        with open(
                csv_output_path,
                "w",
                newline='',
                encoding='utf-8'
        ) as csvfile:

            fieldnames = [
                "severity",
                "category",
                "file",
                "line",
                "message"
            ]

            writer = csv.DictWriter(
                csvfile,
                fieldnames=fieldnames
            )

            writer.writeheader()

            for finding in findings:
                writer.writerow(finding)

        print(
            f"[INFO] Code quality report generated: "
            f"{output_path}"
        )

        print(
            f"[INFO] CSV report generated: "
            f"{csv_output_path}"
        )

        return findings

        # ------------------------------------------------------------
        # Function Comments Extraction
        # ------------------------------------------------------------
    def export_function_comments_to_csv(
            self,
            output_name="function_comments.csv"
    ):
        """
        Extracts comments associated with functions (both leading comments
        and comments inside the function body) and exports them to a CSV file.

        The resulting CSV contains:
            - File name
            - Function name
            - Line number
            - Comments associated with the function
        """
        output_path = os.path.join(self.output_dir, output_name)

        # Regex pattern matching function definitions
        function_pattern = re.compile(
            r'''
            (?P<return_type>[A-Za-z_][\w:<>,\s*&]*?)
            \s+
            (?P<name>(?:[A-Za-z_]\w*::)?[A-Za-z_]\w*)
            \s*
            \(
                (?P<args>[^;{}]*)
            \)
            \s*
            (?:const\s*)?
            \{
            ''',
            re.VERBOSE
        )

        control_keywords = {
            'if', 'for', 'while', 'switch', 'catch'
        }

        records = []

        for file in self.files:
            path = os.path.join(self.directory, file)

            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            lines = content.splitlines()

            for match in function_pattern.finditer(content):
                func_name = match.group("name")

                # Filter out control keywords mistakenly matched
                if func_name.split("::")[-1] in control_keywords:
                    continue

                # Calculate start line of the function definition
                start_pos = match.start()
                line_num = content.count('\n', 0, start_pos) + 1

                # 1. Extract leading comments directly above the function declaration
                leading_comments = []
                current_line_idx = line_num - 2  # 0-indexed line above definition

                while current_line_idx >= 0:
                    line_text = lines[current_line_idx].strip()

                    if line_text.startswith("//") or line_text.startswith("/*") or line_text.startswith(
                            "*") or line_text.endswith("*/"):
                        leading_comments.insert(0, line_text)
                        current_line_idx -= 1
                    elif not line_text:  # Skip empty lines between comments
                        current_line_idx -= 1
                    else:
                        break

                # 2. Extract comments from inside the function body
                brace_start = content.find('{', match.end() - 1)
                body_comments = []

                if brace_start != -1:
                    depth = 0
                    brace_end = brace_start

                    for idx in range(brace_start, len(content)):
                        if content[idx] == '{':
                            depth += 1
                        elif content[idx] == '}':
                            depth -= 1
                            if depth == 0:
                                brace_end = idx
                                break

                    body_text = content[brace_start:brace_end + 1]

                    # Find single-line and multi-line comments inside body
                    comment_matches = re.findall(
                        r'//.*?$|/\*.*?\*/',
                        body_text,
                        re.MULTILINE | re.DOTALL
                    )

                    for c in comment_matches:
                        cleaned = ' '.join(c.split())
                        body_comments.append(cleaned)

                # Combine all extracted comments
                all_comments = leading_comments + body_comments
                formatted_comments = "\n".join(all_comments) if all_comments else "N/A"

                records.append({
                    "file": file,
                    "function": func_name,
                    "line": line_num,
                    "comments": formatted_comments
                })

        # Write results to CSV file
        with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
            fieldnames = ["file", "function", "line", "comments"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            for record in sorted(records, key=lambda x: (x["file"], x["line"])):
                writer.writerow(record)

        print(f"[INFO] Function comments exported to: {output_path}")
        return output_path

