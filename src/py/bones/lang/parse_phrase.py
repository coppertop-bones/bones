# **********************************************************************************************************************
# Copyright (c) 2019-2022 David Briant. All rights reserved.
# This file is part of py-bones. For licensing contact David Briant.
# **********************************************************************************************************************

import sys

import bones.lang.types

if hasattr(sys, '_TRACE_IMPORTS') and sys._TRACE_IMPORTS: print(__name__)


from coppertop.pipe import nullary, unary, binary, ternary
from bones.core.errors import ProgrammerError, NotYetImplemented, PathNotTested, SentenceError, ErrSite, \
    DictionaryError
from bones.core.sentinels import Missing, Null
from bones.lang.core import RET_VAR_NAME
from bones.lang.lex import Token, prettyNameByTag, \
    START, INTEGER, DECIMAL, SYM, SYMS, TEXT, \
    DATE, LOCALTIME_M, LOCALTIME_S, LOCALTIME_SS, \
    GLOBALTIME_M, GLOBALTIME_SS, GLOBALTIME_S, \
    GLOBALTIMESTAMP_M, GLOBALTIMESTAMP_S, GLOBALTIMESTAMP_SS, \
    LOCALTIMESTAMP_SS, LOCALTIMESTAMP_S, LOCALTIMESTAMP_M, \
    NAME, SYMBOLIC_NAME, ASSIGN_RIGHT, \
    PARENT_VALUE_NAME, \
    CONTEXT_NAME, CONTEXT_ASSIGN_RIGHT, \
    GLOBAL_NAME, GLOBAL_ASSIGN_RIGHT, KEYWORD_OR_ASSIGN_LEFT, SYMBOLIC_NAME
from bones.lang.parse_structure import \
    LoadGroup, FromImportGroup, \
    FuncOrStructGroup, TupParenOrDestructureGroup, BlockGroup, \
    TypeLangGroup, \
    FrameGroup, _SemiColonSepCommaSepDotSep, SemiColonSepCommaSep, _DotOrCommaSep, _CommaSepDotSep
from bones.lang.ctx import VMeta, FnMeta
from bones.lang.tc import lit, voidPhrase, bindval, getval, getoverload, snippet, apply, bfunc, load, fromimport, \
    bindfn, getfamily, assumedfunc, litstruct, littup, litframe, getsubvalname, getsubvalindex
from bones.lang.metatypes import BTTuple, BTStruct
from bones.lang.ctx import LOCAL_SCOPE, PARENT_SCOPE, CONTEXT_SCOPE, GLOBAL_SCOPE, newFnCtx, ArgCatcher
from bones.lang.types import TBI
from bones.lang.parse_structure import DESTRUCTURE, TUPLE_NULL, TUPLE_2D, TUPLE_OR_PAREN, TUPLE_0_EMPTY, STRUCT, \
    TUPLE_1_EMPTY, TUPLE_2_EMPTY, TUPLE_3_EMPTY, TUPLE_4_PLUS_EMPTY, UNARY, BINARY, ASSIGN_LEFT, UNARY_OR_STRUCT
from bones.lang.parse_type_lang import parseTypeLang
from bones.lang.structs import tv


def parseSnippet(snippetGroup, ctx, k):
    # must not mutate sm
    tcs = [parsePhrase(phrase, ctx, k) for phrase in snippetGroup.phrases]
    return snippet(snippetGroup.tok1, snippetGroup.tok2, ctx, tcs)


