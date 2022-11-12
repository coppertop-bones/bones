// PGM course example

load dm.core, dm.pgm
from dm.core import ...
from dm.pgm import BayesNet, P, PP


// using maps and panels and a bespoke P fn we can model unconditional PMFs
difficulty:   `d0`d1 ! (0.6;0.4)
intelligence: `i0`i1 ! (0.7;0.3)
sat: ([int: `i0`i1]
    s0: (0.95;0.2),
    s1: (0.05;0.8)
)
grade: ([intDiff: (`i0`d0;`i0`d1;`i1`d0;`i1`d1)]
    gA: (0.3;0.05;0.9;0.5),
    gB: (0.4;0.25;0.08;0.3),
    gC: (0.3;0.7;0.02;0.2)
)
letter: ([grd: `gA`gB`gC]
    l0: (0.1;0.4;0.99),
    l1: (0.9;0.6;0.01)
)

P: {[d,i,s,g,l] .difficulty[d] * .intelligence[i] * .sat[i][s] * .grade[i,d][g] * .letter[g][l]}

sat meta PP
difficulty meta PP

// let's show that our P fn works
expected: difficulty.d0 * intelligence.i0 * sat.i0.s0 * grade[`i0`d0].gA * letter.gA.l0
expected check equal P(`d0,`i0,`s0,`gA,`l0)


// using BayesNet which takes indexed panels we can model conditional PMFs
difficulty2:   ([D:`d0`d1] P:(0.60;0.40))
intelligence2: ([I:`i0`i1] P:(0.70;0.30))
sat2:          ([I:`i0`i0`i1`i1, S:`s0`s1`s0`s1] P:(0.95;0.05;0.20;0.80))
grade2:        (
    [
        I: `i0`i0`i1`i1`i0`i0`i1`i1`i0`i0`i1`i1,
        D: `d0`d1`d0`d1`d0`d1`d0`d1`d0`d1`d0`d1,
        G: `gA`gA`gA`gA`gB`gB`gB`gB`gC`gC`gC`gC
    ]
    P: (0.3;0.05;0.9;0.5;0.4;0.25;0.08;0.3;0.3;0.7;0.02;0.2)
)
letter2:       (
    [G:`gA`gB`gC`gA`gB`gC, L:`l0`l0`l0`l1`l1`l1]
    P: (0.10;0.40;0.99;0.90;0.60;0.01)
)
net: BayesNet(difficulty2, intelligence2, sat2, grade2, letter2) PP
net P(,`d0,`i0,`s0,`gA,`l0) PP
net pmfGiven(,`D,`I)
net pGiven(,`d1,`i0)




