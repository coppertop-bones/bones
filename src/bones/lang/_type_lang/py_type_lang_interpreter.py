import builtins

import antlr4, itertools
from typing import Text
from collections import namedtuple

from bones.lang._type_lang.TypeLangLexer import TypeLangLexer
from bones.lang._type_lang.TypeLangParser import TypeLangParser
from bones.lang._type_lang.utils import ctxLabel

from bones.core.sentinels import Missing
from bones.core.errors import ProgrammerError

# OPEN: monkey patch the contexts corresponding to ruleNames, i.e. TypeLangParser.Tl_bodyContext, etc with a label
# property that returns the label of the rule or subrule, e.g. 'tl_body', 'ignore1', etc


Atom = namedtuple('Atom', ['id', 'name', 'explicit', 'space'])
Atom.__repr__ = lambda self: f'Atom({self.name!r}, explicit=True)' if self.explicit else f'Atom({self.name!r})'
Atom.__str__ = lambda self: f'"{self.name!s}"' if self.explicit else f'{self.name!s}'


Inter = namedtuple('Inter', ['id', 'types'])
def inter__repr__(self):
    return f'Inter({", ".join([repr(t) for t in self.types])})'
Inter.__repr__ = inter__repr__

Union = namedtuple('Union', ['id', 'types'])
def union__repr__(self):
    return f'Union({", ".join([repr(t) for t in self.types])})'
Union.__repr__ = union__repr__

Tuple = namedtuple('Tuple', ['id', 'types'])
def tuple__repr__(self):
    return f'Tuple({", ".join([repr(t) for t in self.types])})'
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

SchemaVar = namedtuple('SchemaVar', ['id', 'name'])
SchemaVar.__repr__ = lambda self: f'SchemaVar({self.name!r})'

class Recursive:
    __slots__ = ('id', 'name', 'main')
    def __init__(self, id, name):
        self.id = id
        self.main = Missing
        self.name = name
    def __repr__(self):
        # OPEN: handle recursion
        return f'Recursive({self.name!r})' if self.main else f'TBC({self.name!r})'




class PyTypeManager:
    __slots__ = [
        '_id', '_btypeById', '_btypeByVar', '_tbcByVar', '_interByTypes', '_unionByTypes', '_tupleByTypes',
        '_structByFields', '_recByFields', '_seqByContained', '_mapByLhsRhs', '_fnByLhsRhs', '_mutableByContained',
    ]

    def __init__(self):
        self._id = itertools.count(start=1)
        self._btypeById = {}
        self._btypeByVar = {}  # types that are assigned to variables (atoms, explicitly assigned and implicit recursives)
        self._tbcByVar = {}
        self._interByTypes = {}
        self._unionByTypes = {}
        self._tupleByTypes = {}
        self._structByFields = {}
        self._recByFields = {}
        self._seqByContained = {}
        self._mapByLhsRhs = {}
        self._fnByLhsRhs = {}
        self._mutableByContained = {}