def parseTupParenOrDestructureGroup(group, ctx, k):
    tt = group.tupleType
    if tt == DESTRUCTURE:
        raise NotYetImplemented()
    elif tt == TUPLE_NULL:
        raise NotYetImplemented()
    elif tt == TUPLE_2D:
        raise NotYetImplemented()
    elif tt == TUPLE_OR_PAREN:
        # of form `(a)`, i.e. no semi-colons and no commas - so just the one phrase and it's in the same ctx
        # OPEN: possibly we might like to have multiple phrases in parentheses   x * (fred: 1 + 1. joe: fred * 2. joe+fred)
        # OPEN: how to specify a 1d or 2d single element tuple? Maybe Python style with a comma or ; however that
        #   sort of precludes Missing elements in a tuple
        phrase = group.grid[0][0]
        tc = parsePhrase(phrase, ctx, k)
        return TUPLE_OR_PAREN, [tc]
    elif tt == TUPLE_0_EMPTY:
        if isinstance(group.grid, _SemiColonSepCommaSepDotSep):
            commaSepDotSepPhrase = group.grid[0]
            commaSepDotSepTc = _CommaSepDotSep()
            for dotSepPhrase in commaSepDotSepPhrase:
                dotSepTc = _DotOrCommaSep('.')
                for phrase in dotSepPhrase:
                    tc = parsePhrase(phrase, ctx, k)
                    dotSepTc << tc
                commaSepDotSepTc << dotSepTc
            return TUPLE_0_EMPTY, commaSepDotSepTc
        elif isinstance(group.grid, SemiColonSepCommaSep):
            commaSepPhrase = group.grid[0]
            dotSepTc = _DotOrCommaSep(',')
            for phrase in commaSepPhrase:
                tc = parsePhrase(phrase, ctx, k)
                dotSepTc << tc
            return TUPLE_0_EMPTY, dotSepTc
        else:
            raise ProgrammerError()
    elif tt == TUPLE_1_EMPTY:
        raise NotYetImplemented()
    elif tt == TUPLE_2_EMPTY:
        raise NotYetImplemented()
    elif tt == TUPLE_3_EMPTY:
        raise NotYetImplemented()
    elif tt == TUPLE_4_PLUS_EMPTY:
        raise NotYetImplemented()
    else:
        raise ProgrammerError()


def snippetOrTc(phrases):
    if isinstance(phrases, list):
        if len(phrases) == 1:
            return phrases[0]
        else:
            raise NotYetImplemented()
    else:
        return phrases

