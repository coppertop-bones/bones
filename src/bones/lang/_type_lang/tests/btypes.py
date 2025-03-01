from collections import namedtuple
from bones.core.sentinels import Missing

atom = namedtuple('atom', ['id', 'name', 'explicit', 'space'])
atom.__repr__ = lambda self: f'atom({self.name!r}, explicit=True)' if self.explicit else f'atom({self.name!r})'
atom.__str__ = lambda self: f'"{self.name!s}"' if self.explicit else f'{self.name!s}'


inter = namedtuple('inter', ['id', 'types'])
def inter__repr__(self):
    return f'inter({", ".join([repr(t) for t in self.types])})'
inter.__repr__ = inter__repr__

union = namedtuple('union', ['id', 'types'])
def union__repr__(self):
    return f'union({", ".join([repr(t) for t in self.types])})'
union.__repr__ = union__repr__

tuple = namedtuple('tuple', ['id', 'types'])
def tuple__repr__(self):
    return f'tuple({", ".join([repr(t) for t in self.types])})'
tuple.__repr__ = tuple__repr__

struct = namedtuple('struct', ['id', 'fields'])
struct.__repr__ = lambda self: f'struct({self.fields!r})'

rec = namedtuple('rec', ['id', 'fields'])
rec.__repr__ = lambda self: f'rec({self.fields!r})'

seq = namedtuple('seq', ['id', 'contained'])
seq.__repr__ = lambda self: f'seq({self.contained!r})'

map = namedtuple('map', ['id', 'tLhs', 'tRhs'])
map.__repr__ = lambda self: f'map({self.tLhs!r}, {self.tRhs!r})'

fn = namedtuple('fn', ['id', 'tArgs', 'tRet'])
fn.__repr__ = lambda self: f'fn({self.tArgs!r}, {self.tRet!r})'

mutable = namedtuple('mutable', ['id', 'contained'])
mutable.__repr__ = lambda self: f'mutable({self.contained!r})'

schemavar = namedtuple('schemavar', ['id', 'name'])
schemavar.__repr__ = lambda self: f'schemavar({self.name!r})'

class recursive:
    __slots__ = ('id', 'name', 'main')
    def __init__(self, id, name):
        self.id = id
        self.main = Missing
        self.name = name
    def __repr__(self):
        # OPEN: handle recursion
        return f'recursive({self.name!r})' if self.main else f'TBC({self.name!r})'
