from collections import namedtuple
from bones.core.sentinels import Missing

atom = namedtuple('atom', ['id', 'name', 'explicit', 'space'])
atom.__repr__ = lambda self: f'atom({self.name!r}, explicit=True)' if self.explicit else f'atom({self.name!r})'
atom.__str__ = lambda self: f'"{self.name!s}"' if self.explicit else f'{self.name!s}'


inter = namedtuple('inter', ['id', 'types', 'explicit'])
def inter__repr__(self):
    if self.explicit:
        return f'inter({", ".join([repr(t) for t in self.types])}, explicit=True)'
    else:
        return f'inter({", ".join([repr(t) for t in self.types])})'
inter.__repr__ = inter__repr__

union = namedtuple('union', ['id', 'types', 'explicit'])
def union__repr__(self):
    if self.explicit:
        return f'union({", ".join([repr(t) for t in self.types])}, explicit=True)'
    else:
        return f'union({", ".join([repr(t) for t in self.types])})'
union.__repr__ = union__repr__

tuple = namedtuple('tuple', ['id', 'types', 'explicit'])
def tuple__repr__(self):
    if self.explicit:
        return f'tuple({", ".join([repr(t) for t in self.types])}, explicit=True)'
    else:
        return f'tuple({", ".join([repr(t) for t in self.types])})'
tuple.__repr__ = tuple__repr__

struct = namedtuple('struct', ['id', 'fields', 'explicit'])
struct.__repr__ = lambda self: f'struct({self.fields!r})'

rec = namedtuple('rec', ['id', 'fields', 'explicit'])
rec.__repr__ = lambda self: f'rec({self.fields!r})'

seq = namedtuple('seq', ['id', 'contained', 'explicit'])
seq.__repr__ = lambda self: f'seq({self.contained!r})'

map = namedtuple('map', ['id', 'tLhs', 'tRhs', 'explicit'])
map.__repr__ = lambda self: f'map({self.tLhs!r}, {self.tRhs!r})'

fn = namedtuple('fn', ['id', 'tArgs', 'tRet', 'explicit'])
fn.__repr__ = lambda self: f'fn({self.tArgs!r}, {self.tRet!r})'

mutable = namedtuple('mutable', ['id', 'contained', 'explicit'])
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
        return f'TBC({self.name!r})'

