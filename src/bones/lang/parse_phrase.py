# **********************************************************************************************************************
# Copyright 2025 David Briant, https://github.com/coppertop-bones. Licensed under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance with the License. You may obtain a copy of the  License at
# http://www.apache.org/licenses/LICENSE-2.0. Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY  KIND,
# either express or implied. See the License for the specific language governing permissions and limitations under the
# License. See the NOTICE file distributed with this work for additional information regarding copyright ownership.
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
    START, NULL, INTEGER, DECIMAL, SYM, SYMS, TEXT, \
    DATE, LOCALTIME_M, LOCALTIME_S, LOCALTIME_SS, \
    GLOBALTIME_M, GLOBALTIME_SS, GLOBALTIME_S, \
    GLOBALTIMESTAMP_M, GLOBALTIMESTAMP_S, GLOBALTIMESTAMP_SS, \
    LOCALTIMESTAMP_SS, LOCALTIMESTAMP_S, LOCALTIMESTAMP_M, \
    NAME, SYMBOLIC_NAME, ASSIGN_RIGHT, ASSIGN_LEFT, \
    PARENT_VALUE_NAME, \
    CONTEXT_NAME, CONTEXT_ASSIGN_RIGHT, \
    GLOBAL_NAME, GLOBAL_ASSIGN_RIGHT, KEYWORD_OR_ASSIGN_LEFT, SYMBOLIC_NAME, ELLIPSES
from bones.lang.parse_groups import \
    LoadGroup, FromImportGroup, \
    FuncOrStructGroup, TupParenOrDestructureGroup, BlockGroup, \
    TypeLangGroup, \
    FrameGroup, _SemiColonSepCommaSepDotSep, SemiColonSepCommaSep, _DotOrCommaSep, _CommaSepDotSep
from bones.lang.symbol_table import VMeta, FnMeta
from bones.lang.tc import lit, voidPhrase, bindval, getval, getoverload, snippet, apply, bfunc, load, fromimport, \
    bindfn, getfamily, assumedfunc, litstruct, littup, litframe, getsubvalname, getsubvalindex, block
from bones.ts.metatypes import BTTuple, BTStruct
from bones.lang.symbol_table import LOCAL_SCOPE, PARENT_SCOPE, CONTEXT_SCOPE, GLOBAL_SCOPE, fnSymTab, ArgCatcher, blockSymTab
from bones.lang.types import TBI
from bones.lang.parse_groups import DESTRUCTURE, TUPLE_NULL, TUPLE_2D, TUPLE_OR_PAREN, TUPLE_0_EMPTY, STRUCT, \
    TUPLE_1_EMPTY, TUPLE_2_EMPTY, TUPLE_3_EMPTY, TUPLE_4_PLUS_EMPTY, UNARY, BINARY, UNARY_OR_STRUCT
from bones.ts.type_lang import TypeLangInterpreter


def parseSnippet(snippetGroup, st, k):
    # must not mutate sm
    tcs = [parsePhrase(phrase, st, k) for phrase in snippetGroup.phrases]
    return snippet(snippetGroup.tok1, snippetGroup.tok2, st, tcs)


