import builtins

import antlr4, itertools
from bones.lang._type_lang.tests import btypes

from bones.core.sentinels import Missing

# here we will construct the types from the input

# OPEN: monkey patch the contexts corresponding to ruleNames, i.e. TypeLangParser.Tl_bodyContext, etc with a label
# property that returns the label of the rule or subrule, e.g. 'tl_body', 'ignore1', etc

makeTuple = builtins.tuple

_id = itertools.count(start=1)
_btypeById = {}
_btypeByVar = {}            # types that are assigned to variables (atoms, explicitly assigned and implicit recursives)
_btypeByCtx = {}            # includes intermediate types
_implicitRecursive = Missing
_tbcByVar = {}
_interByTypes = {}
_unionByTypes = {}
_tupleByTypes = {}
_structByFields = {}
_recByFields = {}
_seqByContained = {}
_mapByLhsRhs = {}
_fnByLhsRhs = {}
_mutableByContained = {}





class Listener:
    def visitTerminal(self, node: antlr4.TerminalNode): pass
    def visitErrorNode(self, node: antlr4.ErrorNode):
        print(f'error: {node}')
        1/0
    def enterEveryRule(self, ctx: antlr4.ParserRuleContext): pass
    def exitEveryRule(self, ctx: antlr4. ParserRuleContext):
        label = ctxLabel(ctx)
        if (fn := globals().get(f'{label}')): fn(ctx)
        # print(label)


# RULES

def assign_expr_to(ctx):
    global _implicitRecursive
    var = ctx.name_.text
    expr =_btypeByCtx[ctx.expr_]
    if (currentExpr := _btypeByVar.get(var, Missing)):
        if currentExpr.id != expr.id:
            if isinstance(currentExpr, btypes.recursive) and currentExpr.main.id == expr.id:
                pass
            else:
                raise ValueError(f'"{var}" is already defined: {ctx.start.line}-{ctx.stop.line}')
    else:
        if _implicitRecursive:
            if _implicitRecursive.name == var:
                _implicitRecursive.main = expr
                _btypeByVar[var] = _implicitRecursive
                _btypeById[_implicitRecursive.id] = _implicitRecursive
                _implicitRecursive = Missing
            else:
                _raiseUnknownVariableEncountered(_implicitRecursive.name, var, ctx)
        else:
            _btypeByVar[var] = expr
            _btypeById[expr.id] = expr
            _tbcByVar.pop(var, None)
    print(f'{var} <= {expr}')


def atom(ctx):
    var = ctx.name_.text
    if (atom := _btypeByVar.get(var, Missing)):
        if not isinstance(atom, btypes.atom): raise ValueError(f'"{var}" is already defined: {ctx.start.line}-{ctx.stop.line}')
    else:
        atom = btypes.atom(next(_id), var, False, Missing)
        _btypeByCtx[ctx] = atom
        _btypeByVar[var] = atom
        _btypeById[atom.id] = atom
    print(f'defining {var}: atom')
    return atom


def atom_explicit(ctx):
    var = ctx.name_.text
    if (atom := _btypeByVar.get(var, Missing)):
        if not isinstance(atom, btypes.atom): raise ValueError(f'"{var}" is already defined: {ctx.start.line}-{ctx.stop.line}')
        if not atom.explicit: raise ValueError(f'{atom} already defined but without explicit matching: {ctx.start.line}-{ctx.stop.line}')
    else:
        atom = btypes.atom(next(_id), var, True, Missing)
        _btypeByCtx[ctx] = atom
        _btypeByVar[var] = atom
        _btypeById[atom.id] = atom
    print(f'defining {var}: atom explicit')
    return atom


def atom_explicit_in(ctx):
    var = ctx.name_.text
    orthspc = get(ctx.atom_)
    if (atom := _btypeByVar.get(var, Missing)) is Missing:
        atom = btypes.atom(next(_id), var, True, orthspc)
        _btypeByCtx[ctx] = atom
        _btypeByVar[var] = atom
        _btypeById[atom.id] = atom
    else:
        if not isinstance(atom, btypes.atom): raise ValueError(f'"{var}" is already defined: {ctx.start.line}-{ctx.stop.line}')
        if not atom.explicit: raise ValueError(f'{atom} already defined but without explicit matching: {ctx.start.line}-{ctx.stop.line}')
    print(f'defining {var}: atom explicit in {orthspc}')
    return atom


