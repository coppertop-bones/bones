// see test_structure.py for test cases that should throw errors (i.e. the commented out code)

// SYMBOLS
`a

// METHOD
// { } and .

// {}
// {.}
{x}
{x+y}
{x.y+z}
{[a] x }
{[a:num] x }
{[a,b] x. y}
{[x:num, y:num] x . y}
// {x[a] y} invalid - see test_structure.py


// PARAMS
// {[ ] and , a param list rather than an expression list, sep = ,   param [type] + name
// {[] x}
{[x] x}
{[x,y] x. y}
{[x:num] x}
{[x,y:num] x. y}
{[x,y:num] <:num> x. y}


// INVOCATION
// [ ] and ,
(expr)[]
(expr)[a]
(expr)[a,b]
// 1+1[]  // invalid?? because [] munches left and will eat the rhs of the expr
name[]
name[a]
name[a,b]
{x}[expr*]


// PARENS
// ( ) and no separator - holds exactly one expression
// ()
(expr)
(expr; expr)


/*
.a.b.c/d: 1
.a.b.c..d: 1
/a/b/c/d.fred: 1
1:.a.b.c..d.name
    .fc..a: 1
    1 :.fc..a
.cfg..PROD.serverHP lookupIP cout
*/

solveAx_b_QR{[A:matrix, b:vector]
    // solves Ax = b using QR decomposition
    // QRx = b
    // Q'QRx = Q'b
    // Rx = Q'b
    QR: A QRDecomp[`Householder]
    (QR`Q)' mul b solveRTriangle[QR`R] <:vector>
}
'(typedefs)
<:matrix> = <:list(list(double))>  // ideally should ensure grid
types -> (lists, assoc, unions, structs of)
(string, float, int, bool, sym)
//table is list(struct(a:int,name:sym
NULL
MISSING
ISIN -> string
col -> int
row -> int
height -> float
width -> float
area -> float
depth->float
volume -> float
variant -> union(string,float,int,bool,sym,NULL,MISSING)
'
mul{[x:matrix, y:matrix] <:matrix> ^linlibMulMM[x,y] }      // explicit return type
mul{[x:matrix, y:vector] ^linlibMulMV[x,y] <:vector>}       // inferred return type
'{[A:matrix>] linlibTransposeM[A]}
!{[LHS:double] factorial[LHS]}
!{[LHS:ANY, RHS:bool ] <:P4> not(RHS)}







// ARRAY
// ( ) and ,
(expr,)
(expr,expr)
// (expr)

a: 10 <:float> :b <:int>
a: getInt[] <:float>


//// TABLE
//// ([ ] assign expr and ,
//([a: expr])         // should generate the relevant symbols
//([a: expr] b: expr)
//([a: expr, c: expr] b: expr)
//([a: expr, c: expr] b: expr, d: expr)
//([a: expr <:int>])         // should generate the relevant symbols
//([a: expr <:list(int)>] b: expr <:list(int)>)
//([a: expr <:list(sym)>, c: expr <:int>] b: expr <:int>)
//([a: expr <:int>, c: expr <:int>] b: expr <:int>, d: expr <:int>)