def buildFnApplication(lhs, ctxWithFn, fOrName, ctx, tokens, k):
    if isinstance(fOrName, bfunc):
        style = fOrName.literalstyle        # use the literal function's literal style
    else:
        style = ctx.styleOfName(fOrName)

    if lhs is Missing:
        # possibilities
        # fn ()                     (fn may have more than one tuple afterward)
        if len(tokens) == 1:
            x = parseSingle(tokens[0], ctx, k)
            return x, 1
        elif len(tokens) > 1:
            next = tokens[1]
            if isinstance(next, TupParenOrDestructureGroup):
                # e.g. fred(...)
                tupleType, tup = parseTupParenOrDestructureGroup(next, ctx, k)
                if tupleType == TUPLE_OR_PAREN:
                    # fn (a)        i.e. passing a into fn
                    rhs = tup
                    if ctxWithFn is Missing:
                        f = fOrName
                    else:
                        f = getoverload(tokens[0].tok1, ctxWithFn, fOrName, 1, LOCAL_SCOPE)      # OPEN handle partials
                    return apply(tokens[0].tok1, next.tok2, ctx, f, rhs), 2
                elif tupleType == TUPLE_0_EMPTY:
                    # fn(a,b,c)
                    if isinstance(tup, _SemiColonSepCommaSepDotSep):
                        rhs = [snippetOrTc(e) for e in tup]
                    elif isinstance(tup, SemiColonSepCommaSep):
                        rhs = [snippetOrTc(e) for e in tup]
                    elif isinstance(tup, _DotOrCommaSep):
                        rhs = [snippetOrTc(e) for e in tup]
                    elif isinstance(tup, _CommaSepDotSep):
                        rhs = [snippetOrTc(e[0]) for e in tup]
                    else:
                        raise ProgrammerError()
                    numargs = len(rhs)
                    if ctxWithFn is Missing:
                        f = fOrName
                    else:
                        f = getoverload(tokens[0].tok1, ctxWithFn, fOrName, numargs, LOCAL_SCOPE)      # OPEN handle partials
                    return apply(tokens[0].tok1, next.tok2, ctx, f, rhs), 2
                else:
                    raise ProgrammerError()
            elif isinstance(next, Token):
                if next.tag == ASSIGN_RIGHT:
                    # OPEN: handle {a+1} :f (1)   which should answer apply(bindfn('f', deffn(...)),1) but may impact elsewhere
                    # handled in main parse loop so just put the function in the lhs and consume 1 token
                    if ctxWithFn is Missing:
                        f = fOrName
                    else:
                        raise NotYetImplemented("need to copy every overload into the local ctx")
                    return f, 1
                else:
                    f = getfamily(tokens[0].tok1, ctxWithFn, fOrName, LOCAL_SCOPE)
                    return f, 1             # fn is probably being called as an argument
            else:
                raise NotYetImplemented()
        else:
            raise ProgrammerError()
    else:

        if style is unary:
            # noun unary                (unary may have tuples afterward)
            if len(tokens) > 1:
                next = tokens[1]
                if isinstance(next, TupParenOrDestructureGroup):
                    tupleType, tup = parseTupParenOrDestructureGroup(next, ctx, k.sm)
                    numargs = 1/0
                    raise NotYetImplemented()  # cound be various
                else:
                    numargs = 1
            else:
                numargs = 1
            if ctxWithFn is Missing:
                f = fOrName
            else:
                f = getoverload(tokens[0], ctxWithFn, fOrName, numargs, LOCAL_SCOPE)      # OPEN handle partials
            return apply(lhs.tok1, tokens[0], ctx, f, [lhs]), 1

        elif style is binary:
            # noun binary rhs           (binary and rhs may have tuples afterward)
            if len(tokens) == 1:
                raise SentenceError("incomplete phrase - [noun, binary] something needed after the binary")
            next = tokens[1]
            if isinstance(next, TupParenOrDestructureGroup):
                tupleType, tup = parseTupParenOrDestructureGroup(next, ctx, k.sm)
                if tupleType == TUPLE_OR_PAREN:
                    # of form `a binary (b)`
                    rhs = tup
                    numargs = 2
                    if ctxWithFn is Missing:
                        f = fOrName
                    else:
                        f = getoverload(1/0, ctxWithFn, fOrName, numargs, LOCAL_SCOPE)      # OPEN handle partials
                    return apply(1/0, 1/0, ctx, f, [lhs, rhs]), 2
                else:
                    # e.g. of form `a binary (,b,) c`
                    parenArgs = next.grid[0]
                    numargs = len(parenArgs)
                    raise NotYetImplemented("need to get the next one pipeable arg and merge with paren args")
            else:
                numargs = 2
                if ctxWithFn is Missing:
                    f = fOrName
                else:
                    f = getoverload(tokens[0].tok1, ctxWithFn, fOrName, numargs, LOCAL_SCOPE)      # OPEN handle partials
                rhs = parseSingle(next, ctx, k)
                return apply(lhs.tok1, rhs.tok2, ctx, f, [lhs, rhs]), 2

        elif style == ternary:
            # noun ternary rhs1 rhs2    (binary, rhs1 and rhs2 may have tuples afterward)
            if len(tokens) <= 2:
                raise SentenceError("incomplete phrase - [noun, binary] something needed after the ternary")
            next = tokens[1]
            if isinstance(next, TupParenOrDestructureGroup):
                tupleType, tup = parseTupParenOrDestructureGroup(next, ctx, k.sm)
                if tupleType == TUPLE_OR_PAREN:
                    # e.g. of form `a ternary (b) c`
                    rhs = tup
                    numargs = 3
                    if ctxWithFn is Missing:
                        f = fOrName
                    else:
                        f = getoverload(1/0, ctxWithFn, fOrName, numargs, LOCAL_SCOPE)      # OPEN handle partials
                    return apply(1/0, 1/0, ctx, f, [lhs, rhs]), 3
                else:
                    # e.g. of form `a binary (,b,,) c d`
                    parenArgs = next.grid[0]
                    numargs = len(parenArgs)
                    raise NotYetImplemented("need to get the next two pipeable args and merge with paren args")

            else:
                numargs = 3
                if ctxWithFn is Missing:
                    f = fOrName
                else:
                    f = getoverload(1/0, ctxWithFn, fOrName, numargs, LOCAL_SCOPE)      # OPEN handle partials
                rhs = parseSingle(next, ctx, k)
                return apply(1/0, 1/0, ctx, f, [lhs, rhs]), 2
        raise NotYetImplemented()


