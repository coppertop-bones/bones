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
from bones.kernel.core import RET_VAR_NAME
from bones.parse.lex import Token, prettyNameByTag, \
    START, NULL, INTEGER, DECIMAL, SYM, SYMS, TEXT, \
    DATE, LOCALTIME_M, LOCALTIME_S, LOCALTIME_SS, \
    GLOBALTIME_M, GLOBALTIME_SS, GLOBALTIME_S, \
    GLOBALTIMESTAMP_M, GLOBALTIMESTAMP_S, GLOBALTIMESTAMP_SS, \
    LOCALTIMESTAMP_SS, LOCALTIMESTAMP_S, LOCALTIMESTAMP_M, \
    NAME, SYMBOLIC_NAME, ASSIGN_RIGHT, ASSIGN_LEFT, \
    PARENT_VALUE_NAME, \
    CONTEXT_NAME, CONTEXT_ASSIGN_RIGHT, \
    GLOBAL_NAME, GLOBAL_ASSIGN_RIGHT, KEYWORD_OR_ASSIGN_LEFT, SYMBOLIC_NAME, ELLIPSES
from bones.parse.parse_groups import \
    LoadGp, FromImportGp, \
    FuncOrStructGp, TupParenOrDestructureGp, BlockGp, \
    TypelangGp, \
    FrameGp, _SemiColonSepCommaSepDotSepGL, SemiColonSepCommaSep, _DotOrCommaSepGL, _CommaSepDotSepGL
from bones.kernel.symbol_table import VMeta, FnMeta, fnSymTab, ArgCatcher, blockSymTab
from bones.kernel.tc import tclit, tcvoidphrase, tcbindval, tcgetval, tcgetoverload, tcsnippet, tcapply, tcfunc, tcload, tcfromimport, \
    tcbindfn, tcgetfamily, tcassumedfunc, tclitstruct, tclittup, tclitframe, tcblock, tclitbtype
from bones.ts.metatypes import BTTuple, BTStruct
from bones.kernel.core import LOCAL_SCOPE, PARENT_SCOPE, CONTEXT_SCOPE, GLOBAL_SCOPE
from bones.lang.types import TBI, littup
from bones.parse.parse_groups import DESTRUCTURE, TUPLE_NULL, TUPLE_2D, TUPLE_OR_PAREN, TUPLE_0_EMPTY, STRUCT, \
    TUPLE_1_EMPTY, TUPLE_2_EMPTY, TUPLE_3_EMPTY, TUPLE_4_PLUS_EMPTY, UNARY, BINARY, UNARY_OR_STRUCT
from bones.ts.type_lang import TypeLangInterpreter
from bones.ts.metatypes import BType


def parseSnippet(snippetGroup, symtab, k):
    # must not mutate sm
    tcs = [parsePhrase(phrase, symtab, k) for phrase in snippetGroup.phrases]
    return tcsnippet(snippetGroup.tok1, snippetGroup.tok2, symtab, tcs)


def parseTupParenOrDestructureGroup(group, symtab, k):
    tt = group.tupleType
    if tt == TUPLE_NULL:
        raise NotYetImplemented()
    elif tt == TUPLE_2D:
        raise NotYetImplemented()
    elif tt == TUPLE_OR_PAREN:
        # of form `(a)`, i.e. no semi-colons and no commas - so just the one phrase and it's in the same symtab
        # OPEN: possibly we might like to have multiple phrases in parentheses   x * (fred: 1 + 1. joe: fred * 2. joe+fred)
        # OPEN: how to specify a 1d or 2d single element tuple? Maybe Python style with a comma or ; however that
        #   sort of precludes Missing elements in a tuple
        phrase = group.grid[0][0]
        tc = parsePhrase(phrase, symtab, k)
        return [tc]
    elif tt == TUPLE_0_EMPTY:
        if isinstance(group.grid, _SemiColonSepCommaSepDotSepGL):
            commaSepDotSepPhrase = group.grid[0]
            commaSepDotSepTc = _CommaSepDotSepGL()
            for dotSepPhrase in commaSepDotSepPhrase:
                dotSepTc = _DotOrCommaSepGL('.')
                for phrase in dotSepPhrase:
                    tc = parsePhrase(phrase, symtab, k)
                    dotSepTc << tc
                commaSepDotSepTc << dotSepTc
            return commaSepDotSepTc
        elif isinstance(group.grid, SemiColonSepCommaSep):
            commaSepPhrase = group.grid[0]
            dotSepTc = _DotOrCommaSepGL(',')
            for phrase in commaSepPhrase:
                tc = parsePhrase(phrase, symtab, k)
                dotSepTc << tc
            return dotSepTc
        else:
            raise ProgrammerError()
    elif tt == TUPLE_1_EMPTY:
        if isinstance(group.grid, SemiColonSepCommaSep):
            commaSepPhrase = group.grid[0]
            commaSepTc = _DotOrCommaSepGL(',')
            for phrase in commaSepPhrase:
                tc = parsePhrase(phrase, symtab, k)
                commaSepTc << tc
            return commaSepTc
        else:
            raise ProgrammerError()
    elif tt == TUPLE_2_EMPTY:
        raise NotYetImplemented()
    elif tt == TUPLE_3_EMPTY:
        raise NotYetImplemented()
    elif tt == TUPLE_4_PLUS_EMPTY:
        raise NotYetImplemented()
    elif tt == DESTRUCTURE:
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