def parseTupParenOrDestructureGroup(group, st, k):
    tt = group.tupleType
    if tt == DESTRUCTURE:
        raise NotYetImplemented()
    elif tt == TUPLE_NULL:
        raise NotYetImplemented()
    elif tt == TUPLE_2D:
        raise NotYetImplemented()
    elif tt == TUPLE_OR_PAREN:
        # of form `(a)`, i.e. no semi-colons and no commas - so just the one phrase and it's in the same st
        # OPEN: possibly we might like to have multiple phrases in parentheses   x * (fred: 1 + 1. joe: fred * 2. joe+fred)
        # OPEN: how to specify a 1d or 2d single element tuple? Maybe Python style with a comma or ; however that
        #   sort of precludes Missing elements in a tuple
        phrase = group.grid[0][0]
        tc = parsePhrase(phrase, st, k)
        return TUPLE_OR_PAREN, [tc]
    elif tt == TUPLE_0_EMPTY:
        if isinstance(group.grid, _SemiColonSepCommaSepDotSep):
            commaSepDotSepPhrase = group.grid[0]
            commaSepDotSepTc = _CommaSepDotSep()
            for dotSepPhrase in commaSepDotSepPhrase:
                dotSepTc = _DotOrCommaSep('.')
                for phrase in dotSepPhrase:
                    tc = parsePhrase(phrase, st, k)
                    dotSepTc << tc
                commaSepDotSepTc << dotSepTc
            return TUPLE_0_EMPTY, commaSepDotSepTc
        elif isinstance(group.grid, SemiColonSepCommaSep):
            commaSepPhrase = group.grid[0]
            dotSepTc = _DotOrCommaSep(',')
            for phrase in commaSepPhrase:
                tc = parsePhrase(phrase, st, k)
                dotSepTc << tc
            return TUPLE_0_EMPTY, dotSepTc
        else:
            raise ProgrammerError()
    elif tt == TUPLE_1_EMPTY:
        if isinstance(group.grid, SemiColonSepCommaSep):
            commaSepPhrase = group.grid[0]
            commaSepTc = _DotOrCommaSep(',')
            for phrase in commaSepPhrase:
                tc = parsePhrase(phrase, st, k)
                commaSepTc << tc
            return TUPLE_1_EMPTY, commaSepTc
        else:
            raise ProgrammerError()
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