class PyTypeLangInterpreter:
    __slots__ = ['_tm', '_btypeByCtx', '_implicitRecursive', '_last']

    def __init__(self, tm):
        self._tm = tm
        self._btypeByCtx = {}                   # includes intermediate types
        self._implicitRecursive = Missing
        self._last = Missing


    def parse(self, src):
        if isinstance(src, Text): src = antlr4.InputStream(src)
        l = TypeLangLexer(src)
        stream = antlr4.CommonTokenStream(l)
        p = TypeLangParser(stream)
        tree = p.tl_body()

        w = antlr4.ParseTreeWalker()
        w.walk(self, tree)
        return self._last


    def visitTerminal(self, node: antlr4.TerminalNode): pass
    def visitErrorNode(self, node: antlr4.ErrorNode):
        print(f'error: {node}')
        1/0
    def enterEveryRule(self, ctx: antlr4.ParserRuleContext): pass
    def exitEveryRule(self, ctx: antlr4. ParserRuleContext):
        label = ctxLabel(ctx)
        # print(label)
        if (fn := getattr(self, label, Missing)):
            fn(ctx)
        elif label.startswith('ignore'):
            pass
        else:
            raise ProgrammerError(f'Handler for "{label}" not defined')


    # RULES

    def assign_expr_to(self, ctx):
        var = ctx.name_.text
        expr = self._btypeByCtx[ctx.expr_]
        if (currentExpr := self._tm._btypeByVar.get(var, Missing)):

            if currentExpr.id != expr.id:
                if isinstance(currentExpr, Recursive) and currentExpr.main.id == expr.id:
                    pass
                else:
                    raise ValueError(f'"{var}" is already defined: {ctx.start.line}-{ctx.stop.line}')
        else:
            if self._implicitRecursive:
                if self._implicitRecursive.name == var:
                    self._implicitRecursive.main = expr
                    self._tm._btypeByVar[var] = self._implicitRecursive
                    self._tm._btypeById[self._implicitRecursive.id] = self._implicitRecursive
                    self._implicitRecursive = Missing
                else:
                    self._tm.raiseUnknownVariableEncountered(self._implicitRecursive.name, var, ctx)
            else:
                self._tm._btypeByVar[var] = expr
                self._tm._btypeById[expr.id] = expr
                self._tm._tbcByVar.pop(var, None)
        print(f'{var} <= {expr}')
        self._last = expr


    def atom(self, ctx):
        var = ctx.name_.text
        if (atom := self._tm._btypeByVar.get(var, Missing)):
            if not isinstance(atom, Atom): raise ValueError(f'"{var}" is already defined: {ctx.start.line}-{ctx.stop.line}')
        else:
            atom = Atom(next(self._tm._id), var, False, Missing)
            self._btypeByCtx[ctx] = atom
            self._tm._btypeByVar[var] = atom
            self._tm._btypeById[atom.id] = atom
        print(f'defining {var}: atom')
        self._last = atom
        return atom


    def atom_explicit(self, ctx):
        var = ctx.name_.text
        if (atom := self._tm._btypeByVar.get(var, Missing)):
            if not isinstance(atom, Atom): raise ValueError(f'"{var}" is already defined: {ctx.start.line}-{ctx.stop.line}')
            if not atom.explicit: raise ValueError(f'{atom} already defined but without explicit matching: {ctx.start.line}-{ctx.stop.line}')
        else:
            atom = Atom(next(self._tm._id), var, True, Missing)
            self._btypeByCtx[ctx] = atom
            self._tm._btypeByVar[var] = atom
            self._tm._btypeById[atom.id] = atom
        print(f'defining {var}: atom explicit')
        self._last = atom
        return atom


    def atom_explicit_in(self, ctx):
        var = ctx.name_.text
        orthspc = self.get(ctx.atom_)
        if (atom := self._tm._btypeByVar.get(var, Missing)) is Missing:
            atom = Atom(next(self._tm._id), var, True, orthspc)
            self._btypeByCtx[ctx] = atom
            self._tm._btypeByVar[var] = atom
            self._tm._btypeById[atom.id] = atom
        else:
            if not isinstance(atom, Atom): raise ValueError(f'"{var}" is already defined: {ctx.start.line}-{ctx.stop.line}')
            if not atom.explicit: raise ValueError(f'{atom} already defined but without explicit matching: {ctx.start.line}-{ctx.stop.line}')
        print(f'defining {var}: atom explicit in {orthspc}')
        self._last = atom
        return atom


    def atom_implicitly(self, ctx):
        var = ctx.name_.text
        orthspc = self.get(ctx.atom_)
        if (atom := self._tm._btypeByVar.get(var, Missing)):
            if not isinstance(atom, Atom): raise ValueError(f'"{var}" is already defined: {ctx.start.line}-{ctx.stop.line}')
        else:
            atom = Atom(next(self._tm._id), var, True, orthspc)
            self._btypeByCtx[ctx] = atom
            self._tm._btypeByVar[var] = atom
            self._tm._btypeById[atom.id] = atom
        print(f'defining {var}: atom explicit in {orthspc}')
        self._last = atom
        return atom


    def atom_in(self, ctx):
        var = ctx.name_.text
        orthspc = self.get(ctx.atom_)
        if (atom := self._tm._btypeByVar.get(var, Missing)):
            if not isinstance(atom, Atom): raise ValueError(f'"{var}" is already defined: {ctx.start.line}-{ctx.stop.line}')
        else:
            atom = Atom(next(self._tm._id), var, False, orthspc)
            self._btypeByCtx[ctx] = atom
            self._tm._btypeByVar[var] = atom
        print(f'defining {var}: atom in {orthspc}')
        self._last = atom
        return atom


    def atom_in_parens(self, ctx):
        pass


    atom_multi = atom


    def comment(self, ctx):
        if ctx.comment_.text == '// error':
            print(ctx.text)


    def check_all_consumed(self, ctx):
        if ctx.children:
            children = [e.symbol.text for e in ctx.children]
            print(f'\nUnconsumed tokens:\n{children}')
            raise SyntaxError()


    def expr_parens(self, ctx):
        pass


    def fn(self, ctx):
        tArgs = self._extractBtype(ctx.lhs_)
        tRet = self._extractBtype(ctx.rhs_)
        if (fn := self._tm._fnByLhsRhs.get((tArgs, tRet), Missing)) is Missing:
            fn = Fn(next(self._tm._id), tArgs, tRet)
            self._tm._btypeById[fn.id] = fn
            self._tm._fnByLhsRhs[(tArgs, tRet)] = fn
        self._btypeByCtx[ctx] = fn
        return fn


    def get(self, ctx):
        label = ctxLabel(ctx)
        if label == 'name':
            var = ctx.name_.text
            if (t := self._tm._btypeByVar.get(var, Missing)) is Missing:
                if (t := self._tm._tbcByVar.get(var, Missing)) is Missing:
                    if (t := self._implicitRecursive) is not Missing and t.name != var: self._raiseSecondImplicitRecursiveFound(var, ctx)
                    t = self._implicitRecursive = Recursive(next(self._tm._id), var)
                    print(f'defining implicit recursive "{var}"')
            return t
        elif label == 'atom_in_parens':
            return self._btypeByCtx[ctx.atom_]
        else:
            print(label)
            1/0


    def inter(self, ctx):
        types = []
        types = tuple(sorted(self._collectInters(types, ctx), key=lambda t: t.id))
        isIntermediate = ctxLabel(ctx.parentCtx) == 'inter'
        if (inter := self._tm._interByTypes.get(types, Missing)):
            if isIntermediate:
                pass
            else:
                if inter.id == 0:
                    # convert intermediate intersection to a final one
                    inter = Inter(next(self._tm._id), types)
                    self._tm._interByTypes[types] = self._tm._btypeById[inter.id] = inter
        else:
            if isIntermediate:
                inter = Inter(0, types)
            else:
                inter = Inter(next(self._tm._id), types)
                self._tm._btypeById[inter.id] = inter
            self._tm._interByTypes[types] = inter
        self._btypeByCtx[ctx] = inter
        return inter


    inter_low = inter


    def map(self, ctx):
        lhs = self._extractBtype(ctx.lhs_)
        rhs = self._extractBtype(ctx.rhs_)
        if (map := self._tm._mapByLhsRhs.get((lhs, rhs), Missing)) is Missing:
            map = Map(next(self._tm._id), lhs, rhs)
            self._tm._btypeById[map.id] = map
            self._tm._mapByLhsRhs[(lhs, rhs)] = map
        self._btypeByCtx[ctx] = map
        return map


    def mutable(self, ctx):
        contained = self._extractBtype(ctx.expr_)
        if (mutable := self._tm._mutableByContained.get(contained, Missing)) is Missing:
            mutable = Mutable(next(self._tm._id), contained)
            self._tm._btypeById[mutable.id] = mutable
            self._tm._mutableByContained[contained] = mutable
        self._btypeByCtx[ctx] = mutable
        return mutable


    def name(self, ctx):
        pass


    def name_or_atom(self, ctx):
        pass


    def prealloc(self, ctx):
        name = ctx.name_.text
        if name in self._tm._btypeByVar: raise ValueError(f'"{name}" is already defined: {ctx.start.line}-{ctx.stop.line}')
        if name in self._tm._tbcByVar: raise ValueError(f'"{name}" is already declared as recursive: {ctx.start.line}-{ctx.stop.line}')
        t = self._tm._tbcByVar[name] = Recursive(next(self._tm._id), name)
        print(f'{name} <= {t}')


    def rec(self, ctx):
        fields = []
        fields = tuple(self._collectFields(fields, ctx.fields_))
        # OPEN: do fields, types instead
        if (rec := self._tm._recByFields.get(fields, Missing)) is Missing:
            rec = Rec(next(self._tm._id), fields)
            self._tm._btypeById[rec.id] = rec
            self._tm._recByFields[fields] = rec
        self._btypeByCtx[ctx] = rec
        return rec


    def return_last(self, ctx):
        if self._implicitRecursive: raise ValueError(f'Implicit recursive variables not assigned: {self._implicitRecursive}')
        if self._tm._tbcByVar: raise ValueError(f'Declared recursive variables not assigned: {", ".join(self._tm._tbcByVar)}')
        print(f'RETURN {self._last}')


    def return_expr(self, ctx):
        if self._implicitRecursive: raise ValueError(f'Implicit recursive variables not assigned: {self._implicitRecursive}')
        if self._tm._tbcByVar: raise ValueError(f'Declared recursive variables not assigned: {", ".join(self._tm._tbcByVar)}')
        self._last = self._extractBtype(ctx.expr_)
        print(f'RETURN {self._last}')


    def return_named_or_atom(self, ctx):
        if self._implicitRecursive: raise ValueError(f'Implicit recursive variables not assigned: {self._implicitRecursive}')
        if self._tm._tbcByVar: raise ValueError(f'Declared recursive variables not assigned: {", ".join(self._tm._tbcByVar)}')
        self._last = self.get(ctx.name_or_atom_)
        print(f'RETURN {self._last}')


    def seq(self, ctx):
        lhs = ctx.lhs_.text
        contained = self._extractBtype(ctx.rhs_)
        if (seq := self._tm._seqByContained.get(contained, Missing)) is Missing:
            seq = Seq(next(self._tm._id), contained)
            self._tm._btypeById[seq.id] = seq
            self._tm._seqByContained[contained] = seq
        self._btypeByCtx[ctx] = seq
        return seq


    def struct(self, ctx):
        fields = []
        fields = tuple(self._collectFields(fields, ctx.fields_))
        # OPEN: do fields, types instead
        if (struct := self._tm._structByFields.get(fields, Missing)) is Missing:
            struct = Struct(next(self._tm._id), fields)
            self._tm._btypeById[struct.id] = struct
            self._tm._structByFields[fields] = struct
        self._btypeByCtx[ctx] = struct
        return struct


    def tuple(self, ctx):
        types = []
        types = builtins.tuple(self._collectTuples(types, ctx))
        isIntermediate = ctxLabel(ctx.parentCtx) == 'tuple'
        if (tuple := self._tm._tupleByTypes.get(types, Missing)):
            if isIntermediate:
                pass
            else:
                if tuple.id == 0:
                    # convert intermediate tuple to a final one
                    tuple = Tuple(next(self._tm._id), types)
                    self._tm._tupleByTypes[types] = self._tm._btypeById[tuple.id] = tuple
        else:
            if isIntermediate:
                tuple = Tuple(0, types)
            else:
                tuple = Tuple(next(self._tm._id), types)
                self._tm._btypeById[tuple.id] = tuple
            self._tm._tupleByTypes[types] = tuple
        self._btypeByCtx[ctx] = tuple
        return tuple


    def union(self, ctx):
        types = []
        types = tuple(sorted(self._collectUnions(types, ctx), key=lambda t: t.id))
        isIntermediate = ctxLabel(ctx.parentCtx) == 'union'
        if (union := self._tm._unionByTypes.get(types, Missing)):
            if isIntermediate:
                pass
            else:
                if union.id == 0:
                    # convert intermediate union to a final one
                    union = Union(next(self._tm._id), types)
                    self._tm._unionByTypes[types] = self._tm._btypeById[union.id] = union
        else:
            if isIntermediate:
                union = Union(0, types)
            else:
                union = Union(next(self._tm._id), types)
                self._tm._btypeById[union.id] = union
            self._tm._unionByTypes[types] = union
        self._btypeByCtx[ctx] = union
        return union



    # UTILITIES

    def _extractBtype(self, ctx):
        label = ctxLabel(ctx)
        if label == 'inter':        return self.inter(ctx)
        if label == 'union':        return self.union(ctx)
        if label == 'tuple':        return self.tuple(ctx)
        if label == 'struct':       return self.struct(ctx)
        if label == 'rec':          return self.rec(ctx)
        if label == 'seq':          return self.seq(ctx)
        if label == 'map':          return self.map(ctx)
        if label == 'fn':           return self.fn(ctx)
        if label == 'name_or_atom': return self.get(ctx.name_or_atom_)
        if label == 'expr_parens':  return self._extractBtype(ctx.expr_)
        if label == 'mutable':      return self.mutable(ctx)
        if label == 'atom_in_parens': return self._btypeByCtx[ctx.atom_]
        print(label)
        1/0



    def _ppexpr(self, ctx):
        msg = self._expr_imp(ctx)
        while msg.startswith('(') and msg.endswith(')'):
            msg = msg[1:-1]
        return msg


    def _expr_imp(self, ctx):
        label = ctxLabel(ctx)

        # assign_expr_imp rule
        if label == 'explicit_expr':     return f'{ctx.name_.text} <= {self._ppexpr(ctx.expr_)} exp'
        if label == 'assign_expr_to':    return f'{ctx.name_.text} <= {self._ppexpr(ctx.expr_)}'
        if label == 'prealloc':          return f'#define {ctx.name_.text}'

        # _ppexpr rule
        if label == 'inter':         return f'({self._expr_imp(ctx.lhs_)!s} & {self._expr_imp(ctx.rhs_)!s})'
        if label == 'union':         return f'({self._expr_imp(ctx.lhs_)} + {self._expr_imp(ctx.rhs_)})'
        if label == 'tuple':         return f'({self._expr_imp(ctx.lhs_)} * {self._expr_imp(ctx.rhs_)})'
        if label == 'struct':        return f'{{{", ".join(self._getFields(ctx.fields_))}}}'
        if label == 'rec':           return f'{{{{{", ".join(self._getFields(ctx.fields_))}}}}}'
        if label == 'seq':           return f'({self._expr_imp(ctx.lhs_)} ** {self._expr_imp(ctx.rhs_)})'
        if label == 'map':           return f'({self._expr_imp(ctx.lhs_)} ** {self._expr_imp(ctx.rhs_)})'
        if label == 'fn':            return f'({self._expr_imp(ctx.lhs_)} ^ {self._expr_imp(ctx.rhs_)})'
        if label == 'inter_low':     return f'(({self._ppexpr(ctx.lhs_)}) & {self._expr_imp(ctx.rhs_)})'
        if label == 'name_or_atom':  return self.get(ctx.name_or_atom_)
        if label == 'expr_parens':   return f'{self._expr_imp(ctx.expr_)}'
        if label == 'seq_var':       return f'{self._expr_imp(ctx.name_)}'
        if label == 'mut_name':      return f'*{ctx.name_.text}'

        if label == 'CommonToken':   return ctx.text
        return f'\nunhandled expr: {label}'


    def _getFields(self, ctx):
        fields = [self._field(ctx)]
        while ctx.rhs_:
            fields.append(self._field(ctx.rhs_))
            ctx = ctx.rhs_
        return fields


    def _field(self, ctx):
        return f'{self._expr_imp(ctx.name_)}={self._expr_imp(ctx.type_)}'


    def _collectInters(self, types, ctx):
        self._collectInters(types, ctx.lhs_) if ctxLabel(ctx.lhs_) == 'inter' else types.insert(0, self._extractBtype(ctx.lhs_))
        self._collectInters(types, ctx.rhs_) if ctxLabel(ctx.rhs_) == 'inter'  else types.append(self._extractBtype(ctx.rhs_))
        return types

    def _collectUnions(self, types, ctx):
        self._collectUnions(types, ctx.lhs_) if ctxLabel(ctx.lhs_) == 'union' else types.insert(0, self._extractBtype(ctx.lhs_))
        self._collectUnions(types, ctx.rhs_) if ctxLabel(ctx.rhs_) == 'union' else types.append(self._extractBtype(ctx.rhs_))
        return types

    def _collectTuples(self, types, ctx):
        self._collectTuples(types, ctx.lhs_) if ctxLabel(ctx.lhs_) == 'tuple' else types.insert(0, self._extractBtype(ctx.lhs_))
        self._collectTuples(types, ctx.rhs_) if ctxLabel(ctx.rhs_) == 'tuple' else types.append(self._extractBtype(ctx.rhs_))
        return types

    def _collectFields(self, fields, ctx):
        fields.append((ctx.name_.text, self._extractBtype(ctx.type_)))
        return self._collectFields(fields, ctx.rhs_) if getattr(ctx, 'rhs_', Missing) else fields

    def _checkExplicit(self, ctx, t):
        if not t.explicit:
            raise ValueError(f'{t} already defined as not being explicitly matched: {ctx.start.line}-{ctx.stop.line}')

    def _raiseUnknownVariableEncountered(self, recname, var, ctx):
        raise ValueError(f'Unassigned implicit recursive variable "{recname}" found whilst assigning "{var}": {ctx.start.line}-{ctx.stop.line}')

    def _raiseSecondImplicitRecursiveFound(self, var, ctx):
        raise ValueError(f'Another implicit recursive "{var}" found before current implicit recursive is assigned: {ctx.start.line}-{ctx.stop.line}')

