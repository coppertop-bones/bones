

We find that the presence of multi-dispatch changes the way we use modules. A module is now a unit of functions rather 
than a namespace organisation of functions.

In bones we can import names from modules into our namespace, e.g. scratch in a REPL environment. If we import 
functions with the same name they are overloaded in our namespace (not globally).


### IMPORTING IN PYTHON
In python we don't want to break the current import mechanism as that would be very confusing (we tried it). So 
instead, we use the standard import hook mechanism to create the overloads when a magic package, currently we use `_` 
is encountered.

import dm.core                  # works as normal
from dm.core import linalg      # works as normal
from _.dm.core import fred      # imports the name fred from dm.core creating a local overload if necessary

from _.dm.core import linalg    # raises a CoppertopImportError as we don't allow any non-coppertop functions to be 
                                # imported using this magic
import _.dm.core                # similarly a CoppertopImportError is raised









 Typically we want these functions, e.g. considering `+`, to play with the 
existing functions. They usually don't need to be organised by a name space.

So

```
import dm.core                  // module
import dm.testing

from _ import check, ==, <>, is, sum    // and so on.
from import 

groot is a little twee
from dm.core import ...         // namespace
from dm.testing import ...
```

the namespace dm.core would include all the normal symbols, i.e. +, -, *, /, <=, <, ==, etc
dm.bool
dm.arith    +, *, -, /     fp and int
dm.math.core   sin, cos, ln, log, rounding etc
dm.linalg.core      mmul, madd etc
dm.linalg.decomps    

need a list of expected builtins

but module name we are importing from is not the same as we overloads exist

from dm.ccy import ...      // defines ccy and fx and +, * etc on those

do we need to restrict the symbols in bones?

e.g. I don't want my check function to clash with dm.testing
so my functions get defined in scratch - unless I put them into groot


from _..core import ...
so does the namespace you import from have its own overloads?

import dm.linalg.algos.underdetermined


res: dm.linalg.algos.underdetermined.search(,,,,)


explicit overload creation gives more configurability and less cross library pollution but also is a layer of 
complexity? so you need to understand modules


our problem is making bones and python work similarly


import dm.core
from dm.core import add

from fred.core import add

add is overloaded in my namespace here, but not in dm.core nor fred.core

can we do that with _groot.py?

if we try to overwrite a coppertop function with a non-coppertop function or vice versa we through an import error?

we can also optionally throw a redefinition error if the type sig is already defined? probably not as would prevent 
this:
```
import buggy_module
import fixes_to_buggy_module
```