def parseSingle(t, ctx, k):
    if isinstance(t, Token):
        tag = t.tag
        if tag == NAME:
            name = t.src
            meta = ctx.fOrVMetaForGet(name, LOCAL_SCOPE)
            if meta is Missing: raise SentenceError(f"unknown name - {name}")
            if isinstance(meta, VMeta):
                return getval(t.tok1, meta.ctx, name, meta.t, LOCAL_SCOPE)
            else:
                return getfamily(t.tok1, meta.ctx, name, LOCAL_SCOPE)
        elif tag == INTEGER:
            return lit(t.tok1, ctx, *k.sm.parseLitInt(t.src))
        elif tag == DECIMAL:
            return lit(t.tok1, ctx, *k.sm.parseLitDec(t.src))
        elif tag == TEXT:
            return lit(t.tok1, ctx, *k.sm.parseLitUtf8(t.src))
        else:
            missingTag = prettyNameByTag[tag]
            raise NotYetImplemented()
    else:
        raise NotYetImplemented()

def parseParameters(params, fnctx, k):
    argnames = []
    tArgs = []
    for tokens in params.phrases:
        name, tp = tokens[0].nameToken.src, tokens[0].typePhrase
        if len(tp) > 0:
            t = parseTypeLang(tp, k)
        else:
            t = TBI
        fnctx.defVMeta(name, t)
        argnames.append(name)
        tArgs.append(t)
    return argnames, tArgs