def buildFnApplication(tcnode, ctxWithFn, fOrName, symtab, tokens, k):
    if isinstance(fOrName, tcfunc):
        style = fOrName.literalstyle
    else:
        style = symtab.styleOfName(fOrName)

    if tcnode is Missing:
        # possibilities
        # fn ()                     (fn may have more than one tuple afterward)
        if len(tokens) == 1:
            if isinstance(fOrName, tcfunc):
                return fOrName, 1
            else:
                f = parseSingle(tokens[0], symtab, k)
                return f, 1
        elif len(tokens) > 1:
            next = tokens[1]
            if isinstance(next, TupParenOrDestructureGp):
                # e.g. fred(...)
                tup = parseTupParenOrDestructureGroup(next, symtab, k)
                tupleType = next.tupleType
                if tupleType == TUPLE_OR_PAREN:
                    # fn (a)        i.e. passing a into fn
                    rhs = tup
                    if ctxWithFn is Missing:
                        f = fOrName
                    else:
                        f = tcgetoverload(tokens[0].tok1, ctxWithFn, fOrName, 1, LOCAL_SCOPE)      # OPEN handle partials
                    return tcapply(tokens[0].tok1, next.tok2, symtab, f, rhs), 2
                elif tupleType == TUPLE_0_EMPTY:
                    # fn(a,b,c)
                    if isinstance(tup, _SemiColonSepCommaSepDotSepGL):
                        rhs = [snippetOrTc(e) for e in tup]
                    elif isinstance(tup, SemiColonSepCommaSep):
                        rhs = [snippetOrTc(e) for e in tup]
                    elif isinstance(tup, _DotOrCommaSepGL):
                        rhs = [snippetOrTc(e) for e in tup]
                    elif isinstance(tup, _CommaSepDotSepGL):
                        rhs = [snippetOrTc(e[0]) for e in tup]
                    else:
                        raise ProgrammerError()
                    numargs = len(rhs)
                    if ctxWithFn is Missing:
                        f = fOrName
                    else:
                        f = tcgetoverload(tokens[0].tok1, ctxWithFn, fOrName, numargs, LOCAL_SCOPE)      # OPEN handle partials
                    return tcapply(tokens[0].tok1, next.tok2, symtab, f, rhs), 2
                else:
                    raise ProgrammerError()
            elif isinstance(next, Token):
                if next.tag == ASSIGN_RIGHT:
                    # OPEN: handle {a+1} :f (1)   which should answer tcapply(tcbindfn('f', deffn(...)),1) but may impact elsewhere
                    # handled in main parse loop so just put the function in the tcnode and consume 1 token
                    if ctxWithFn is Missing:
                        f = fOrName
                    else:
                        raise NotYetImplemented("need to copy every overload into the local symtab")
                    return f, 1
                else:
                    f = tcgetfamily(tokens[0].tok1, ctxWithFn, fOrName, LOCAL_SCOPE)
                    return f, 1             # fn is probably being called as an argument
            else:
                raise NotYetImplemented()
        else:
            raise ProgrammerError()


    elif style is unary:
        # noun unary            (unary may have tuples afterward)
        if len(tokens) > 1 and isinstance(postUnaryTok := tokens[1], TupParenOrDestructureGp):
            tup = parseTupParenOrDestructureGroup(postUnaryTok, symtab, k.sm)
            tupleType = postUnaryTok.tupleType
            if tupleType == TUPLE_OR_PAREN:
                # noun unary (...)
                raise NotYetImplemented("need to get the next one pipeable arg and merge with paren args")
            elif tupleType == TUPLE_1_EMPTY:
                # noun unary(,args)
                rhs = postUnaryTok.tok2
                f = fOrName if ctxWithFn is Missing else tcgetoverload(tokens[0].tok1, ctxWithFn, fOrName, len(tup), LOCAL_SCOPE)
                for i in range(len(tup)):
                    if isinstance(tup[i], tcvoidphrase):
                        tup[i] = tcnode
                        break
                return tcapply(tcnode.tok1, rhs, symtab, f, tup), 2
            else:
                raise SentenceError("error needs describing properly")
        else:
            # noun unary
            rhs = tokens[0].tok2
            f = fOrName if ctxWithFn is Missing else tcgetoverload(tokens[0].tok1, ctxWithFn, fOrName, 1, LOCAL_SCOPE)
        return tcapply(tcnode.tok1, tokens[0], symtab, f, [tcnode]), 1


    elif style is binary:
        # noun binary arg2          (binary and arg2 may have tuples afterward)
        if len(tokens) < 2: raise SentenceError("incomplete phrase - {noun, binary} is missing args after the binary")
        postBinaryTok = tokens[1]
        if isinstance(postBinaryTok, TupParenOrDestructureGp):
            tup = parseTupParenOrDestructureGroup(postBinaryTok, symtab, k.sm)
            tupleType = postBinaryTok.tupleType
            if tupleType == TUPLE_OR_PAREN:
                # noun binary (arg2)
                arg2 = tup[0]
                rhs = postBinaryTok.tok2
                f = fOrName if ctxWithFn is Missing else tcgetoverload(tokens[0].tok1, ctxWithFn, fOrName, 2, LOCAL_SCOPE)
            else:
                # e.g. noun binary (,,args) arg2`
                parenArgs = postBinaryTok.grid[0]
                rhs = postBinaryTok.tok2
                f = fOrName if ctxWithFn is Missing else tcgetoverload(tokens[0].tok1, ctxWithFn, fOrName, len(parenArgs), LOCAL_SCOPE)
                # OPEN: handle arg2(...)
                raise NotYetImplemented("need to get the next one pipeable arg and merge with paren args")
        else:
            arg2 = parseSingle(postBinaryTok, symtab, k)
            rhs = arg2.tok2
            f = fOrName if ctxWithFn is Missing else tcgetoverload(tokens[0].tok1, ctxWithFn, fOrName, 2, LOCAL_SCOPE)      # OPEN handle partials

        return tcapply(tcnode.tok1, rhs, symtab, f, [tcnode, arg2]), 2


    elif style is ternary:
        # noun ternary arg2 arg3    (ternary, arg2 and arg3 may have parens afterward)
        if len(tokens) < 3: raise SentenceError(f"incomplete phrase - {{noun, ternary{', arg2' if len(tokens) == 2 else ''}}} is missing args after the ternary")

        i = 1

        # handle token after ternary
        tok = tokens[i]
        if isinstance(tok, TupParenOrDestructureGp):
            tup = parseTupParenOrDestructureGroup(tok, symtab, k.sm)
            tupleType = tok.tupleType
            if tupleType == TUPLE_OR_PAREN:
                # e.g. of form `noun ternary (arg2) arg3`
                arg2 = tup[0]
                f = fOrName if ctxWithFn is Missing else tcgetoverload(tokens[0].tok1, ctxWithFn, fOrName, 3, LOCAL_SCOPE)  # OPEN handle partials
                i += 1
            else:
                # e.g. of form `noun ternary (,,...) arg2 arg3`
                parenArgs = tok.grid[0]
                f = fOrName if ctxWithFn is Missing else tcgetoverload(tokens[0].tok1, ctxWithFn, fOrName, len(parenArgs), LOCAL_SCOPE)  # OPEN handle partials
                raise NotYetImplemented("need to get the postTernaryTok two pipeable args and merge with paren args")
        else:
            arg2 = parseSingle(tok, symtab, k)  # OPEN: handle post arg2 to parens
            f = fOrName if ctxWithFn is Missing else tcgetoverload(tokens[0].tok1, ctxWithFn, fOrName, 3, LOCAL_SCOPE)  # OPEN handle partials
            i += 1

        # handle token after arg2
        tok = tokens[i]
        if isinstance(tok, TupParenOrDestructureGp):
            tup = parseTupParenOrDestructureGroup(tok, symtab, k.sm)
            tupleType = tok.tupleType
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
            arg3 = parseSingle(tok, symtab, k)  # OPEN: handle post arg3 to parens
            i += 1

        return tcapply(tcnode.tok1, arg3.tok2, symtab, f, [tcnode, arg2, arg3]), 3


    else:
        raise NotYetImplemented()


