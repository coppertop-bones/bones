
// COULD DO
// matrix and vector syntax / types <:M>, <:vec>
// multi-assignment
// allow unicode operators √, π, ÷,


// FIX:
// load scipy.linalg
// from scipy.linalg import QR, SVD, backSub, Id
A: (2.;0.;1., 0.;1.;-1., 1.;1.;1.) <:matrix>
b: (2.,0.,2.) + (1.,0.,1.) <:vec>               // just showing vector addition to get (3,0,3)
(Q,R): A QR
x: backSub(R, Q' dot b)
x cout

// solve Ax = b using QR
// Q . R . x = b
// Q' . Q . R . x = Q' . b     =>  ' is unary transpose
// R . x = Q' . b
QRSolve: {{[A:matrix, b:vec] -> vec                    // R is <:UpperRight>, Q is <:Q>
    A QR :(Q,R)
    Q' dot Q assertEqual I(Q.nCols)
    backSub(R, Q' dot b)
}}
x: A QRSolve b

QR: {{[A:matrix] <:{Q:matrix,R:matrix}> ...}}


//load scipy.linalg
// from scipy.linalg import QR, SVD, backSub, I
A: (2, 0, 1; 0, 1, -1; 1, 1, 1) <:matrix>
b: (2, 0, 2) + (1, 0, 1) <:vec>                 // just showing vector addition to get (3,0,3)
// MUSTDO - implement tuple unpacking
// Q,R: A QR
x: backSub(R, Q T dot b)
x cout

// solve Ax = b using QR
// Q . R . x = b
// Q' . Q . R . x = Q' . b     =>  ' is unary transpose
// R . x = Q' . b
//QRSolve: {{[A:matrix, b:vec, -> vec]                   // R is <:UpperRight>, Q is <:Q>
//QRSolve: {{[A:matrix, b:vec] -> vec.                   // R is <:UpperRight>, Q is <:Q>
//QRSolve: {{[A:matrix, b:vec] -> <:vec>                 // R is <:UpperRight>, Q is <:Q>
//QRSolve: {{[A:matrix, b:vec] -> vec                    // R is <:UpperRight>, Q is <:Q>
QRSolve: {{[A:matrix, b:vec] <:vec>                    // R is <:UpperRight>, Q is <:Q>
    A QR :(Q,R)
    Q T dot Q assertEqual I(Q.nCols)
    backSub(R, Q T dot b)
}}
x: A QRSolve b


{x + y} <:count>
{[x,y] <:count> x + y}

QRSolve: {{[A:matrix, b:vec] <:vec> _.numSolves: _.numSolves + 1. x dot y}}




// indentation to remove need for separators? purpose is to give as much flexability in layout as possible

fred
  v1
  vv v3
  v4
  :a
a fred joe
  sally
  arthur. b fred joe

cond ifTrue: [
1
  ]
  ifFalse: [
2
  ]
  addOne




// do the householder reflections...
// e.g. https://www.quantstart.com/articles/QR-Decomposition-with-Python-and-NumPy/
// and
// https://en.wikipedia.org/wiki/QR_decomposition#Using_Householder_reflections
// https://gist.github.com/cbellei/8ab3ab8551b8dfc8b081c518ccd9ada9 tridiagonal
// https://en.wikipedia.org/wiki/Tridiagonal_matrix_algorithm


// R
// dt <- data.table(mtcars)[, .(cyl, gear)]
// dt[,unique(gear), by=cyl]
//
// Bones
// dt: mtCars
//   take `cyl`gear      // table with only the columns
//   groupBy(,`cyl)
//   each {x `gear unique}
//
//
// R
// dt <- data.table(mtcars)[,.(gear, cyl)]
// dt[,gearsL:=list(list(unique(gear))), by=cyl] # original, ugly
// dt[,gearsL:=.(list(unique(gear))), by=cyl] # improved, pretty
//
// Bones
// dt: mtCars take `cyl`gear :t1 groupBy(,`cyl) rename `cyl`gearsL lj(t1,)

