Analyzing the internal architecture of my C++ project "image-and-video-processing" by scanning all header (.h, .hpp) and source (.cpp) files.

[image-and-video-Processing](https://github.com/Julien186design/image-and-video-processing)

# CPP Dependency Analyzer

A regex-based static analysis tool for C++ projects. It scans a flat directory of `.cpp`/`.h`/`.hpp` files and generates dependency graphs, class/function origin tables, and an external library usage report — without requiring a build system or compiler toolchain.

No AST parsing is used. All analysis is done with regular expressions, which makes the tool fast and dependency-light but heuristic: it will miss or misattribute edge cases such as macro-generated code, function pointers, overload resolution, and forward-declared types used only by pointer/reference. See [Limitations](#limitations).

## Features

- **Include dependency graph** — parses `#include` directives and builds a per-file dependency graph (basic and styled/dark-themed variants).
- **Detailed object dependency graph** — resolves which `class`/`struct` types used in a header are declared in another header, and graphs `Header → Class → Origin header`.
- **Detailed dependency table** — same analysis as above, printed as a plain-text table.
- **Function origin analysis** — maps function calls to their declaration (`.h`/`.hpp` prototype) and definition (`.cpp` body, or `Class::method` in headers) sites, and prints a `Caller → Function → Declared in → Defined in` table.
- **Function origin graph** — graph form of the above, with each function as its own node (namespaced by defining file) so calls fan in/out correctly instead of collapsing into file-to-file edges.
- **Variable scope heuristic** — lists variables declared per file for a subset of common types (`int`, `double`, `float`, `bool`, `string`, `size_t`, `uint8_t`, `std::*`).
- **External library report** — lists system/angle-bracket includes (`#include <...>`) per file, written to a text report.

## Requirements

- Python 3.7+
- [Graphviz](https://graphviz.org/download/) system binaries (the `dot` executable must be on `PATH`)
- Python package: `graphviz`

```bash
pip install graphviz
```

On Debian/Ubuntu, the system Graphviz package is also required:

```bash
sudo apt install graphviz
```

## Usage

Edit the `PROJECT_DIR` constant at the top of the script to point to the directory containing your `.cpp`/`.h`/`.hpp` files:

```python
PROJECT_DIR = "/path/to/your/project"
```

Then run:

```bash
python analyzer.py
```

Output (PNG graphs, `libraries_report.txt`) is written to `<PROJECT_DIR>/Dependency trees`, created automatically if it doesn't exist. Console output includes the variable scope table, detailed dependency table, and function origin table.

## Scope and assumptions

- Scans **one directory, non-recursively**. Files in subdirectories are not included.
- Only local project includes are tracked for the dependency graph (`#include "..."` matching a filename in the same directory, with `.h` → `.cpp` mapping).
- Class/struct detection matches `class Name` / `struct Name` declarations; it does not distinguish declaration from definition, or handle nested/templated classes robustly.
- Function declaration/definition detection distinguishes signatures ending in `;` (declaration) from `{` (definition), and excludes a small hardcoded set of C++ keywords (`if`, `for`, `sizeof`, casts, etc.) that would otherwise match the call-site regex.

## Limitations

- **No preprocessor evaluation** — `#ifdef`-guarded code, macros, and conditional includes are read as-is.
- **No template/generic resolution** — template instantiations and SFINAE constructs are not analyzed semantically.
- **No overload resolution** — a function name match does not account for parameter types or overload sets.
- **False positives/negatives are expected** on non-trivial codebases; treat output as a navigation aid, not ground truth.
- **Class usage regex is line/content-based**, not scope-aware — a class name appearing in a comment or string literal that matches the usage pattern will be reported as a dependency.

## License

Add a license of your choice (e.g., MIT) if publishing this repository.