def parseSingle(t, symtab, k):
    if isinstance(t, Token):
        tag = t.tag
        if tag == NAME:
            nameAndAccessors = t.src.split('.')
            name, accessors = nameAndAccessors[0], nameAndAccessors[1:]
            meta = symtab.fOrVMetaForGet(name, LOCAL_SCOPE)
            if meta is Missing: raise SentenceError(f'unknown name - {name}')
            if isinstance(meta, VMeta):
                return tcgetval(t.tok1, meta.symtab, LOCAL_SCOPE, name, accessors).setTOut(meta.t)
            else:
                return tcgetfamily(t.tok1, meta.symtab, name, LOCAL_SCOPE)
        elif tag == INTEGER:
            return tclit(t.tok1, symtab, k.sm.parseLitInt(t.src))
        elif tag == DECIMAL:
            return tclit(t.tok1, symtab, k.sm.parseLitNum(t.src))
        elif tag == TEXT:
            return tclit(t.tok1, symtab, k.sm.parseLitUtf8(t.src))
        else:
            missingTag = prettyNameByTag[tag]
            raise NotYetImplemented()
    else:
        return parsePhrase([t], symtab, k)


def parseParameters(params, fnctx, k):
    argnames = []
    tArgs = []
    for tokens in params.phrases:
        name, tp = tokens[0].nameToken.src, tokens[0].typePhrase
        if len(tp) == 0:
            t = TBI
        elif len(tp) == 1:
            src = tp[0].src
            t = BType(src)
        else:
            raise NotYetImplemented()
        fnctx.defVMeta(name, t, LOCAL_SCOPE)
        argnames.append(name)
        tArgs.append(t)
    return argnames, tArgs


