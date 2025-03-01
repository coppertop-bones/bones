// atoms
txt: atom
ret_code: atom err: atom capitals: atom
null: f64: i32: atom

// intersections
i1: capitals & ret_code & txt
i1: txt & capitals & ret_code

// intersections & unions
u1: txt & ret_code + i32 & ret_code + err
u2:txt&capitals+err                         // assert u1 == u2, 'u1 != u2'

// tuple
tup1: f64 * u2
tup2: tup1 * f64
tup3: f64 * err + ret_code & txt * f64      // assert tup2 == tup3, 'tup2 != tup3'

// recursion in one line
f64list: f64 * f64list + null

// recursive intersection
isin: txt & isin

// recursion via predeclaring
txtList: tbc
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


// orthogonal spaces, explicitly matched and recursive intersections in

// runtime fx
ccyfx: atom
ccysym: atom
rt_ccy: rt_ccy && {v:f64, ccy:ccysym} in ccyfx
rt_fx: rt_fx && {v:f64, dom:ccysym, for:ccysym} in ccyfx

rt_convert_ccy_fn: rt_ccy * rt_fx ^ rt_ccy

// static fx
ccyfx: atom
ccy: atom explicit in ccyfx             // disallow GBP & USD => GBP && ccy & USD && ccy
fx: atom explicit in ccyfx              // disallow ccy & fx
domfor: atom explicit in domfor         // allow fx & domfor

GBP: GBP && ccy in ccy                  // GBP is a ccy and is orthogonal in ccy
USD: USD && ccy in ccy
JPY: JPY && ccy in ccy

GBP2USD: domfor && {dom:GBP, for:USD} in domfor
USD2JPY: domfor && {dom:USD, for:JPY} in domfor

GBPUSD: fx & domfor && {dom:GBP, for:USD} in fx     // && is required here
USDJPY: fx & domfor && {dom:USD, for:JPY} in fx

convert_ccy_fn: (ccy && T1) * (fx & domfor && {dom: ccy && T1, for: ccy && T2}) ^ (ccy && T2)
convert_f64_ccy_fn: (f64 & ccy && T1) * (f64 & fx & domfor && {dom: ccy && T1, for: ccy && T2}) ^ (f64 & ccy && T2)

rat: {num: f64, den: f64}
convert_rat_ccy_fn: (rat & ccy && T1) * (rat & fx & domfor && {dom: ccy && T1, for: ccy && T2}) ^ (rat & ccy && T2)


// implicitly is

//c-style const
mut: tbc                                // i.e. is mutable
consty: atom implicitly mut             // consty is a space with that is implicitly mut
const: atom in consty
mut: mut & const

