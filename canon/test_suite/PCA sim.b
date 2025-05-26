load dm.linalg, dm.linalg.decomp, dm.core.io
from dm.linalg import ...   // defines matrix and vector
from dm.linalg.decomp import Cholesky :CH, SVD, Eigen, QR: QRHouseholder
from dm.core.io import stdout, NL

// +, -, *, /, ~, <<, >>, <, >, <=, >=, ==, !=  are imported by default


ppMatrix: {[A:matrix, dp:count]
    // prints a matrix nicely with new lines
    fmt: "0." ~ ("0" take dp)
    A each {[row:vector]
        ("[" ~ (row each {x format fmt} joinAll ", ") ~ "]")
    } joinAll NL
}

rho: (
    1.00, 0.95, 0.80;
    0.95, 1.00, 0.90;
    0.80, 0.90, 1.00;
) <:matrix>

L: rho CH `L           // (rho CH).L or rho CH `L

stdout << "Choelsky: " << NL << (L ppMatrix)

// context and calculation order - can we replace the fn with a value?
