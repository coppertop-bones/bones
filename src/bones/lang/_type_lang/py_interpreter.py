import antlr4, itertools, traceback
from typing import Text
from collections import namedtuple

from bones.lang._type_lang.TypeLangLexer import TypeLangLexer
from bones.lang._type_lang.TypeLangParser import TypeLangParser
from bones.lang._type_lang.ast_builder import TypeLangAstBuilder, TLError

from bones.core.sentinels import Missing
from bones.core.errors import ProgrammerError, NotYetImplemented

# OPEN: monkey patch the contexts corresponding to ruleNames, i.e. TypeLangParser.Tl_bodyContext, etc with a label
# property that returns the label of the rule or subrule, e.g. 'tl_body', 'ignore1', etc


_gVarnameById = Missing

def atom__repr__(self):
    return f'{_gVarnameById[self.id]}'

def inter__repr__(self):
    return f'Inter{self.id}({" & ".join([repr(t) for t in self.types])})'

def union__repr__(self):
    return f'Union{self.id}({" + ".join([repr(t) for t in self.types])})'

def tuple__repr__(self):
    return f'Tup{self.id}({" * ".join([repr(t) for t in self.types])})'


# types

Atom = namedtuple('Atom', ['id', 'explicit', 'space', 'implicitly'])
Atom.__repr__ = atom__repr__

Inter = namedtuple('Inter', ['id', 'types', 'space'])
Inter.__repr__ = inter__repr__

Union = namedtuple('Union', ['id', 'types'])
Union.__repr__ = union__repr__

Tuple = namedtuple('Tuple', ['id', 'types'])
Tuple.__repr__ = tuple__repr__

Struct = namedtuple('Struct', ['id', 'fields'])
Struct.__repr__ = lambda self: f'Struct({self.fields!r})'

Rec = namedtuple('Rec', ['id', 'fields'])
Rec.__repr__ = lambda self: f'Rec({self.fields!r})'

Seq = namedtuple('Seq', ['id', 'contained'])
Seq.__repr__ = lambda self: f'Seq({self.contained!r})'

Map = namedtuple('Map', ['id', 'tLhs', 'tRhs'])
Map.__repr__ = lambda self: f'Map({self.tLhs!r}, {self.tRhs!r})'

Fn = namedtuple('Fn', ['id', 'tArgs', 'tRet'])
Fn.__repr__ = lambda self: f'Fn({self.tArgs!r}, {self.tRet!r})'

Mutable = namedtuple('Mutable', ['id', 'contained'])
Mutable.__repr__ = lambda self: f'Mutable({self.contained!r})'

SchemaVar = namedtuple('SchemaVar', ['id'])
SchemaVar.__repr__ = lambda self: f'SchemaVar({self.id!r})'

class Recursive:
    __slots__ = ('id', 'main', 'space')
    def __init__(self, id, space):
        self.id = id
        self.main = Missing
        self.space = space
    def __repr__(self):
        # OPEN: handle recursion - could add varname for PP
        if self.main:
            return f'Recursive({type(self.main).__name__})' + (f' in {self.space.name}' if self.space else '')
        else:
            return f'TBC({self.id})' + (f' in {self.space.name}' if self.space else '')