def buildFnApplication(node, ctxWithFn, fOrName, st, tokens, k):
    style = fOrName.literalstyle if isinstance(fOrName, bfunc) else st.styleOfName(fOrName)

    if node is Missing:
        # possibilities
        # fn ()                     (fn may have more than one tuple afterward)
        if len(tokens) == 1:
            x = parseSingle(tokens[0], st, k)
            return x, 1
        elif len(tokens) > 1:
            next = tokens[1]
            if isinstance(next, TupParenOrDestructureGroup):
                # e.g. fred(...)
                tupleType, tup = parseTupParenOrDestructureGroup(next, st, k)
                if tupleType == TUPLE_OR_PAREN:
                    # fn (a)        i.e. passing a into fn
                    rhs = tup
                    if ctxWithFn is Missing:
                        f = fOrName
                    else:
                        f = getoverload(tokens[0].tok1, ctxWithFn, fOrName, 1, LOCAL_SCOPE)      # OPEN handle partials
                    return apply(tokens[0].tok1, next.tok2, st, f, rhs), 2
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
                    return apply(tokens[0].tok1, next.tok2, st, f, rhs), 2
                else:
                    raise ProgrammerError()
            elif isinstance(next, Token):
                if next.tag == ASSIGN_RIGHT:
                    # OPEN: handle {a+1} :f (1)   which should answer apply(bindfn('f', deffn(...)),1) but may impact elsewhere
                    # handled in main parse loop so just put the function in the node and consume 1 token
                    if ctxWithFn is Missing:
                        f = fOrName
                    else:
                        raise NotYetImplemented("need to copy every overload into the local symtab")
                    return f, 1
                else:
                    f = getfamily(tokens[0].tok1, ctxWithFn, fOrName, LOCAL_SCOPE)
                    return f, 1             # fn is probably being called as an argument
            else:
                raise NotYetImplemented()
        else:
            raise ProgrammerError()


    elif style is unary:
        # noun unary            (unary may have tuples afterward)
        if len(tokens) > 1 and isinstance(postUnaryTok := tokens[1], TupParenOrDestructureGroup):
            tupleType, tup = parseTupParenOrDestructureGroup(postUnaryTok, st, k.sm)
            if tupleType == TUPLE_OR_PAREN:
                # noun unary (...)
                raise NotYetImplemented("need to get the next one pipeable arg and merge with paren args")
            elif tupleType == TUPLE_1_EMPTY:
                # noun unary(,args)
                rhs = postUnaryTok.tok2
                f = fOrName if ctxWithFn is Missing else getoverload(tokens[0].tok1, ctxWithFn, fOrName, len(tup), LOCAL_SCOPE)
                for i in range(len(tup)):
                    if isinstance(tup[i], voidPhrase):
                        tup[i] = node
                        break
                return apply(node.tok1, rhs, st, f, tup), 2
            else:
                raise SentenceError("error needs describing properly")
        else:
            # noun unary
            rhs = tokens[0].tok2
            f = fOrName if ctxWithFn is Missing else getoverload(tokens[0].tok1, ctxWithFn, fOrName, 1, LOCAL_SCOPE)
        return apply(node.tok1, tokens[0], st, f, [node]), 1


    elif style is binary:
        # noun binary arg2          (binary and arg2 may have tuples afterward)
        if len(tokens) < 2: raise SentenceError("incomplete phrase - {noun, binary} is missing args after the binary")
        postBinaryTok = tokens[1]
        if isinstance(postBinaryTok, TupParenOrDestructureGroup):
            tupleType, tup = parseTupParenOrDestructureGroup(postBinaryTok, st, k.sm)
            if tupleType == TUPLE_OR_PAREN:
                # noun binary (arg2)
                arg2 = tup[0]
                rhs = postBinaryTok.tok2
                f = fOrName if ctxWithFn is Missing else getoverload(tokens[0].tok1, ctxWithFn, fOrName, 2, LOCAL_SCOPE)
            else:
                # e.g. noun binary (,,args) arg2`
                parenArgs = postBinaryTok.grid[0]
                rhs = postBinaryTok.tok2
                f = fOrName if ctxWithFn is Missing else getoverload(tokens[0].tok1, ctxWithFn, fOrName, len(parenArgs), LOCAL_SCOPE)
                # OPEN: handle arg2(...)
                raise NotYetImplemented("need to get the next one pipeable arg and merge with paren args")
        else:
            arg2 = parseSingle(postBinaryTok, st, k)
            rhs = arg2.tok2
            f = fOrName if ctxWithFn is Missing else getoverload(tokens[0].tok1, ctxWithFn, fOrName, 2, LOCAL_SCOPE)      # OPEN handle partials

        return apply(node.tok1, rhs, st, f, [node, arg2]), 2


    elif style is ternary:
        # noun ternary arg2 arg3    (ternary, arg2 and arg3 may have parens afterward)
        if len(tokens) < 3: raise SentenceError(f"incomplete phrase - {{noun, ternary{', arg2' if len(tokens) == 2 else ''}}} is missing args after the ternary")

        i = 1

        # handle token after ternary
        tok = tokens[i]
        if isinstance(tok, TupParenOrDestructureGroup):
            tupleType, tup = parseTupParenOrDestructureGroup(tok, st, k.sm)
            if tupleType == TUPLE_OR_PAREN:
                # e.g. of form `noun ternary (arg2) arg3`
                arg2 = tup[0]
                f = fOrName if ctxWithFn is Missing else getoverload(tokens[0].tok1, ctxWithFn, fOrName, 3, LOCAL_SCOPE)  # OPEN handle partials
                i += 1
            else:
                # e.g. of form `noun ternary (,,...) arg2 arg3`
                parenArgs = tok.grid[0]
                f = fOrName if ctxWithFn is Missing else getoverload(tokens[0].tok1, ctxWithFn, fOrName, len(parenArgs), LOCAL_SCOPE)  # OPEN handle partials
                raise NotYetImplemented("need to get the postTernaryTok two pipeable args and merge with paren args")
        else:
            arg2 = parseSingle(tok, st, k)  # OPEN: handle post arg2 to parens
            f = fOrName if ctxWithFn is Missing else getoverload(tokens[0].tok1, ctxWithFn, fOrName, 3, LOCAL_SCOPE)  # OPEN handle partials
            i += 1

        # handle token after arg2
        tok = tokens[i]
        if isinstance(tok, TupParenOrDestructureGroup):
            tupleType, tup = parseTupParenOrDestructureGroup(tok, st, k.sm)
            if tupleType == TUPLE_OR_PAREN:
                # e.g. of form `noun ternary arg2 (arg3)`
                arg3 = tup[0]
                i += 1
            else:
                # e.g. of form `noun ternary arg2 (,,...) arg3`
                parenArgs = tok.grid[0]
                numargs = len(parenArgs)
                raise NotYetImplemented("need to get the postTernaryTok two pipeable args and merge with paren args")
        else:
            arg3 = parseSingle(tok, st, k)  # OPEN: handle post arg3 to parens
            i += 1

        return apply(node.tok1, arg3.tok2, st, f, [node, arg2, arg3]), 3


    else:
        raise NotYetImplemented()


