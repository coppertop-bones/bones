
a: {x}         // unary (1 arg)
a: {x + y}     // unary (2 args)
a: {[x,y,z] x+y+z}   // unary (3 args)
b: {{x + y}}   // binary
a: b <:unary>
c: {x + y + z} <:ternary>
d: {1+1} <:nullary>
e: {x} <:rau>



// OVERLOADS

addOne: {x + 1}             // polymorphic
addOne: {x ~ y}             // polymorphic on ~ operator
addOne: {[x:num] x + 1}     // takes explicit num arg, inferred to return <:num>
addOne: {x ~ " ONE"}        // polymorphic on ~ and literal ""   <:str>, <:ascii>, <:str>

a: 1 to <:ascii>

from std import array, string, table

array.join
string.join
table.join


// name type error

a: {x + y}
a: {{x + y}}

// literal integers, decimals and strings are mildly polymorphic - types can be inferred from the type check but
// default to ascii, index and num
<:+err>  <:&GBP>
x <:num> + 1

