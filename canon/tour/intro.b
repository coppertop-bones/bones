// this is a tour of the bones language
// it is not a tour of a core library however it wouldn't be much fun if the code was not runnable so a
// companion library, tlib.core, written in Python that provides necessary supporting functionality is included.
//
// let's begin...

// first off we have a comment - the usual double slash
/-
   we can also do block comments which
   can span multiple lines like this
-/


// we can tell the kernel to load other libraries - this make names available in the namespace they are defined
load tlib.stats
load tlib.core              // in all likelihood core was loaded by stats but let's ensure it

// we can import names from other namespaces into our local scope
from tlib.misc import ...   // "..." here means that every function in tlib.core is added to our module namespace

// technical note: scopes come in four types: global, module, function, contextual. When we load a file, a
// corresponding module namespace is created, and by default names are located there. There are two well known
// namespaces, the global root and scratch (which is were all interact programming is done). Because functions are
// resolved via multi-dispatch there are less conflicts and more names tend to be added to the global root.


// let's define a binary function (remember "binary" means it takes in two arguments from the pipeline not that it
// can only take two arguments)
add: {{[x:u8, y:u8] <:u8> x + y}}

1 add 2 check equals 3

// ( ) creates a literal list - bones knows the size and the sorts of things in the list (technically termed a tuple)
(1,2,3) both add (1,2,3) check equals (2,4,6)

// expressions can span multiple lines if subsequent lines after the phrase's start are indented
(1,2,3)
    both add (1,2,3)
    check equals (2,4,6)

// we can also separate phrases with a full stop
b: (1,2,3). b
    each both (1,2,3)
    check equals (2,4,6)

// btw the b: means bind the following to the name b. In a similar vein :c means bind the preceding to the name c.
d + c * x + b * (x * x :x2) + a * x * x2 :y

// take care, although it can help make code denser and is easier to follow than using =, style and good taste
// should prevail

