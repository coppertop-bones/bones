// atoms
txt: atom
isin: atom err: atom capitals: atom
null: f64: i32: atom

i1: capitals & isin & txt
i1: txt & capitals & isin               // reassign same type

// intersections & unions
u1: txt & isin + i32 & isin + err
u2:txt&isin+err                         // assert u1 == u2, 'u1 != u2'

// tuple
tup1: f64 * u2
tup2: tup1 * f64
tup3: f64 * err + isin & txt * f64      // assert tup2 == tup3, 'tup2 != tup3'

// recursion in one line
f64list: f64 * f64list + null

// recursion via predeclaring
txtList: tbc
//txtListOrNull: txtList + null + fred
txtListOrNull: txtList + null
txtList: txt * txtListOrNull

// struct
point1: {x:f64, y:f64}
point2: {y:f64, x:f64}                  // assert point1 != point2, 'point1 == point2'

// records
r1: {{x:f64, y:f64}}
r2: {{y:f64, x:f64}}                    // assert r1 == r2, 'r1 =! r2'

// seq, map, fn
seq1: N ** i32
seq2: Ni ** Nj ** f64
matrix: N1 ** N2 ** f64                 // assert seq2 == matrix, 'seq2 != matrix'
map1: txt ** txt + err
f64op_2: f64 * f64 ^ f64
// OPEN: 0 arg functions

// mutatable
mut_list: N ** *(txt + err)
mut_tup: txt* *(txt)
mut_tup: txt * *(txt)
tup4: txt*txt
tup5: txt *txt                          // assert tup4 == tup5, 'tup4 != tup5'
tup6: txt * txt                         // assert tup5 == tup6, 'tup5 != tup6'

// low precedence intersection
t7: f64 * txtList & mut_list + null [txt]

// orthogonal, explicit and implicit
ccy: atom exp in (ccyfx: atom)
GBP: ccy & GBP & f64
domfor: {dom: ccy, for: ccy}
fx_: atom exp in ccyfx
// fx: fx & domfor in ccyfx    - illegal
fx: fx_ & domfor

rat: {num: f64, den: f64}
f64fx: f64 & fx
ratfx: rat & fx

ccyfx: atom
ccy: atom exp in ccyfx
fx_: atom exp in ccyfx
GBP: ccy & GBP & f64

mut: tbc
consty: atom implicitly mut
const: atom in consty
mut: mut & const

f64 * f64