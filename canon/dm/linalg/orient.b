// *********************************************************************************************************************
//
//                            Copyright (c) 2022 David Briant. All rights reserved.
//
//    This is a derivation of Jay Damask's work from:
//       https://gitlab.com/thucyd-dev/thucyd, and,
//       https://gitlab.com/thucyd-dev/thucyd-eigen-working-examples
//    Original Copyright 2019 Buell Lane Press, LLC (buell-lane-press.co)
//    Licensed under Apache License, Version 2.0, January 2004, see http://www.apache.org/licenses/
//
// DESCRIPTION:
//       Implementation of the theory of consistently oriented eigenvectors
// *********************************************************************************************************************

from dm.core import ...
load dm.linalg.tupimpl     // could alternatively load the npimpl - if load both then need to distinguish somewhere
from dm.linalg import ...
from dm.math import ...
from dm.algos import ...

<:Givens:Givens>


orientEigenvectors: {[V:matrix, E:matrix] <:{Vor:matrix, Eor:matrix, anglesMtx:matrix, signFlips:vec}>
    (Vsort, SSort): sortEigenvectors(V, E diag).  Vwork: Vsort.  anglesMtx: Vwork shape zeros.  signFlips: Vwork nCols :n zeros

    seq(1, n) do: [[cursor]
        signFlips[cursor]: Vwork[cursor, cursor] >= 0.0 ifTrue: 1.0 ifFalse: -1.0
        Vwork[..., cursor]: Vwork atCol cursor mul (signFlips cursor)
        (Vwork, anglesMtx[cursor, ...]): reduceDimensionByOne(cursor, Vwork)
    ]

    (Vsort dot (signFlips toDiag), SSort toDiag, anglesMtx, signFlips)
}


reduceDimensionByOne: {[cursor:index, Vwork:matrix] <:{Vwork:matrix, anglesCol:vec}>
    solveRotationAnglesInSubDim(cursor, Vwork atCol cursor) :anglesCol
    constructSubspaceRotationMatrix(cursor, anglesCol) :R
    (R T dot Vwork, anglesCol)
}


solveRotationAnglesInSubDim: {[cursor:index, Vcol:vec] <:vec>
    anglesCol: Vcol count :n + 1 zeros

    r: 1.0
    seq(cursor + 1, n) rev do: [[subCursor]          // iterate over rows in subspace to calculate full 2-pi angles
        y: Vcol[subCursor]
        r: r * cos(anglesCol[subCursor + 1])
        anglesCol[subCursor]: (r != 0.0 ifTrue: [arcsin(y / r)] ifFalse: 0.0)
    ]
    anglesCol take n
}


constructSubspaceRotationMatrix: {[cursor:index, anglesCol:vec] <:matrix>
    // iterate over angles (in reverse order), build a Givens matrix, and apply, e.g. R2 * (R3 * (R4 * I))
    anglesCol drop cursor to(,<:count>) rev enumerate inject(, anglesCol count :n eye,)
        {[R, subcursor] Givens(.n, .cursor, subCursor, .anglesCol[subCursor]) dot R}
}


Givens: {[n:count, cursor:index, subCursor:index, theta:num] <:matrix>
    (1 <= cursor) and (cursor < n) and (cursor < subCursor) ifFalse: [^^ 'invalid input' <:err & Givens>]

    R: n eye
    R[cursor, cursor]: cos(theta)
    R[cursor, subCursor]: -sin(theta)
    R[subCursor, cursor]: sin(theta)
    R[subCursor, subCursor]: cos(theta)
    R
}


sortEigenvectors: {[V:matrix, S:vec] <:{V:matrix, S:vec}>
    indices: S abs <:+desc> sortedIndices
    (V atCol indices, S at indices)
}