class PyTypeManager:
    __slots__ = [
        '_seed', '_btypeById', '_idByVarname', '_varnameById', '_checkpointIds', '_implicitRecursiveId', '_tbcIdByVarname',
        '_unwinds',
        '_interByTypes', '_unionByTypes', '_tupleByTypes', '_structByFields', '_recByFields', '_seqByContained',
        '_mapByLhsRhs', '_fnByLhsRhs', '_mutableByContained',
    ]

    def __init__(self):
        global _gVarnameById
        self._seed = itertools.count(start=1)
        self._btypeById = {}
        self._idByVarname = {}
        self._varnameById = _gVarnameById = {}
        self._checkpointIds = []
        self._implicitRecursiveId = Missing
        self._tbcIdByVarname = {}

        self._unwinds = Missing
        
        self._interByTypes = {}
        self._unionByTypes = {}
        self._tupleByTypes = {}
        self._structByFields = {}
        self._recByFields = {}
        self._seqByContained = {}
        self._mapByLhsRhs = {}
        self._fnByLhsRhs = {}
        self._mutableByContained = {}

        for i in range(1, 20):
            t = SchemaVar(next(self._seed))
            self._btypeById[t.id] = t
            self._idByVarname[f'T{t.id}'] = t.id
            self._varnameById[t.id] = f'T{t.id}'

    def __getitem__(self, varname):
        return self._btypeById[self._idByVarname[varname]]

    def has(self, varname):
        return varname in self._idByVarname

    def get(self, varname):
        # gets the type for the name creating up to one implicit recursive type if it doesn't exist
        if (btypeid := self._idByVarname.get(varname, Missing)) is Missing:
            if (btypeid := self._tbcIdByVarname.get(varname, Missing)) is Missing:
                if (btypeid := self._implicitRecursiveId) is not Missing and self._varnameById[btypeid] != varname:
                    raise TLError(f'Only one implicit recursive type can be define simutaneously. "{varname}" encountered but "{self._varnameById[btypeid]}" is already the currently defined implicit recursive type.')
                btypeid = (btype := self.recursive(Missing)).id
                self._implicitRecursiveId = self._tbcIdByVarname[varname] = btypeid
                self._idByVarname[varname] = btypeid
                self._varnameById[btypeid] = varname
        return self._btypeById[btypeid]

    def set(self, varname, btype):
        # checks the type if it already exists (so can do identical redefines) and sets the type for the name
        # clearing any recursive types (including the single implicit one) that are waiting

        if (currentid := self._idByVarname.get(varname, Missing)) is not Missing:
            # if recursive define else check
            if currentid == btype.id:
                # same
                return btype
            else:
                if isinstance(currentType := self._btypeById[currentid], Recursive):
                    if currentType.main is Missing:
                        # define recursive type
                        if (rec := self._tbcIdByVarname.pop(varname, Missing)) is Missing:
                            raise ProgrammerError(f'Expected to find recursive type "{varname}" in _tbcIdByVarname')
                        if self._implicitRecursiveId == currentid:
                            # we are now defining the sole implicit recursive type
                            self._implicitRecursiveId = Missing
                        currentType.main = btype
                        print(f'{varname}: {self.pp(btype)}')
                        return btype
                    else:
                        # check recursive type
                        if currentType.main.id == btype.id:
                            # same
                            return btype
                        else:
                            raise TLError(f'Variable "{varname}" already defined as recursive type with "{currentType.main}"')
                else:
                    # different
                    raise TLError(f'Variable "{varname}" already defined as type "{currentType}')
        else:
            # define
            self._idByVarname[varname] = btype.id
            self._varnameById[btype.id] = varname
            if isinstance(btype, Recursive):
                self._tbcIdByVarname[varname] = btype.id
            print(f'{varname}: {self.pp(btype)}')
            return btype

    def pp(self, t):
        if isinstance(t, Atom):
            name = self._varnameById[t.id]
            return f'Atom({name}, explicit=True)' if t.explicit else f'Atom({name})'
            # f'"{self.name!s}"' if self.explicit else f'{self.name!s}'
        elif isinstance(t, Recursive):
            name = self._varnameById[t.id]
            return f'Recursive({name}, in={self.pp(t.space)})' if t.space else f'Recursive({name})'
        else:
            return repr(t)

    def onErrRollback(self):
        return OnErrorRollback(self)

    def checkImplicitRecursiveAssigned(self):
        if (btypeid := self._implicitRecursiveId) is not Missing:
            raise TLError(f'Implicit recursive type "{self._varnameById[btypeid]}" has not been assigned')
        return Missing

    def done(self):
        if self._implicitRecursiveId: raise ValueError(f'Implicit recursive variables not assigned: {self._implicitRecursiveId}')
        if self._tbcIdByVarname: raise ValueError(f'Declared recursive variables not assigned: {", ".join(self._tbcIdByVarname)}')
        return None

    def atom(self, explicit, space, implicitly, varname):
        if (currentId := self._idByVarname.get(varname, Missing)) is Missing:
            atom = Atom(next(self._seed), explicit, space, implicitly)
            self._btypeById[atom.id] = atom
        else:
            if not (current := self._btypeById[currentId]).explicit and explicit: raise TLError(f'"{varname}" is already defined but without explicit matching')
            if current.space != space: raise TLError(f'"{varname}" is already defined in space "{self.pp(current.space)}"')
            if current.implicitly != implicitly: raise TLError(f'"{varname}" is already defined as implicitly "{self.pp(current.implicitly)}"')
            atom = current
        return atom

    def recursive(self, space):
        t = Recursive(next(self._seed), space)
        self._btypeById[t.id] = t
        return t

    def inter(self, types, space):
        sortedtypes = []
        for t in (sorted(types, key=lambda t: t.id)):
            if t not in sortedtypes:
                sortedtypes.append(t)
        roots = set([_rootParent(t, self).id for t in sortedtypes])
        if len(roots) < len(sortedtypes):
            raise TLError('common rooots')
        sortedtypes = tuple(sortedtypes)
        if (inter := self._interByTypes.get(sortedtypes, Missing)) is Missing:
            inter = Inter(next(self._seed), sortedtypes, space)
            self._btypeById[inter.id] = inter
            self._interByTypes[sortedtypes] = inter
        return inter

    def union(self, types):
        sortedtypes = []
        for t in (sorted(types, key=lambda t: t.id)):
            if t not in sortedtypes:
                sortedtypes.append(t)
        sortedtypes = tuple(sortedtypes)
        if (union := self._unionByTypes.get(sortedtypes, Missing)) is Missing:
            union = Union(next(self._seed), types)
            self._btypeById[union.id] = union
            self._unionByTypes[sortedtypes] = union
        return union

    def tuple(self, types):
        if (tup := self._tupleByTypes.get(types, Missing)) is Missing:
            tup = Tuple(next(self._seed), types)
            self._btypeById[tup.id] = tup
            self._tupleByTypes[types] = tup
        return tup

    def struct(self, fields):
        if (struct := self._structByFields.get(fields, Missing)) is Missing:
            struct = Struct(next(self._seed), fields)
            self._btypeById[struct.id] = struct
            self._structByFields[fields] = struct
        return struct

    def rec(self, fields):
        if (rec := self._recByFields.get(fields, Missing)) is Missing:
            rec = Rec(next(self._seed), fields)
            self._btypeById[rec.id] = rec
            self._recByFields[fields] = rec
        return rec

    def seq(self, contained):
        contained = contained[0]
        if (seq := self._seqByContained.get(contained, Missing)) is Missing:
            seq = Seq(next(self._seed), contained)
            self._btypeById[seq.id] = seq
            self._seqByContained[contained] = seq
        return seq

    def map(self, types):
        if (map := self._mapByLhsRhs.get(types, Missing)) is Missing:
            map = Map(next(self._seed), types[0], types[1])
            self._btypeById[map.id] = map
            self._mapByLhsRhs[types] = map
        return map

    def mutable(self, contained):
        contained = contained[0]
        if (mutable := self._mutableByContained.get(contained, Missing)) is Missing:
            mutable = Mutable(next(self._seed), contained)
            self._btypeById[mutable.id] = mutable
            self._mutableByContained[contained] = mutable
        return mutable

    def fn(self, types):
        if (fn := self._fnByLhsRhs.get(types, Missing)) is Missing:
            fn = Fn(next(self._seed), types[0], types[1])
            self._btypeById[fn.id] = fn
            self._fnByLhsRhs[types] = fn
        return fn

    def fitsWithin(self, A, B):
        if A.id == B.id: return True
        if isinstance(A, Atom):
            if isinstance(B, Atom): return A.id == B.id
            elif isinstance(B, Union):
                for t in B.types:
                    if self.fitsWithin(A, t): return True
                return False
            else:
                raise NotYetImplemented('#1')
        elif isinstance(A, Inter):
            if isinstance(B, Inter):
                raise NotYetImplemented('need to decompose')
            for t in A.types:
                if self.fitsWithin(t, B): return True
        elif isinstance(A, Union):
            if isinstance(B, Union):
                for t in A.types:
                    if not self.fitsWithin(t, B): return False
                return True
            else:
                return False
        else:
            raise NotYetImplemented('#3')
        return False


def _rootParent(t, tm):
    if isinstance(t, (Atom, Inter)) and t.space is not Missing:
        return _rootParent(t.space.eval(tm), tm)
    else:
        return t


class PyTypeLangInterpreter:
    def __init__(self, tm):
        self._btypeByCtx = {}                   # includes intermediate types
        self._implicitRecursiveId = Missing
        self._tm = tm

    def parse(self, src):
        if isinstance(src, Text): src = antlr4.InputStream(src)
        l = TypeLangLexer(src)
        stream = antlr4.CommonTokenStream(l)
        p = TypeLangParser(stream)
        tree = p.tl_body()

        w = antlr4.ParseTreeWalker()
        b = TypeLangAstBuilder()
        w.walk(b, tree)
        last = Missing
        for element in b.ast:
            last = element.eval(self._tm) or last
        return last


class OnErrorRollback:

    def __init__(self, tm):
        self.tm = tm
        self.et = None
        self.ev = None
        self.tb = None

    def __enter__(self):
        return self

    def __exit__(self, et, ev, tb):
        self.et = et
        self.ev = ev
        self.tb = tb
        if et is None:
            # no exception was raised
            return True
        else:
            # print the tb to make it easier to figure what happened
            traceback.print_tb(tb)
            raise ev