def atom_implicitly(ctx):
    var = ctx.name_.text
    orthspc = get(ctx.atom_)
    if (atom := _btypeByVar.get(var, Missing)):
        if not isinstance(atom, btypes.atom): raise ValueError(f'"{var}" is already defined: {ctx.start.line}-{ctx.stop.line}')
    else:
        atom = btypes.atom(next(_id), var, True, orthspc)
        _btypeByCtx[ctx] = atom
        _btypeByVar[var] = atom
        _btypeById[atom.id] = atom
    print(f'defining {var}: atom explicit in {orthspc}')
    return atom


def atom_in(ctx):
    var = ctx.name_.text
    orthspc = get(ctx.atom_)
    if (atom := _btypeByVar.get(var, Missing)):
        if not isinstance(atom, btypes.atom): raise ValueError(f'"{var}" is already defined: {ctx.start.line}-{ctx.stop.line}')
    else:
        atom = btypes.atom(next(_id), var, False, orthspc)
        _btypeByCtx[ctx] = atom
        _btypeByVar[var] = atom
    print(f'defining {var}: atom in {orthspc}')
    return atom


atom_multi = atom


def comment(ctx):
    if ctx.comment_.text == '// error':
        print(ctx.text)


def fn(ctx):
    tArgs = _extractBtype(ctx.lhs_)
    tRet = _extractBtype(ctx.rhs_)
    if (fn := _fnByLhsRhs.get((tArgs, tRet), Missing)) is Missing:
        fn = btypes.fn(next(_id), tArgs, tRet)
        _btypeById[fn.id] = fn
        _fnByLhsRhs[(tArgs, tRet)] = fn
    _btypeByCtx[ctx] = fn
    return fn


def get(ctx):
    global _implicitRecursive
    label = ctxLabel(ctx)
    if label == 'name':
        var = ctx.name_.text
        if ctx.start.line in (69,):
            a = 1
        if (t := _btypeByVar.get(var, Missing)) is Missing:
            if (t := _tbcByVar.get(var, Missing)) is Missing:
                if (t := _implicitRecursive) is not Missing and t.name != var: _raiseSecondImplicitRecursiveFound(var, ctx)
                t = _implicitRecursive = btypes.recursive(next(_id), var)
                print(f'defining implicit recursive "{var}"')
        return t
    elif label == 'atom_in_parens':
        return _btypeByCtx[ctx.atom_]
    else:
        print(label)
        1/0


def inter(ctx):
    types = []
    types = makeTuple(sorted(_collectInters(types, ctx), key=lambda t: t.id))
    isIntermediate = ctxLabel(ctx.parentCtx) == 'inter'
    if (inter := _interByTypes.get(types, Missing)):
        if isIntermediate:
            pass
        else:
            if inter.id == 0:
                # convert intermediate intersection to a final one
                inter = btypes.inter(next(_id), types)
                _interByTypes[types] = _btypeById[inter.id] = inter
    else:
        if isIntermediate:
            inter = btypes.inter(0, types)
        else:
            inter = btypes.inter(next(_id), types)
            _btypeById[inter.id] = inter
        _interByTypes[types] = inter
    _btypeByCtx[ctx] = inter
    return inter


inter_low = inter


def map(ctx):
    lhs = _extractBtype(ctx.lhs_)
    rhs = _extractBtype(ctx.rhs_)
    if (map := _mapByLhsRhs.get((lhs, rhs), Missing)) is Missing:
        map = btypes.map(next(_id), lhs, rhs)
        _btypeById[map.id] = map
        _mapByLhsRhs[(lhs, rhs)] = map
    _btypeByCtx[ctx] = map
    return map


def mutable(ctx):
    contained = _extractBtype(ctx.expr_)
    if (mutable := _mutableByContained.get(contained, Missing)) is Missing:
        mutable = btypes.mutable(next(_id), contained)
        _btypeById[mutable.id] = mutable
        _mutableByContained[contained] = mutable
    _btypeByCtx[ctx] = mutable
    return mutable