def parsePhrase(tokens, ctx, k):
    # must not mutate sm

    if not tokens: return voidPhrase(ctx)

    lhs = Missing

    tokens = _queue(tokens[1:] if isinstance(tokens[0], Token) and tokens[0].tag == START else tokens)

    while tokens:
        t = tokens[0]
        if isinstance(t, Token):
            tag = t.tag

            if tag == SYMBOLIC_NAME:
                name = t.src
                meta = ctx.fMetaForGet(name, LOCAL_SCOPE)
                if meta is Missing: raise DictionaryError(f"unknown function - {name}", ErrSite("unknown function"))
                lhs, numConsumed = buildFnApplication(lhs, meta.ctx, name, ctx, tokens, k)
                tokens >> numConsumed

            elif tag == NAME:
                name = t.src
                # for the moment check every name for dots - could (should?) be done by lexer
                names = name.split('.')
                name, otherNames = (names[0], names[1:]) if len(names) > 1 else (name, [])
                meta = ctx.fOrVMetaForGet(name, LOCAL_SCOPE)
                if meta is Missing:
                    raise SentenceError(f"unknown name - {name}", ErrSite("unknown name"))
                if isinstance(meta, FnMeta):
                    if otherNames:
                        raise SentenceError(f"{t.src} makes no sense as {name} is a function", ErrSite("NAME #1"))
                    lhs, numConsumed = buildFnApplication(lhs, meta.ctx, name, ctx, tokens, k)
                    tokens >> numConsumed
                elif len(tokens) > 1 and isinstance(tokens[1], TupParenOrDestructureGroup) and name in ctx.argCatcher.inferredArgnames:
                    if otherNames:
                        raise SentenceError(f"{t.src} makes no sense, e.g. inferredArg.a.b(...) - need to explain why in normal speak", ErrSite("NAME #2"))
                    # ambiguous - is `inferredArg (...)` an object object apply or a fun apply
                    # design decision - decide that it is the latter
                    meta = ctx.changeVMetaToFnMeta(name)
                    # these don't make sense:
                    # `arg1 inferredArg` unary? but inferredArg could be a symbol so an object object apply
                    # `arg1 inferredArg arg2` binary? but inferredArg could be a symbol so an object object apply
                    # potentially the following could be allowed:
                        # `arg1 inferredArg(,...)` unary with partial
                        # `arg1 inferredArg(,,...) arg2` binary with partial
                        # `arg1 inferredArg(,,,...) arg2 arg3` ternary with partial
                    # however to keep the usage of inferred arguments we'll limit inferred functions to fn(...) form
                    if lhs is not Missing: raise SentenceError(f"object {name}(...) not allowed", ErrSite("object name(...) not allowed"))
                    # TODO add a test to check that `{1 + f(x)}` is handled correctly (i.e. the binary + doesn't appear in lhs here)
                    lhs, numConsumed = buildFnApplication(lhs, meta.ctx, name, ctx, tokens, k)
                    numArgs = lhs.fnnode.numargs
                    f = assumedfunc(t.tok1, t.tok2, Missing, ['?'] * numArgs, BTTuple(*(TBI,) * numArgs), TBI, Missing, nullary)
                    overload = ctx.bindFn(name, f)    # add the function to the local ctx - the TBIs will be converted to type variables later
                    tokens >> numConsumed
                else:
                    lhs = getval(t, meta.ctx, name, LOCAL_SCOPE)
                    lhs.tOut = meta.t
                    tokens >> 1
                    if otherNames:
                        for name in otherNames:
                            lhs = getsubvalname(t, ctx, lhs, name)

            elif tag == PARENT_VALUE_NAME:
                name = t.src
                meta = ctx.vMetaForGet(name, PARENT_SCOPE)
                if meta is Missing: raise SentenceError(f"unknown parent value name - {name}")
                raise NotYetImplemented()

            elif tag == CONTEXT_NAME:
                name = t.src
                meta = ctx.fOrVMetaForGet(name, CONTEXT_NAME)
                if meta is Missing: raise SentenceError(f"unknown context name - {name}")
                raise NotYetImplemented()

            elif tag == GLOBAL_NAME:
                name = t.src
                meta = ctx.vMetaForGet(name, GLOBAL_SCOPE)
                if meta is Missing: raise SentenceError(f"unknown parent value name - {name}")
                raise NotYetImplemented()

            elif tag == ASSIGN_RIGHT:
                name = t.src
                # take care with ctx here - probably needs careful thinking through
                if isinstance(lhs, bfunc):
                    # meta = ctx.fMetaForBind(name, LOCAL_SCOPE)
                    # if meta is not Missing:
                    #     raise SentenceError(f'{name} already defined', ErrSite("name already defined"))
                    # more may need to happen here - e.g. check for style tag
                    ctx.defFnMeta(name, TBI, LOCAL_SCOPE)   # create a slot in the ctx for the fn
                    ctx.bindFn(name, lhs)       # add it to the overloads (it will be queued if it needs inferring)
                    currentStyle = k.styleByName.setdefault(name, lhs.literalstyle)
                    if lhs.literalstyle != currentStyle:
                        raise NotYetImplemented("Note that style has been changed")
                    lhs = bindfn(min(t.tok1, lhs.tok1), max(t.tok2, lhs.tok2), ctx, name, lhs, LOCAL_SCOPE)
                    tokens >> 1
                else:
                    # meta = ctx.vMetaForBind(name, LOCAL_SCOPE)
                    # if meta is not Missing:
                    #     raise SentenceError(f'{name} already defined', ErrSite("name already defined"))
                    ctx.defVMeta(name, TBI, LOCAL_SCOPE)
                    #HACK
                    lhs = lhs[0] if isinstance(lhs, list) else lhs
                    lhs = bindval(t.tok1, t.tok2, ctx, name, lhs, LOCAL_SCOPE)
                    tokens >> 1

            elif tag == CONTEXT_ASSIGN_RIGHT:
                name = t.src
                meta = ctx.fOrVMetaForBind(name, CONTEXT_SCOPE)
                raise NotYetImplemented()

            elif tag == GLOBAL_ASSIGN_RIGHT:
                name = t.src
                meta = ctx.vMetaForBind(name, GLOBAL_SCOPE)
                if meta is not Missing:
                    raise SentenceError(f'{name} already defined', ErrSite("name already defined"))
                else:
                    ctx.defVMeta(name, TBI, GLOBAL_SCOPE)
                    lhs = bindval(ctx, name, lhs, GLOBAL_SCOPE)
                    tokens >> 1

            elif tag == INTEGER:
                lhs = lit(t.tok1, ctx, *k.sm.parseLitInt(t.src))
                tokens >> 1

            elif tag == DECIMAL:
                lhs = lit(t.tok1, ctx, *k.sm.parseLitDec(t.src))
                tokens >> 1

            elif tag == TEXT:
                lhs = lit(t.tok1, ctx, *k.sm.parseLitUtf8(t.src))
                tokens >> 1

            elif tag == SYM:
                lhs = lit(t.tok1, ctx, *k.sm.parseLitSym(t.src))
                tokens >> 1

            elif tag == SYMS:
                lhs = lit(t.tok1, ctx, *k.sm.parseLitSyms(t.src))
                tokens >> 1

            elif tag == DATE:
                lhs = lit(t.tok1, ctx, *k.sm.parseLitDate(t.src))
                tokens >> 1

            elif tag in (
                    GLOBALTIMESTAMP_SS, GLOBALTIMESTAMP_S, GLOBALTIMESTAMP_M, LOCALTIMESTAMP_SS, LOCALTIMESTAMP_S,
                    LOCALTIMESTAMP_M, GLOBALTIME_SS, GLOBALTIME_S, GLOBALTIME_M, LOCALTIME_SS, LOCALTIME_S, LOCALTIME_M
            ):
                raise NotYetImplemented()

            else:
                if tag == ASSIGN_LEFT:
                    k.dumpLines(t.srcId, t.l1-3, t.l2)
                    raise ProgrammerError("Looks like the grouping hasn't worked proprerly", ErrSite("Encountered ASSIGN_LEFT"))
                else: raise ProgrammerError()

        else:

            if isinstance(t, FuncOrStructGroup):
                if len(tokens) == 1: raise Exception("doesn't make sense to have just a function or a struct by itself on a line")
                elif t._unaryBinaryOrStruct == STRUCT:
                    # create the litstruct and the struct type
                    vs, names, ts = [], [], []
                    for v, nameToken in t.phrases:
                        names.append(k.sm.parseLitSym(nameToken.src)[1])
                        node = parsePhrase([v], ctx, k)
                        vs.append(node)
                        ts.append(node.tOut)
                    tStruct = BTStruct(names, ts) & bones.lang.types.litstruct
                    tvObj = tv(tStruct, dict(zip(names, vs)))
                    tokens >> 1
                    lhs = litstruct(t.tok1, t.tok2, ctx, tvObj)
                elif t._unaryBinaryOrStruct == UNARY_OR_STRUCT:
                    raise NotYetImplemented()
                else:
                    fnCtx = newFnCtx(ctx)
                    if t._params is Missing:
                        fnCtx.argCatcher = ArgCatcher([])
                    else:
                        argnames, tArgs = parseParameters(t._params, fnCtx, k.sm)
                    tRet = TBI if t._tRet is Missing else parseTypeLang(t._tRet, k)
                    body = [parsePhrase(phrase, fnCtx, k) for phrase in t.phrases]
                    if t._params is Missing:
                        argnames = fnCtx.argCatcher.inferredArgnames
                        argnames.sort(key=_inDictionaryOrder)
                        tArgs = [TBI] * len(argnames)
                    if t._unaryBinaryOrStruct == UNARY: style = unary
                    elif t._unaryBinaryOrStruct == BINARY: style = binary
                    else: raise ProgrammerError()
                    fnCtx.defVMeta(RET_VAR_NAME, TBI, LOCAL_SCOPE)
                    f = bfunc(t.tok1, t.tok1, fnCtx, argnames, BTTuple(*tArgs), tRet, body, style)
                    tokens[0] = f
                    lhs, numConsumed = buildFnApplication(lhs, Missing, f, ctx, tokens, k.sm)
                    tokens >> numConsumed

            elif isinstance(t, TupParenOrDestructureGroup):
                if t.tupleType == TUPLE_OR_PAREN:
                    if lhs is Missing:
                        # of form `(a)` - is it a tuple of one element or a parenthesis?
                        # for the moment we will assume a parenthesis -> 1 entup to make a one tuple? like q
                        tupleType, tup = parseTupParenOrDestructureGroup(t, ctx, k)
                        lhs = tup
                        tokens >> 1
                    else:
                        # two possible intentions
                        #   1) object paren, intended as an object object apply OR
                        #   2) fn paren
                        # three cases -
                        #   1) lhs is a function (but that is handled in the NAME case)
                        #   2) lhs is a value - known from the name space
                        #   3) lhs is TBI - i.e. a parameter
                        # OPEN: could set this up to be handled in inference or even later but for now assume the TBI is a function

                        # create a fn with generic tArgs and tRet
                        name = lhs.name
                        if ctx.argCatcher and name in ctx.argCatcher.inferredArgnames:
                            ctx.changeVMetaToFnMeta(name)
                        tupleType, tup = parseTupParenOrDestructureGroup(t, ctx, k)
                        numArgs = 1
                        fnode = getoverload(t.tok1, ctx, name, numArgs, LOCAL_SCOPE)      # OPEN handle partials
                        f = bfunc(t.tok1, t.tok2, Missing, ['?'] * numArgs, BTTuple(*(TBI,)*numArgs), TBI, Missing, unary)
                        overload = ctx.bindFn(name, f)
                        lhs = apply(t.tok1, t.tok2, ctx, fnode, tup)
                        tokens >> 1
                else:
                    raise ProgrammerError("all other cases should be captured in buildFnApplication")

            elif isinstance(t, BlockGroup):
                raise NotYetImplemented()

            elif isinstance(t, FrameGroup):
                raise NotYetImplemented()

            elif isinstance(t, LoadGroup):
                # i.e. searches PYTHON_PATH and BONES_PATH for bones/ex/ and load core.py or core.b
                paths = []
                for tok in t.phrases[0]:
                    paths.append(tok.src)
                lhs = load(t.tok1, t.tok2, ctx, paths)
                k.loadModules(lhs.paths)
                tokens >> 1

            elif isinstance(t, FromImportGroup):
                names = []
                for phr in t.phrases:
                    name = ''
                    for tok in phr:
                        if tok.tag == KEYWORD_OR_ASSIGN_LEFT:
                            name += tok.src
                            name += ':'
                        elif tok.tag in (NAME, SYMBOLIC_NAME):
                            name += tok.src
                        else:
                            raise NotYetImplemented()
                    names.append(name)
                lhs = fromimport(t.tok1, t.tok2, ctx, t.path, names)
                k.importSymbols(lhs.path, lhs.names, lhs.ctx)
                tokens >> 1

            elif isinstance(t, TypeLangGroup):
                raise NotYetImplemented()

            else:
                raise ProgrammerError()

    return lhs


def _inDictionaryOrder(x):
    o = ord(x)
    if o >= 96:
        return (o - 96)*2
    else:
        return (o - 65) * 2 + 1


class _queue(list):
    # could make more efficient by creating a view into tokens rather than copying?
    def __rshift__(self, other):    # self >> other
        for i in range(other):
            self.pop(0)
        return self
