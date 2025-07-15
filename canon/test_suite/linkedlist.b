

<:ll: null + (T*ll)>
<:null + (T*ll) :ll>

pupils: () <:ll & person>

node: T + (N**node)

// or

<:tree: {item: T} + {children: N**tree}>   // loops are allowed in types

family: () <:tree & (person + null)>





