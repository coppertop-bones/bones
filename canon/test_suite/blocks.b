// test that CoW and blocks work properly together on names in the enclosing scope

// asMatrix converts a 1d or 2d tuple into a matrix
// addressOf returns the address in memory right at the instant of a bones object (NB consider the idea that an address
// is not of the same essence as a pointer)

load dm, linalg, tdd, ctesting, fred
from dm import ...
from linalg import mmul, asMatrix, T
from tdd import check
from ctesting import addressOf      // the result of addressOf is xor'd so it doesn't get mutated by the GC
from fred import isOne

// not sure we can rely on compiler to not optimise below so let's use a redundant conditional it can't understand
// since fred is a precompiled lib (maybe even should write in C)
thing: 1

(1,2;3,4) asMatrix :a addressOf :aAdd
(5,6;7,8) asMatrix :b addressOf :bAdd


thing isOne ifTrue: [b: b T]                    // simpler in place test
b addressOf check == bAdd                       // the unaliased b is updated in place

thing isOne ifTrue: [b: a mmul b]
b addressOf check == bAdd                       // cool - we've figured out that b can be done in place

b: thing isOne ifTrue: [b T] ifFalse: [b]       // ifTrue:ifFalse ensures b's type is not a union of matrix + missing
b addressOf check == bAdd                       // binding outside of the block behaves similarly

c: b                                            // alias b ensuring that Cow happens and b is not updated in place
thing isOne ifTrue: [b: b T]
b addressOf :newBAdd check != bAdd

thing isOne ifTrue: [b: b T]
b addressOf check == newBAdd                    // the new b can be updated in place

c: b                                            // alias the new b
b: thing isOne ifTrue: [b T] ifFalse: [b]
b addressOf check != newBAdd                    // binding outside of the block behaves similarly as before


// do it all again but at a deeper level

{mat:(1,2;3,4) asMatrix} :h addressOf :hAdd     // h for holder
h.mat addressOf :hmatAdd

thing isOne ifTrue: [h.mat: h.mat T]
h.mat addressOf check == hmatAdd                // h.mat can be done in place
h addressOf check == hAdd                       // as can h

c: h.mat                                        // alias h.mat but not h
thing isOne ifTrue: [h.mat: h.mat T]
h.mat addressOf check != hmatAdd                // h.mat has been alias so must be copied
h addressOf check == hAdd                       // but h itself hasn't so can be updated in place

d: h                                            // alias h but not h.mat
hmatAdd: h.mat addressOf
thing isOne ifTrue: [h.mat: h.mat T]
h.mat addressOf check == hmatAdd                // h.mat has been aliased yet so can be done in place
h addressOf check != hAdd                       // but h has so must be copied

h :d addressOf :hAdd
h.mat :c addressOf :hmatAdd
thing isOne ifTrue: [h.mat: h.mat mmul b]
h.mat addressOf check != hmatAdd                // the new h.mat has been aliased yet so can be done in place
h addressOf check != hAdd                       // but h has so must be copied




// do partitions in fortran style



