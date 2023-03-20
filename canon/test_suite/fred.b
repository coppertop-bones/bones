load snibs.core
from snibs.core import ifTrue:ifFalse:, true, false, join, +
a: (true ifTrue: "1.0" ifFalse: 1)
addTwo: {x + 2}
addTwo: {x join "Two"}
a addTwo


'{[type:python]
types = [
    void,
    void,
]
expected = "1.0Two"

}'