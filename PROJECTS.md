coppertop is a Python decorator. It provides:
- multi-dispatch
- algebraic subtyping
- piping
- partial functions

bones-kernel is a C library
- type manager
- memory manager
- sym & enum managers
- RST, IR code gen, dynamic compilation
- function selection

jones is a C extension that exposes the bones kernel to Python

minc is a minimum (partially implemented) C compiler created principally to dogfood the bones kernel

bones is a set of pure Python
- parsing (lexing, grouping and phrase parsing)
- static analysis
- symbol table
- error framework to report errors encountered in parsing and static analysis
- RST interpretation + inspection

dm is a collection of functions that might form a standard library for bones
