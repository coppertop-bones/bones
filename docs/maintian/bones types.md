

bones types 

can describe data well and succinctly
are intuitive
allow type inference in the presence of multiple dispatch

mutli dispathch give us a nice way to organise programs, handles a bunch of boiler plate, allows for elegant and expressive apis

this feels like smalltalk to me but at the next level


what is a type

there are all sorts of answers, but the simplest and most profound I've encountered is it is a label used by a type 
system to do some analysis.

bones comes in two flavours - static and dynamic. In dynamic bones we don't do any static analysis and the type is for 
each object is stored in a well known location, e.g in the memory structure, similar to Python and Smalltalk

For simplicity we use the exact same set of labels in static bones, but with the notable exception of unions we can 
discard the label after the program has been analysed. The type of a specific elemnt in a union cannot be inferred 
upfront so we keep the label to hand with that element and branch code accordingly.


There are six types of label - we term the type of a label aka type a metatypes in keeping with our Smalltalk influence.



Atoms

these are basic labels that cannot be broken down further - these labels are used to refer to objects the cpu uses, 
such as integer and float, to objects a programming langauge uses such as lists, structs, frames, handles, etc, and 
objects that exist in the problem domain such as currecy, fx rates, matrices, trades, bonds.



Unions

we can create a new label that is understood to be this label or that label, for example a piece of text OR an error 
description - e.g. read a file answers the contents or a file not found error.

We notate unions with a + operator, e.g. txt + err



Intersections

This kind of label indicates that it is both this and that, for example the number 121.3 can be both a decimal and a 
foreign exchange rate.

We notate intersectoins with an & operator, e.g. decimel & fx



Note on sum types

Consider a type boolean with possibilities True and False, and a type preschoolage (i.e. integers in the 
range of zero to three).

The union of these two has six different possibilities, two from boolean and four from preschoolage. If we take a 
union of preschoolage or preschoolage we only have four possibilities. If we take the union of 

fred & preschoolage + joe & preschoolage we have eight possibilities. In some programming styles these go be the term sum type.



Products

Currently we have two sorts of "product" types - structs and tuples. For us a struct is an ordered set of associations, 
each mapping a name to a type. E.g. a point might be {x: float64, y:float64}, and this is different to 
{y:float64, x:float64}. A tuple is an ordered set of associations each mapping an index to a type, e.g. 
{1:float64, 2:float64}. It would be possible to add other product types, for example an unordered set of name to type 
mappings (aka records?) where {x: float64, y:float64} is the same as {y:float64, x:float64}.

Products are called products because the number of possible combinations is the number of the first association * the 
number of the second

tuples are notated T1*T2
structs {name1: T1, name2:T2}



Exponentials

exponentials map a union to a union, e.g. an index to a text or err, a symbol to a float, two float to a float. These are 
examples of sequences (e.g. lists), maps (e.g. dictionaries) and functions.

seq are notated N**T, e.g. N ** (text + err)
maps are notated T**T, e.g. txt ** float
functions are notated (T1*T2)^T3, e.g. (float*float) ^ float, or alternatively (T1, T2) -> T3

the number of possibilities is the number on the RHS to the power of the number on the left hand side



For tuples each elements type is associated with the slot index. For a sequence the type of the element is the 
one that describes every possible element, i.e. a union of the type of each element.

This is the essential difference between tuples and lists.

So a matrix is an exponential - each element is a float + nan and is indexed by a row index and a column index - thus
it is a sequence.



Schema variables

These are notated T1, T2, T3, Ta, Tb, Tc etc and represent relationships within a type. e.g. (N**T1, T1^T2) -> N**T2.
We term any type a type schema if it contains schema variables.




<: aka fitsWithin







### Nomenclature

value

immutable

name

binding

arrow

object - more in the c sense than in the oo sense, i.e. an object has a class which means structures and interpretation
however there is no tight association with behaviour

behaviour - the smalltalk word for the stuff that is caused by sending a message

message

noun

verb

type

class - a layout convention in memory - a little broader than a c struct as it encompasses collections of structs that
work together. it captures the idea that is piece of memory is interpreted, i.e. encoded and decoded, in this way.


adjective, adverb, adverbial