def prealloc(ctx):
    name = ctx.name_.text
    if name in _btypeByVar: raise ValueError(f'"{name}" is already defined: {ctx.start.line}-{ctx.stop.line}')
    if name in _tbcByVar: raise ValueError(f'"{name}" is already declared as recursive: {ctx.start.line}-{ctx.stop.line}')
    t = _tbcByVar[name] = btypes.recursive(next(_id), name)
    print(f'{name} <= {t}')


def rec(ctx):
    fields = []
    fields = makeTuple(_collectFields(fields, ctx.fields_))
    # OPEN: do fields, types instead
    if (rec := _recByFields.get(fields, Missing)) is Missing:
        rec = btypes.rec(next(_id), fields)
        _btypeById[rec.id] = rec
        _recByFields[fields] = rec
    _btypeByCtx[ctx] = rec
    return rec


def return_expr(ctx):
    print(_ppexpr(ctx.expr_))


def seq(ctx):
    lhs = ctx.lhs_.text
    contained = _extractBtype(ctx.rhs_)
    if (seq := _seqByContained.get(contained, Missing)) is Missing:
        seq = btypes.seq(next(_id), contained)
        _btypeById[seq.id] = seq
        _seqByContained[contained] = seq
    _btypeByCtx[ctx] = seq
    return seq


def struct(ctx):
    fields = []
    fields = makeTuple(_collectFields(fields, ctx.fields_))
    # OPEN: do fields, types instead
    if (struct := _structByFields.get(fields, Missing)) is Missing:
        struct = btypes.struct(next(_id), fields)
        _btypeById[struct.id] = struct
        _structByFields[fields] = struct
    _btypeByCtx[ctx] = struct
    return struct


def tuple(ctx):
    types = []
    types = makeTuple(_collectTuples(types, ctx))
    isIntermediate = ctxLabel(ctx.parentCtx) == 'tuple'
    if (tuple := _tupleByTypes.get(types, Missing)):
        if isIntermediate:
            pass
        else:
            if tuple.id == 0:
                # convert intermediate tuple to a final one
                tuple = btypes.tuple(next(_id), types)
                _tupleByTypes[types] = _btypeById[tuple.id] = tuple
    else:
        if isIntermediate:
            tuple = btypes.tuple(0, types)
        else:
            tuple = btypes.tuple(next(_id), types)
            _btypeById[tuple.id] = tuple
        _tupleByTypes[types] = tuple
    _btypeByCtx[ctx] = tuple
    return tuple


def union(ctx):
    types = []
    types = makeTuple(sorted(_collectUnions(types, ctx), key=lambda t: t.id))
    isIntermediate = ctxLabel(ctx.parentCtx) == 'union'
    if (union := _unionByTypes.get(types, Missing)):
        if isIntermediate:
            pass
        else:
            if union.id == 0:
                # convert intermediate union to a final one
                union = btypes.union(next(_id), types)
                _unionByTypes[types] = _btypeById[union.id] = union
    else:
        if isIntermediate:
            union = btypes.union(0, types)
        else:
            union = btypes.union(next(_id), types)
            _btypeById[union.id] = union
        _unionByTypes[types] = union
    _btypeByCtx[ctx] = union
    return union



# UTILITIES

def _extractBtype(ctx):
    label = ctxLabel(ctx)
    if label == 'inter':        return inter(ctx)
    if label == 'union':        return union(ctx)
    if label == 'tuple':        return tuple(ctx)
    if label == 'struct':       return struct(ctx)
    if label == 'rec':          return rec(ctx)
    if label == 'seq':          return seq(ctx)
    if label == 'map':          return map(ctx)
    if label == 'fn':           return fn(ctx)
    if label == 'name_or_atom': return get(ctx.name_or_atom_)
    if label == 'expr_parens':  return _extractBtype(ctx.expr_)
    if label == 'mutable':      return mutable(ctx)
    if label == 'atom_in_parens': return _btypeByCtx[ctx.atom_]
    print(label)
    1/0



def _ppexpr(ctx):
    msg = _expr_imp(ctx)
    while msg.startswith('(') and msg.endswith(')'):
        msg = msg[1:-1]
    return msg


