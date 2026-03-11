Analyzing the internal architecture of my C++ project "Image Processing" by scanning all header (.h, .hpp) and source (.cpp) files.

https://github.com/Julien186design/Image-Processing

It automatically extracts dependencies and generates neat visual representations of the project structure using Graphviz.

Overview

The script performs three main tasks:

  1) Architecture Analysis: Parses all project files and extracts #include relationships.

  2) Variable Scope Analysis: Provides a simple heuristic to identify global or member variables.

  3) Graph Generation: Builds a clean visual map of file dependencies.

Two versions of the graph generator are available:

  1) generate_dependency_graph() — the original, straightforward implementation.

  2) generate_dependency_graph_v2() — an enhanced and visually refined version.

The second function (generate_dependency_graph_v2) was entirely derived from the first one using ChatGPT. I specifically requested a more "sexy" visualization style and published it without restructuring or rewriting the AI-generated text, apart from a few details regarding the format. Professional coders would rightly say that the quality of the code and its design are poor. You can reuse this code if you keep this detail in mind. If you intend to extend the code, work on the architecture.