def parseSingle(t, st, k):
    if isinstance(t, Token):
        tag = t.tag
        if tag == NAME:
            name = t.src
            meta = st.fOrVMetaForGet(name, LOCAL_SCOPE)
            if meta is Missing: raise SentenceError(f"unknown name - {name}")
            if isinstance(meta, VMeta):
                return getval(t.tok1, meta.st, name, meta.t, LOCAL_SCOPE)
            else:
                return getfamily(t.tok1, meta.st, name, LOCAL_SCOPE)
        elif tag == INTEGER:
            return lit(t.tok1, st, *k.sm.parseLitInt(t.src))
        elif tag == DECIMAL:
            return lit(t.tok1, st, *k.sm.parseLitDec(t.src))
        elif tag == TEXT:
            return lit(t.tok1, st, *k.sm.parseLitUtf8(t.src))
        else:
            missingTag = prettyNameByTag[tag]
            raise NotYetImplemented()
    else:
        return parsePhrase([t], st, k)


def parseParameters(params, fnctx, k):
    argnames = []
    tArgs = []
    for tokens in params.phrases:
        name, tp = tokens[0].nameToken.src, tokens[0].typePhrase
        if len(tp) > 0:
            t = parseTypeLang(tp, k)
        else:
            t = TBI
        fnctx.defVMeta(name, t, LOCAL_SCOPE)
        argnames.append(name)
        tArgs.append(t)
    return argnames, tArgs