def parsePhrase(tokens, symtab, k):
    # must not mutate sm

    if not tokens: return tcvoidphrase(0, 0, symtab)

    tcnode = Missing

    tokens = _queue(tokens[1:] if isinstance(tokens[0], Token) and tokens[0].tag == START else tokens)

    while tokens:
        t = tokens[0]
        if isinstance(t, Token):
            tag = t.tag

            if tag == SYMBOLIC_NAME:
                name = t.src
                meta = symtab.fMetaForGet(name, LOCAL_SCOPE)
                if meta is Missing: raise DictionaryError(f"unknown function - {name}", ErrSite("unknown function"))
                tcnode, numConsumed = buildFnApplication(tcnode, meta.symtab, name, symtab, tokens, k)
                tokens >> numConsumed

            elif tag == NAME:
                name = t.src
                # for the moment check every name for dots - could (should?) be done by lexer
                names = name.split('.')
                name, accessors = (names[0], names[1:]) if len(names) > 1 else (name, [])
                meta = symtab.fOrVMetaForGet(name, LOCAL_SCOPE)
                if meta is Missing:
                    raise SentenceError(f"unknown name - {name}", ErrSite("unknown name"))
                if isinstance(meta, FnMeta):
                    if accessors:
                        raise SentenceError(f"{t.src} makes no sense as {name} is a function", ErrSite("NAME #1"))
                    tcnode, numConsumed = buildFnApplication(tcnode, meta.symtab, name, symtab, tokens, k)
                    tokens >> numConsumed
                elif len(tokens) > 1 and isinstance(tokens[1], TupParenOrDestructureGp) and name in symtab.argCatcher.inferredArgnames:
                    if accessors:
                        raise SentenceError(f"{t.src} makes no sense, e.g. inferredArg.a.b(...) - need to explain why in normal speak", ErrSite("NAME #2"))
                    # ambiguous - is `inferredArg (...)` an object object apply or a fun apply
                    # design decision - decide that it is the latter
                    meta = symtab.changeVMetaToFnMeta(name)
                    # these don't make sense:
                    # `arg1 inferredArg` unary? but inferredArg could be a symbol so an object object apply
                    # `arg1 inferredArg arg2` binary? but inferredArg could be a symbol so an object object apply
                    # potentially the following could be allowed:
                        # `arg1 inferredArg(,...)` unary with partial
                        # `arg1 inferredArg(,,...) arg2` binary with partial
                        # `arg1 inferredArg(,,,...) arg2 arg3` ternary with partial
                    # however to keep the usage of inferred arguments we'll limit inferred functions to fn(...) form
                    if tcnode is not Missing: raise SentenceError(f"object {name}(...) not allowed", ErrSite("object name(...) not allowed"))
                    # TODO add a test to check that `{1 + f(x)}` is handled correctly (i.e. the binary + doesn't appear in tcnode here)
                    tcnode, numConsumed = buildFnApplication(tcnode, meta.symtab, name, symtab, tokens, k)
                    numArgs = tcnode.fnnode.numargs
                    f = tcassumedfunc(t.tok1, t.tok2, Missing, ['?'] * numArgs, BTTuple(*(TBI,) * numArgs), TBI, Missing, nullary)
                    overload = symtab.bindFn(name, f)    # add the function to the local symtab - the TBIs will be converted to type variables later
                    tokens >> numConsumed
                else:
                    tcnode = tcgetval(t, meta.symtab, LOCAL_SCOPE, name, accessors).setTOut(meta.t)
                    tokens >> 1

            elif tag == PARENT_VALUE_NAME:
                name = t.src
                meta = symtab.vMetaForGet(name, PARENT_SCOPE)
                if meta is Missing: raise SentenceError(f"unknown parent value name - {name}")
                raise NotYetImplemented()

            elif tag == CONTEXT_NAME:
                name = t.src
                meta = symtab.fOrVMetaForGet(name, CONTEXT_NAME)
                if meta is Missing: raise SentenceError(f"unknown context name - {name}")
                raise NotYetImplemented()

            elif tag == GLOBAL_NAME:
                name = t.src
                meta = symtab.vMetaForGet(name, GLOBAL_SCOPE)
                if meta is Missing: raise SentenceError(f"unknown parent value name - {name}")
                raise NotYetImplemented()

            elif tag == ASSIGN_RIGHT:
                name = t.src
                # take care with symtab here - probably needs careful thinking through
                if isinstance(tcnode, tcfunc):
                    # meta = symtab.fMetaForBind(name, LOCAL_SCOPE)
                    # if meta is not Missing:
                    #     raise SentenceError(f'{name} already defined', ErrSite("name already defined"))
                    # more may need to happen here - e.g. check for style tag
                    symtab.defFnMeta(name, tcfunc.tRet, LOCAL_SCOPE)   # create a slot in the symtab for the fn
                    symtab.bindFn(name, tcnode)       # add it to the overloads (it will be queued if it needs inferring)
                    currentStyle = k.styleByName.setdefault(name, tcnode.literalstyle)
                    if tcnode.literalstyle != currentStyle:
                        raise NotYetImplemented("Note that style has been changed")
                    tcnode = tcbindfn(min(t.tok1, tcnode.tok1), max(t.tok2, tcnode.tok2), symtab, name, tcnode, LOCAL_SCOPE)
                    tokens >> 1
                else:
                    # meta = symtab.vMetaForBind(name, LOCAL_SCOPE)
                    # if meta is not Missing:
                    #     raise SentenceError(f'{name} already defined', ErrSite("name already defined"))
                    symtab.defVMeta(name, TBI, LOCAL_SCOPE)
                    #HACK
                    tcnode = tcnode[0] if isinstance(tcnode, list) else tcnode
                    accessors = []
                    tcnode = tcbindval(t.tok1, t.tok2, symtab, tcnode, LOCAL_SCOPE, name, accessors)
                    tokens >> 1

            elif tag == CONTEXT_ASSIGN_RIGHT:
                name = t.src
                meta = symtab.fOrVMetaForBind(name, CONTEXT_SCOPE)
                raise NotYetImplemented()

            elif tag == GLOBAL_ASSIGN_RIGHT:
                name = t.src
                meta = symtab.vMetaForBind(name, GLOBAL_SCOPE)
                if meta is not Missing:
                    raise SentenceError(f'{name} already defined', ErrSite("name already defined"))
                else:
                    symtab.defVMeta(name, TBI, GLOBAL_SCOPE)
                    accessors = []
                    tcnode = tcbindval(t.tok1, t.tok2, symtab, tcnode, GLOBAL_SCOPE, name, accessors)
                    tokens >> 1

            elif tag == INTEGER:
                tcnode = tclit(t.tok1, symtab, k.sm.parseLitInt(t.src))
                tokens >> 1

            elif tag == DECIMAL:
                tcnode = tclit(t.tok1, symtab, k.sm.parseLitNum(t.src))
                tokens >> 1

            elif tag == TEXT:
                tcnode = tclit(t.tok1, symtab, k.sm.parseLitUtf8(t.src))
                tokens >> 1

            elif tag == SYM:
                tcnode = tclit(t.tok1, symtab, k.litsymCons(k.sm.parseSym(t.src)))
                tokens >> 1

            elif tag == SYMS:
                tcnode = tclit(t.tok1, symtab, k.sm.parseLitSyms(t.src))
                tokens >> 1

            elif tag == DATE:
                tcnode = tclit(t.tok1, symtab, k.sm.parseLitDate(t.src))
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
                return tcvoidphrase(t.tok1, t.tok2, symtab)

            else:
                raise ProgrammerError()

        else:

            if isinstance(t, FuncOrStructGp):
                if t._unaryBinaryOrStruct == STRUCT:
                    # create the tclitstruct and the struct type
                    vs, names, ts = [], [], []
                    for phrase in t.phrases:
                        v, nameToken = phrase[:-1], phrase[-1]
                        names.append(k.sm.parseSym(nameToken.src))
                        tcnode = parsePhrase(v, symtab, k)
                        vs.append(tcnode)
                        ts.append(tcnode.tOut)
                    tStruct = BTStruct(names, ts) & bones.lang.types.litstruct
                    tvstruct = k.litstructCons(tStruct, dict(zip(names, vs)))
                    tokens >> 1
                    tcnode = tclitstruct(t.tok1, t.tok2, symtab, tvstruct)
                elif t._unaryBinaryOrStruct == UNARY_OR_STRUCT:
                    raise NotYetImplemented()
                else:
                    # OPRN: create the fnSymTab in the grouping stage and add explicit parameters and assigned variables there
                    # implicit args need to be done here
                    fnSt = fnSymTab(symtab)
                    if t._params is Missing:
                        fnSt.argCatcher = ArgCatcher([])
                    else:
                        argnames, tArgs = parseParameters(t._params, fnSt, k.sm)
                    # {[] <:tRet> x + y...
                    tRet = TBI if t._tRet is Missing else BType(t._tRet.tl)
                    body = [parsePhrase(phrase, fnSt, k) for phrase in t.phrases]
                    if t._params is Missing:
                        argnames = fnSt.argCatcher.inferredArgnames
                        argnames.sort(key=_inDictionaryOrder)
                        tArgs = [TBI] * len(argnames)
                    if t._unaryBinaryOrStruct == UNARY: style = unary
                    elif t._unaryBinaryOrStruct == BINARY: style = binary
                    else: raise ProgrammerError()
                    fnSt.defVMeta(RET_VAR_NAME, TBI, LOCAL_SCOPE)
                    f = tcfunc(t.tok1, t.tok1, fnSt, argnames, BTTuple(*tArgs), tRet, body, style)
                    # tokens[0] = f
                    # OPEN: handle style conversion and assignment (as we're not always calling a function)
                    tcnode, numConsumed = buildFnApplication(tcnode, Missing, f, symtab, tokens[0:], k.sm)
                    tokens >> numConsumed

            elif isinstance(t, TupParenOrDestructureGp):
                if tcnode is Missing:
                    if t.tupleType == DESTRUCTURE:
                        raise NotYetImplemented('TupParenOrDestructureGp.tupleType == DESTRUCTURE')
                    if t.tupleType == TUPLE_OR_PAREN:
                        # if TUPLE_OR_PAREN then of form `(a)` - is it a tuple of one element or a parenthesis?
                        # for the moment we will assume a parenthesis -> 1 entup to make a one tuple? like q
                        pass
                    if t.tupleType == TUPLE_2D:
                        raise NotYetImplemented('TupParenOrDestructureGp.tupleType == TUPLE_2D')
                    else:
                        vs, ts = [], []
                        innertcnodes = parseTupParenOrDestructureGroup(t, symtab, k)
                        for innertcnode in innertcnodes:
                            vs.append(innertcnode)
                            ts.append(innertcnode.tOut)
                        tTup = BTTuple(*ts) & bones.lang.types.littup
                        tup = k.littupCons(tTup, vs)
                        tcnode = tclittup(t.tok1, t.tok2, symtab, tup)
                        tokens >> 1
                else:
                    if t.tupleType == TUPLE_OR_PAREN:
                        # two possible intentions
                        #   1) object paren, intended as an object object apply OR
                        #   2) fn paren
                        # three cases -
                        #   1) tcnode is a function (but that is handled in the NAME case)
                        #   2) tcnode is a value - known from the name space
                        #   3) tcnode is TBI - i.e. a parameter
                        # OPEN: could set this up to be handled in inference or even later but for now assume the TBI is a function

                        # create a fn with generic tArgs and tRet
                        name = tcnode.name
                        if symtab.argCatcher and name in symtab.argCatcher.inferredArgnames:
                            symtab.changeVMetaToFnMeta(name)
                        tup = parseTupParenOrDestructureGroup(t, symtab, k)
                        numArgs = 1
                        fnode = tcgetoverload(t.tok1, symtab, name, numArgs, LOCAL_SCOPE)      # OPEN handle partials
                        f = tcfunc(t.tok1, t.tok2, Missing, ['?'] * numArgs, BTTuple(*(TBI,)*numArgs), TBI, Missing, unary)
                        overload = symtab.bindFn(name, f)
                        tcnode = tcapply(t.tok1, t.tok2, symtab, fnode, tup)
                        tokens >> 1
                    else:
                        raise ProgrammerError()

            elif isinstance(t, BlockGp):
                blockSt = blockSymTab(symtab)
                if t._params is Missing:
                    argnames, tArgs = [], []
                else:
                    argnames, tArgs = parseParameters(t._params, blockSt, k.sm)
                tRet = TBI if t._tRet is Missing else parseTypeLang(t._tRet, k)
                body = [parsePhrase(phrase, blockSt, k) for phrase in t.phrases]
                blockSt.defVMeta(RET_VAR_NAME, TBI, LOCAL_SCOPE)
                tcnode = tcblock(t.tok1, t.tok1, blockSt, argnames, BTTuple(*tArgs), tRet, body)
                tokens[0] = tcnode
                tokens >> 1

            elif isinstance(t, FrameGp):
                raise NotYetImplemented()

            elif isinstance(t, LoadGp):
                # i.e. searches PYTHON_PATH and BONES_PATH for bones/ex/ and load core.py or core.b
                paths = []
                for phrase in t.phrases:
                    for tok in phrase:
                        paths.append(tok.src)
                tcnode = tcload(t.tok1, t.tok2, symtab, paths)
                k.loadModules(tcnode.paths)
                tokens >> 1

            elif isinstance(t, FromImportGp):
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
                tcnode = tcfromimport(t.tok1, t.tok2, symtab, t.path, names)
                k.importSymbols(tcnode.path, tcnode.names, tcnode.symtab)
                tokens >> 1

            elif isinstance(t, TypelangGp):
                tcnode = tclitbtype(t.tok1, t.tok2, symtab, BType(t.tl))
                tokens >> 1

            else:
                raise ProgrammerError()

    return tcnode


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

