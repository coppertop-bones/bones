


BTAtom = collections.namedtuple('BTAtom', ['id', 'name'])
BTAtom.__repr__ = lambda self: f'BTAtom({self.name})'
BTAtom.__str__ = lambda self: self.name

BTUnion = collections.namedtuple('BTUnion', ['id', 'types'])
BTUnion.__repr__ = lambda self: f'BTUnion({list(self.types)})'
BTUnion.__str__ = lambda self: ' + '.join(sorted(str(e) for e in self.types))

BTIntersection = collections.namedtuple('BTIntersection', ['id', 'types'])
BTIntersection.__repr__ = lambda self: f'BTIntersection({list(self.types)})'
BTIntersection.__str__ = lambda self: ' & '.join(sorted(str(e) for e in self.types))

BTTuple = collections.namedtuple('BTTuple', ['id', 'types'])
BTTuple.__repr__ = lambda self: f'BTTuple({list(self.types)})'
BTTuple.__str__ = lambda self: ' * '.join(str(e) for e in self.types)

BTStruct = collections.namedtuple('BTStruct', ['id', 'names', 'types'])
BTStruct.__repr__ = lambda self: f'BTStruct({list(self.types)})'
BTStruct.__str__ = lambda self: ' * '.join(str(e) for e in self.types)

BTSeq = collections.namedtuple('BTSeq', ['id', 'type'])
BTSeq.__repr__ = lambda self: f'BTSeq({self.type})'
BTSeq.__str__ = lambda self: ' * '.join(str(e) for e in self.types)

BTMap = collections.namedtuple('BTMap', ['id', 'tKey', 'tRet'])
BTMap.__repr__ = lambda self: f'BTMap({list(self.types)})'
BTMap.__str__ = lambda self: ' * '.join(str(e) for e in self.types)

BTFn = collections.namedtuple('BTFn', ['id', 'names', 'tArgs', 'tRet'])
BTFn.__repr__ = lambda self: f'BTFn({list(self.names)}, {list(self.tArgs)}, {self.tRet})'
BTFn.__str__ = lambda self: ' * '.join(str(e) for e in self.types)

BTSchemaVar = collections.namedtuple('BTSchemaVar', ['id', 'name'])
BTSchemaVar.__repr__ = lambda self: f'BTSchemaVar({list(self.names)}, {list(self.tArgs)}, {self.tRet})'
BTSchemaVar.__str__ = lambda self: ' * '.join(str(e) for e in self.types)


class TypeManager:
    __slots__ = [
        '_next_id', 'types', 'atoms', 'intersections', 'unions', 'tuples', 'seqs', 'maps', 'fns', 'schemavars',
        'globals', 'locals'
    ]

    def __init__(self):

        self._next_id = itertools.count(1)
        self.types = {}  # keyed by id
        self.atoms = {}  # keyed by name
        self.intersections = {}  # keyed by sorted type ids
        self.unions = {}  # keyed by sorted type ids
        self.tuples = {}  # keyed by type ids
        self.seqs = {}  # keyed by contained type id
        self.maps = {}  # keyed by tKey, tValue
        self.fns = {}  # keyed by tArg, tRet
        self.schemavars = {}  # keyed by tArg, tRet

        self.globals = {}  # keyed by name
        self.locals = {}  # keyed by name

    def __getitem__(self, k):
        if isinstance(k, int):
            return self.types[k]
        elif isinstance(k, str):
            return self.globals.get(k, Missing) or self.locals[k]
        else:
            raise TypeError(f'k must be an int or str gor {k}')

    def parse(self, src):
        tokens = list(tokenize(src))
        ast = Parser(tokens, self).ast
        return ast


def test_atom():
    tm = TypeManager()
    t1 = parse('''
        txt: atom
        txt
    ''')
    t2 = tm['txt']
    assert isinstance(t1, BTAtom), f'{t1} is not a BTAtom'
    assert t1 is t2 , f'{t1} is not {t2}'


def test_intersection():
    tm = TypeManager()
    tm.parse('''
        txt: atom
        isin: atom
        t1: isin & txt
        t2: txt & isin
    ''')
    t1 = tm['t1']
    t2 = tm['t2']
    assert t1 is t2, f'{t1} != {t2}'


def test_union(tm):
    tm = TypeManager()
    tm.parse('''
        txt: atom
        err: atom
        t1: txt + err
        t2: err + txt
    ''')
    t1 = tm['t1']
    t2 = tm['t2']
    assert t1 is t2, f'{t1} != {t2}'


def test_intersection_union_precedence():
    tm = TypeManager()
    tm.parse('''
        txt: atom
        isin: atom
        err: atom
        t1: txt & isin + err
        t2: err + isin & txt
    ''')
    t1 = tm['t1']
    t2 = tm['t2']
    assert t1 is t2, f'{t1} != {t2}'


def test_parse_expr():
    tm = TypeManager()
    tm.parse('''
        txt: atom
        isin: atom
        err: atom
        t1: txt & isin + err
    ''')
    t1 = tm['t1']
    t2 = tm.parse('err + isin & txt')
    assert t1 is t2, f'{t1} != {t2}'


def test_tuple():
    tm = TypeManager()
    tm.parse('''
        txt: atom
        isin: atom
        err: atom
        f64: atom
        t1: f64 * txt & isin + err
        t2: f64 * txt & isin + err * f64
        t3: f64 * txt & isin + err * f64
    ''')
    f64, u1 = tm['f64'], tm.parse('err + isin & txt')
    t1, t2, t3 = tm['t1'], tm['t2'], tm['t3']
    assert t1.types == (f64, u1), f'{t1.types} != {(f64, u1)}'
    assert t2.types == (f64, u1, f64), f'{t2.types} != {(f64, u1, f64)}'
    assert t2 is t3, f'{t2} != {t3}'


def test_paren():
    tm = TypeManager()
    tm.parse('''
        txt: atom
        isin: atom
        err: atom
        f64: atom
        t1: f64 * txt & isin + err * f64 * txt & isin + err 
        t2: (f64 * txt & isin + err) * (f64 * txt & isin + err) 
        t3: f64 * txt & isin + err
        t4: t3 * t3
    ''')
    t1, t2, t4 = tm['t1'], tm['t2'], tm['t4']
    assert t1 is not t2, f'{t1} == {t2}'
    assert t2 is t4, f'{t2} == {t4}'


def test_all():
    test_atom()
    test_intersection()
    test_union()
    test_intersection_union_precedence()
    test_parse_expr()
    test_tuple()
    test_paren()
    print("All tests passed!")

test_all_ast()
test_all()