def parsePhrase(tokens, st, k):
    # must not mutate sm

    if not tokens: return voidPhrase(0, 0, st)

    node = Missing

    tokens = _queue(tokens[1:] if isinstance(tokens[0], Token) and tokens[0].tag == START else tokens)

    while tokens:
        t = tokens[0]
        if isinstance(t, Token):
            tag = t.tag

            if tag == SYMBOLIC_NAME:
                name = t.src
                meta = st.fMetaForGet(name, LOCAL_SCOPE)
                if meta is Missing: raise DictionaryError(f"unknown function - {name}", ErrSite("unknown function"))
                node, numConsumed = buildFnApplication(node, meta.st, name, st, tokens, k)
                tokens >> numConsumed

            elif tag == NAME:
                name = t.src
                # for the moment check every name for dots - could (should?) be done by lexer
                names = name.split('.')
                name, otherNames = (names[0], names[1:]) if len(names) > 1 else (name, [])
                meta = st.fOrVMetaForGet(name, LOCAL_SCOPE)
                if meta is Missing:
                    raise SentenceError(f"unknown name - {name}", ErrSite("unknown name"))
                if isinstance(meta, FnMeta):
                    if otherNames:
                        raise SentenceError(f"{t.src} makes no sense as {name} is a function", ErrSite("NAME #1"))
                    node, numConsumed = buildFnApplication(node, meta.st, name, st, tokens, k)
                    tokens >> numConsumed
                elif len(tokens) > 1 and isinstance(tokens[1], TupParenOrDestructureGroup) and name in st.argCatcher.inferredArgnames:
                    if otherNames:
                        raise SentenceError(f"{t.src} makes no sense, e.g. inferredArg.a.b(...) - need to explain why in normal speak", ErrSite("NAME #2"))
                    # ambiguous - is `inferredArg (...)` an object object apply or a fun apply
                    # design decision - decide that it is the latter
                    meta = st.changeVMetaToFnMeta(name)
                    # these don't make sense:
                    # `arg1 inferredArg` unary? but inferredArg could be a symbol so an object object apply
                    # `arg1 inferredArg arg2` binary? but inferredArg could be a symbol so an object object apply
                    # potentially the following could be allowed:
                        # `arg1 inferredArg(,...)` unary with partial
                        # `arg1 inferredArg(,,...) arg2` binary with partial
                        # `arg1 inferredArg(,,,...) arg2 arg3` ternary with partial
                    # however to keep the usage of inferred arguments we'll limit inferred functions to fn(...) form
                    if node is not Missing: raise SentenceError(f"object {name}(...) not allowed", ErrSite("object name(...) not allowed"))
                    # TODO add a test to check that `{1 + f(x)}` is handled correctly (i.e. the binary + doesn't appear in node here)
                    node, numConsumed = buildFnApplication(node, meta.st, name, st, tokens, k)
                    numArgs = node.fnnode.numargs
                    f = assumedfunc(t.tok1, t.tok2, Missing, ['?'] * numArgs, BTTuple(*(TBI,) * numArgs), TBI, Missing, nullary)
                    overload = st.bindFn(name, f)    # add the function to the local symtab - the TBIs will be converted to type variables later
                    tokens >> numConsumed
                else:
                    node = getval(t, meta.st, name, LOCAL_SCOPE)
                    node.tOut = meta.t
                    tokens >> 1
                    if otherNames:
                        for name in otherNames:
                            node = getsubvalname(t, st, node, name)

            elif tag == PARENT_VALUE_NAME:
                name = t.src
                meta = st.vMetaForGet(name, PARENT_SCOPE)
                if meta is Missing: raise SentenceError(f"unknown parent value name - {name}")
                raise NotYetImplemented()

            elif tag == CONTEXT_NAME:
                name = t.src
                meta = st.fOrVMetaForGet(name, CONTEXT_NAME)
                if meta is Missing: raise SentenceError(f"unknown context name - {name}")
                raise NotYetImplemented()

            elif tag == GLOBAL_NAME:
                name = t.src
                meta = st.vMetaForGet(name, GLOBAL_SCOPE)
                if meta is Missing: raise SentenceError(f"unknown parent value name - {name}")
                raise NotYetImplemented()

            elif tag == ASSIGN_RIGHT:
                name = t.src
                # take care with st here - probably needs careful thinking through
                if isinstance(node, bfunc):
                    # meta = st.fMetaForBind(name, LOCAL_SCOPE)
                    # if meta is not Missing:
                    #     raise SentenceError(f'{name} already defined', ErrSite("name already defined"))
                    # more may need to happen here - e.g. check for style tag
                    st.defFnMeta(name, TBI, LOCAL_SCOPE)   # create a slot in the symtab for the fn
                    st.bindFn(name, node)       # add it to the overloads (it will be queued if it needs inferring)
                    currentStyle = k.styleByName.setdefault(name, node.literalstyle)
                    if node.literalstyle != currentStyle:
                        raise NotYetImplemented("Note that style has been changed")
                    node = bindfn(min(t.tok1, node.tok1), max(t.tok2, node.tok2), st, name, node, LOCAL_SCOPE)
                    tokens >> 1
                else:
                    # meta = st.vMetaForBind(name, LOCAL_SCOPE)
                    # if meta is not Missing:
                    #     raise SentenceError(f'{name} already defined', ErrSite("name already defined"))
                    st.defVMeta(name, TBI, LOCAL_SCOPE)
                    #HACK
                    node = node[0] if isinstance(node, list) else node
                    node = bindval(t.tok1, t.tok2, st, name, node, LOCAL_SCOPE)
                    tokens >> 1

            elif tag == CONTEXT_ASSIGN_RIGHT:
                name = t.src
                meta = st.fOrVMetaForBind(name, CONTEXT_SCOPE)
                raise NotYetImplemented()

            elif tag == GLOBAL_ASSIGN_RIGHT:
                name = t.src
                meta = st.vMetaForBind(name, GLOBAL_SCOPE)
                if meta is not Missing:
                    raise SentenceError(f'{name} already defined', ErrSite("name already defined"))
                else:
                    st.defVMeta(name, TBI, GLOBAL_SCOPE)
                    node = bindval(st, name, node, GLOBAL_SCOPE)
                    tokens >> 1

            elif tag == INTEGER:
                node = lit(t.tok1, st, *k.sm.parseLitInt(t.src))
                tokens >> 1

            elif tag == DECIMAL:
                node = lit(t.tok1, st, *k.sm.parseLitDec(t.src))
                tokens >> 1

            elif tag == TEXT:
                node = lit(t.tok1, st, *k.sm.parseLitUtf8(t.src))
                tokens >> 1

            elif tag == SYM:
                node = lit(t.tok1, st, *k.sm.parseLitSym(t.src))
                tokens >> 1

            elif tag == SYMS:
                node = lit(t.tok1, st, *k.sm.parseLitSyms(t.src))
                tokens >> 1

            elif tag == DATE:
                node = lit(t.tok1, st, *k.sm.parseLitDate(t.src))
                tokens >> 1

            elif tag in (
                    GLOBALTIMESTAMP_SS, GLOBALTIMESTAMP_S, GLOBALTIMESTAMP_M, LOCALTIMESTAMP_SS, LOCALTIMESTAMP_S,
                    LOCALTIMESTAMP_M, GLOBALTIME_SS, GLOBALTIME_S, GLOBALTIME_M, LOCALTIME_SS, LOCALTIME_S, LOCALTIME_M
            ):
                raise NotYetImplemented()

            elif tag == ASSIGN_LEFT:
                k.dumpLines(t.srcId, t.l1-3, t.l2)
                raise ProgrammerError("Looks like the grouping hasn't worked proprerly", ErrSite("Encountered ASSIGN_LEFT"))

            elif tag == NULL:
                return voidPhrase(t.tok1, t.tok2, st)

            else:
                raise ProgrammerError()

        else:

            if isinstance(t, FuncOrStructGroup):
                if t._unaryBinaryOrStruct == STRUCT:
                    # create the litstruct and the struct type
                    vs, names, ts = [], [], []
                    for v, nameToken in t.phrases:
                        names.append(k.sm.parseLitSym(nameToken.src)[1])
                        node = parsePhrase([v], st, k)
                        vs.append(node)
                        ts.append(node.tOut)
                    tStruct = BTStruct(names, ts) & bones.lang.types.litstruct
                    # tvObj = tv(tStruct, dict(zip(names, vs)))
                    raise NotYetImplemented('how do we get the struct type from the dm library?')
                    tokens >> 1
                    node = litstruct(t.tok1, t.tok2, st, tvObj)
                elif t._unaryBinaryOrStruct == UNARY_OR_STRUCT:
                    raise NotYetImplemented()
                else:
                    # OPRN: create the fnSymTab in the grouping stage and add explicit parameters and assigned variables there
                    # implicit args need to be done here
                    fnSt = fnSymTab(st)
                    if t._params is Missing:
                        fnSt.argCatcher = ArgCatcher([])
                    else:
                        argnames, tArgs = parseParameters(t._params, fnSt, k.sm)
                    tRet = TBI if t._tRet is Missing else parseTypeLang(t._tRet, k)
                    body = [parsePhrase(phrase, fnSt, k) for phrase in t.phrases]
                    if t._params is Missing:
                        argnames = fnSt.argCatcher.inferredArgnames
                        argnames.sort(key=_inDictionaryOrder)
                        tArgs = [TBI] * len(argnames)
                    if t._unaryBinaryOrStruct == UNARY: style = unary
                    elif t._unaryBinaryOrStruct == BINARY: style = binary
                    else: raise ProgrammerError()
                    fnSt.defVMeta(RET_VAR_NAME, TBI, LOCAL_SCOPE)
                    f = bfunc(t.tok1, t.tok1, fnSt, argnames, BTTuple(*tArgs), tRet, body, style)
                    tokens[0] = f
                    # OPEN: handle style conversion and assignment (as we're not always calling a function)
                    node, numConsumed = buildFnApplication(node, Missing, f, st, tokens, k.sm)
                    tokens >> numConsumed

            elif isinstance(t, TupParenOrDestructureGroup):
                if t.tupleType == TUPLE_OR_PAREN:
                    if node is Missing:
                        # of form `(a)` - is it a tuple of one element or a parenthesis?
                        # for the moment we will assume a parenthesis -> 1 entup to make a one tuple? like q
                        tupleType, tup = parseTupParenOrDestructureGroup(t, st, k)
                        node = tup
                        tokens >> 1
                    else:
                        # two possible intentions
                        #   1) object paren, intended as an object object apply OR
                        #   2) fn paren
                        # three cases -
                        #   1) node is a function (but that is handled in the NAME case)
                        #   2) node is a value - known from the name space
                        #   3) node is TBI - i.e. a parameter
                        # OPEN: could set this up to be handled in inference or even later but for now assume the TBI is a function

                        # create a fn with generic tArgs and tRet
                        name = node.name
                        if st.argCatcher and name in st.argCatcher.inferredArgnames:
                            st.changeVMetaToFnMeta(name)
                        tupleType, tup = parseTupParenOrDestructureGroup(t, st, k)
                        numArgs = 1
                        fnode = getoverload(t.tok1, st, name, numArgs, LOCAL_SCOPE)      # OPEN handle partials
                        f = bfunc(t.tok1, t.tok2, Missing, ['?'] * numArgs, BTTuple(*(TBI,)*numArgs), TBI, Missing, unary)
                        overload = st.bindFn(name, f)
                        node = apply(t.tok1, t.tok2, st, fnode, tup)
                        tokens >> 1
                else:
                    raise ProgrammerError("all other cases should be captured in buildFnApplication")

            elif isinstance(t, BlockGroup):
                blockSt = blockSymTab(st)
                if t._params is Missing:
                    argnames, tArgs = [], []
                else:
                    argnames, tArgs = parseParameters(t._params, blockSt, k.sm)
                tRet = TBI if t._tRet is Missing else parseTypeLang(t._tRet, k)
                body = [parsePhrase(phrase, blockSt, k) for phrase in t.phrases]
                blockSt.defVMeta(RET_VAR_NAME, TBI, LOCAL_SCOPE)
                node = block(t.tok1, t.tok1, blockSt, argnames, BTTuple(*tArgs), tRet, body)
                tokens[0] = node
                tokens >> 1

            elif isinstance(t, FrameGroup):
                raise NotYetImplemented()

            elif isinstance(t, LoadGroup):
                # i.e. searches PYTHON_PATH and BONES_PATH for bones/ex/ and load core.py or core.b
                paths = []
                for phrase in t.phrases:
                    for tok in phrase:
                        paths.append(tok.src)
                node = load(t.tok1, t.tok2, st, paths)
                k.loadModules(node.paths)
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
                        elif tok.tag == ELLIPSES:
                            name += tok.src
                        else:
                            raise NotYetImplemented(f'tok: {tok}')
                    names.append(name)
                node = fromimport(t.tok1, t.tok2, st, t.path, names)
                k.importSymbols(node.path, node.names, node.st)
                tokens >> 1

            elif isinstance(t, TypeLangGroup):
                raise NotYetImplemented()

            else:
                raise ProgrammerError()

    return node


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