def _expr_imp(ctx):
    label = ctxLabel(ctx)

    # assign_expr_imp rule
    if label == 'explicit_expr':     return f'{ctx.name_.text} <= {_ppexpr(ctx.expr_)} exp'
    if label == 'assign_expr_to':    return f'{ctx.name_.text} <= {_ppexpr(ctx.expr_)}'
    if label == 'prealloc':          return f'#define {ctx.name_.text}'

    # _ppexpr rule
    if label == 'inter':         return f'({_expr_imp(ctx.lhs_)!s} & {_expr_imp(ctx.rhs_)!s})'
    if label == 'union':         return f'({_expr_imp(ctx.lhs_)} + {_expr_imp(ctx.rhs_)})'
    if label == 'tuple':         return f'({_expr_imp(ctx.lhs_)} * {_expr_imp(ctx.rhs_)})'
    if label == 'struct':        return f'{{{", ".join(_getFields(ctx.fields_))}}}'
    if label == 'rec':           return f'{{{{{", ".join(_getFields(ctx.fields_))}}}}}'
    if label == 'seq':           return f'({_expr_imp(ctx.lhs_)} ** {_expr_imp(ctx.rhs_)})'
    if label == 'map':           return f'({_expr_imp(ctx.lhs_)} ** {_expr_imp(ctx.rhs_)})'
    if label == 'fn':            return f'({_expr_imp(ctx.lhs_)} ^ {_expr_imp(ctx.rhs_)})'
    if label == 'inter_low':     return f'(({_ppexpr(ctx.lhs_)}) & {_expr_imp(ctx.rhs_)})'
    if label == 'name_or_atom':  return get(ctx.name_or_atom_)
    if label == 'expr_parens':   return f'{_expr_imp(ctx.expr_)}'
    if label == 'seq_var':       return f'{_expr_imp(ctx.name_)}'
    if label == 'mut_name':      return f'*{ctx.name_.text}'

    if label == 'CommonToken':   return ctx.text
    return f'\nunhandled expr: {label}'


def _getFields(ctx):
    fields = [_field(ctx)]
    while ctx.rhs_:
        fields.append(_field(ctx.rhs_))
        ctx = ctx.rhs_
    return fields


def _field(ctx):
    return f'{_expr_imp(ctx.name_)}={_expr_imp(ctx.type_)}'


def ctxLabel(ctx):
    label = type(ctx).__name__
    if label.endswith('Context'): label = label[:-7].lower()
    return label

def _collectInters(types, ctx):
    _collectInters(types, ctx.lhs_) if ctxLabel(ctx.lhs_) == 'inter' else types.insert(0, _extractBtype(ctx.lhs_))
    _collectInters(types, ctx.rhs_) if ctxLabel(ctx.rhs_) == 'inter'  else types.append(_extractBtype(ctx.rhs_))
    return types

def _collectUnions(types, ctx):
    _collectUnions(types, ctx.lhs_) if ctxLabel(ctx.lhs_) == 'union' else types.insert(0, _extractBtype(ctx.lhs_))
    _collectUnions(types, ctx.rhs_) if ctxLabel(ctx.rhs_) == 'union' else types.append(_extractBtype(ctx.rhs_))
    return types

def _collectTuples(types, ctx):
    _collectTuples(types, ctx.lhs_) if ctxLabel(ctx.lhs_) == 'tuple' else types.insert(0, _extractBtype(ctx.lhs_))
    _collectTuples(types, ctx.rhs_) if ctxLabel(ctx.rhs_) == 'tuple' else types.append(_extractBtype(ctx.rhs_))
    return types

def _collectFields(fields, ctx):
    fields.append((ctx.name_.text, _extractBtype(ctx.type_)))
    return _collectFields(fields, ctx.rhs_) if ctx.rhs_ else fields

def _checkExplicit(ctx, t):
    if not t.explicit:
        raise ValueError(f'{t} already defined as not being explicitly matched: {ctx.start.line}-{ctx.stop.line}')

def _raiseUnknownVariableEncountered(recname, var, ctx):
    raise ValueError(f'Unassigned implicit recursive variable "{recname}" found whilst assigning "{var}": {ctx.start.line}-{ctx.stop.line}')

def _raiseSecondImplicitRecursiveFound(var, ctx):
    raise ValueError(f'Another implicit recursive "{var}" found before current implicit recursive is assigned: {ctx.start.line}-{ctx.stop.line}')

