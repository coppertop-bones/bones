

when we group we can figure some things


know if the function is nullary, unary, binary, ternary - this means the grouper must be able to parse <:binary> etc
can see if a name is accessed - e.g. local, context, parent, module, global, block args
know if a name has been typed - i.e. last token before the assignment is typelang
know all the scopes in the PACE unit - we define new scopes for modules, functions and blocks. (blocks are simple - 
they share their enclosing scope but can have local parameters - which will override their parent). variables defined 
in blocks are added to the parent? We could prevent blocks to write to their parents but we would loose conditional 
updates. We could allow a parent to access a value only bound in block but this might lead to bugs.

rule is parents can only access variables bound in blocks if they are bound in the parent? why bother - we can have 
local names
however the point of block is to conditionally bind a value and we can have hidden locals in functions (which are 
mildly less complex anyway)


for implicit fns args we don't know the args - or don't we? e.g. all names must either be a local, an arg or a fn

so at the end of grouping we have a symbol table that is incomplete - we know all the symbols but we don't 
necessarily what they refer to

at the end of phrase parsing the symbol table is known but the types of the symbols may still need inferring

to get functions defined in scope we need to parse breadth first - but to know the end of a group we need to parse 
depth first. So we parse depth first, then revisit to fill in functions.

Thus a scope must be able to keep a list of unresolved symbols that are resolved in later steps. If we allow values 
and fn names to overload then we have to note if the unresolved symbol has been used as one whilst keeping it to the 
end to resolve as the other.


# ALGO

Parsing is done in two stages:

## GROUP PARSING
- depth first
- outputs groups of phrases
- creates a symbol table (aka scope) for each function and block (adding explicit parameters), module symbol tables are 
  created by import behaviour
- detects name access (local, parent, contextual, module, global) and assignment
- for each scope notes accesses
- can detect many function assignments (e.g. `fn1: {x+1}` and `fn2: {x+y+z} <:ternary>`), but not all of them (e.g. 
  `fn3: {x+1} wrap`) 
- could disallow some block assignments if we wanted but not `trueStuff: [x: x + 1] wrap`
- so an assignment cannot be said to be a value until the type is known (either explicitly or by inference)
- type-lang is parsed here (within the context of the module being processed)
- we can assign some types here, e.g. `x: 10 + y <:f64>`
- distinguish between a literal struct and a function

## PHRASE PARSING
- breadth first - so child functions and blocks can refer to names defined later
- outputs RST
- all function names must have a known style before being accessed
- at the end of each phrase every name will be resolved to be a local or external (i.e. defined outside of this scope) 
  overload, and / or value
- can add implicit function parameters to symbol table
- if we overload too much then sometimes we may uncover ambiguity e.g. if `joe` can take a `<:function + something>` 
  then we cannot tell which `fred` to use in `fred joe` if `fred` is defined as a function and also as a value


At the end of parsing, we know the location of every single name and if it is a local or external overload and/or a 
value. We know all function styles, and some function and value types. We know every overload. We have an RST we could 
execute in dynamic mode.

  
# NOTES
## FUNCTION ASSIGNMENT

global functions are disallowed? (consider the case when a function is reassigned - do we mean to replace it or overload 
it), but what about I/O commit on assignment

contextual functions are allowed? but does this introduce new syntax to replace functions? e.g. `_.stdout: myNewStream`

could we have `_.*stdout: myNewStream` to mean replacement?


## TYPE ALIASES

## VOID
uninitialised variables - can we detect them? almost certainly



type checking and inference - result is fully typed with partial checks

