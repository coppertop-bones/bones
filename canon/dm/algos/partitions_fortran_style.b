// *********************************************************************************************************************
//
//                            Copyright (c) 2022 David Briant. All rights reserved.
//
// *********************************************************************************************************************

// based on https://rosettacode.org/wiki/Ordered_partitions#Python  - the 2nd algo

load dm.core
from dm.core import ...


// T1 is a type argument to a template
// typedef u32 count


// T1 *** paritions(T1 *xs, count *sizes)
partitions: {{[xs:N**T1, sizes:N2**count] <:N**N2**N**T1>

    // sizes sum check equal (xs count)
    check(sum(sizes), equal, count(sx))

    // xs _partitions(, xs count, sizes)
    _partitions(xs, count(xs), sizes)

}}


// T1 *** _pwartitions(*T1 xs, count n, count *sizes)
_partitions: {[xs:N**T1, n:count, sizes:N2**count] <:N**N2**N**T1>

    // sizes isEmpty ifTrue: [^ (())]
    isEmpty(sizes) ifTrue: [^ (())]

    // xs _combRest(, n, sizes first) each {[a, b]
    //    _partitions(b, .n - (.sizes first), .sizes drop 1) each {
    //        .a prependTo r
    //    }
    //} joinAll
    joinAll(
        each(
            _combRest(xs, n, first(sizes)),
            { [a, b]
                each(
                    _partitions(b, .n - first(.sizes), drop(.sizes, 1)),
                    { [r]
                        prependTo(.a, r)
                    }
                )
            }
        )
    )

}


// struct tuple2 {T1 a; T2 b;}
// struct tuple2 * _combRest(T1 *xs, count n, count m)
_combRest: {[xs:N**T1, n:count, m:count] <:N**(N**T1)*(N**T1)>

    m == 0 ifTrue: [^ to( ( ((), xs) ), <:N**T1>)]
    m == n ifTrue: [^ to( ( (xs, ()) ), <:N**T1>)]

    //(s1, s2): xs takeDrop 1
    (s1, s2): takeDrop(XS, 1)

    // _combRest(s2, s2 count, m - 1) each { (.s1 join a, b) }    // #1
    //  join
    //  _combRest(s2, s2 count, m) each { (a, .s1 join b) }      // #2
    join(
        each(_combRest(s2, count(s2), m - 1), { (join(.s1, a), b) }),    // #1
        each(_combRest(s2, count(s2), m), { (a, join().s1,b) })      // #2
    )

}


// 1 upto 9 partitions (5,4) count PP
PP(count(partitions(1 upto 9, (5,4))))
