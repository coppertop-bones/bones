# **********************************************************************************************************************
# Copyright 2025 David Briant, https://github.com/coppertop-bones. Licensed under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance with the License. You may obtain a copy of the  License at
# http://www.apache.org/licenses/LICENSE-2.0. Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY  KIND,
# either express or implied. See the License for the specific language governing permissions and limitations under the
# License. See the NOTICE file distributed with this work for additional information regarding copyright ownership.
# **********************************************************************************************************************

import itertools, sys, collections

from bones import jones

from coppertop.core import context, NotYetImplemented, ProgrammerError, Missing, Void

from coppertop.core import handlersByErrSiteId, ErrSite
from bones.kernel.errors import BonesIncompatibleTypesError, BonesModuleImportError
from bones.kernel import lex
from bones.kernel import parse_phrase, parse_groups
from coppertop.dm.pp import PP
from bones.kernel._core import LOCAL_SCOPE, SCRATCH_CTX, GLOBAL_CTX
from bones.lang.types import unary, litnum, litint, litsyms, littxt
from bones.kernel.sym_manager import SymManager
from bones.kernel.symbol_table import GlobalSymTab, ModSymTab
from bones.kernel.stack_manager import StackManager, bframe
from bones.kernel.globals_manager import GlobalsManager
from bones.kernel.code_manager import CodeManager
from bones.kernel.contextual_scope_manager import ContextualScopeManager
from bones.kernel.tc import tcfromimport, tcbindval, tcapply, tcgetval, tcfunc, tclit, tcbindfn, tcgetfamily, \
    tcgetoverload, tclitstruct, tclittup, tclitbtype, tcblock, TcReport
from bones.kernel._core import MODULE_SCOPE
from bones.ts.metatypes import BTTuple, updateSchemaVarsWith, fitsWithin, BType, BTypeError
from bones.ts.select import _typeOf, tvoverload, tvfunc, tvfamily


pace_res = collections.namedtuple('pace_res', 'tokens, types, result, error')


class BonesKernel:

    __slots__ = [
        'stackManager', 'globalsManager', 'codeManager', 'contextualScopeManager', 'symbolManager',
        'ctxs', 'modByPath', 'styleByName', 'srcById', 'linesById', 'nextSrcId', 'infercache',
        'scratch', 'litdateCons', 'litsymCons', 'littupCons', 'litstructCons', 'litframeCons',
        '_holderByModPathByName', '_frameBySymTab', 'stack'
    ]

    def __init__(self, *, litdateCons, litsymCons, littupCons, litstructCons, litframeCons):

        self._holderByModPathByName = {}
        self._frameBySymTab = {}
        self.stack = []
        self.stackManager = StackManager()
        self.globalsManager = GlobalsManager()
        self.codeManager = CodeManager()
        self.contextualScopeManager = ContextualScopeManager()
        self.symbolManager = SymManager()

        self.ctxs = {}
        self.modByPath = {}
        self.styleByName = {}
        self.srcById = {}
        self.linesById = {}
        self.nextSrcId = itertools.count(start=1)
        self.infercache = set()
        self.litdateCons = litdateCons
        self.litsymCons = litsymCons
        self.littupCons = littupCons
        self.litstructCons = litstructCons
        self.litframeCons = litframeCons
        self.scratch = Missing

        self.ctxs[GLOBAL_CTX] = GlobalSymTab(GLOBAL_CTX)
        self.ctxs[SCRATCH_CTX] = scratchCtx = ModSymTab(SCRATCH_CTX, self.ctxs[GLOBAL_CTX])
        self.scratch = scratchCtx
        self.frameForSymTab(self.ctxs[GLOBAL_CTX])
        self.frameForSymTab(self.ctxs[SCRATCH_CTX])


    def styleForName(self, name):
        return self.styleByName.get(name, unary)


    def dumpLines(self, srcId, l1, l2):
        l1 = max(l1, 1)
        lines = self.linesById[srcId]
        src = self.srcById[srcId]
        for l in range(l1, l2 + 1):
            s1, s2 = lines[l].s1, lines[l].s2
            print(src[s1:s2], file=sys.stderr)


    def pace(self, src, stopAtLine=Missing):
        srcId = next(self.nextSrcId)
        self.srcById[srcId] = src

        '' >> PP

        # parse
        tokens, lines = lex.lexBonesSrc(srcId, src)
        self.linesById[srcId] = lines
        if context.showSrc:
            for line in lines[1:]:
                f'{line.l:>3}:  {line.src}' >> PP
            '' >> PP

        snippet = parse_groups.parseStructure(tokens, self.scratch, src)

        if context.showGroups:
            snippet.PPGroup >> PP
            '' >> PP

        snippetTc = parse_phrase.parseSnippet(snippet, self.scratch, self)
        if context.showTc:
            tcReport = TcReport()
            snippetTc.PPTC(1, tcReport)
            for i, line in enumerate(tcReport):
                f'{i + 1:>3} {line.node.id:>3}  ' + '  ' * (line.depth - 1) + line.pp >> PP
            '' >> PP

        # analyse
        grammarError = Missing
        allVars = []
        typesReport = []

        analyse = False if context.analyse is Missing else context.analyse
        if analyse:
            from bones.lang.infer import Simplifier, visit, InferenceLogger
            with context(actions=[], kernel=self, tt=(InferenceLogger(log=False) if context.tt is Missing else context.tt), infercache=self.infercache):
                for i, n in enumerate(snippetTc.nodes):
                    linenum = i + 1
                    try:
                        with context(newVars=[], stop=False, tt=context.tt.setNum(linenum)): #.newLevel().preloadForMe(f'')):
                            if stopAtLine is not Missing and stopAtLine == linenum:
                                context.stop = True
                            t = visit(n, self.scratch)
                            with context(tt=context.tt.newLevel()):
                                s = Simplifier(context.newVars)
                                # s.trySimplifyAll()      # we have a simple return type but there may be vars underneath that haven't been similified
                                typesReport.append((n, s.trySimplify(t)))
                            allVars.extend(context.newVars)
                    except BonesIncompatibleTypesError as ex:
                        grammarError = ex
                        break
                '' >> context.tt

        if context.showTypes:
            for n, t in typesReport:
                f'{n.tok1.l1:>3}:  {t}' >> PP
            '' >> PP

        if context.showVars:
            COL1_WIDTH = 30
            for name, v in allVars:
                f'{name:<{COL1_WIDTH}} {v}' >> PP
            '' >> PP

        # compile


        # execute
        run = True if context.run is Missing else context.run
        if run and not grammarError:
            answer = self.executeTc(snippetTc)
        else:
            answer = Void

        return pace_res(tokens, typesReport, answer, grammarError)


    def importSymbols(self, path, names, symtab):
        if (mod := self.modByPath.get(path, Missing)) is Missing:
            # OPEN: search BONES_PATH too as well as PYTHON_PATH
            mod = __import__(path)
            splits = path.split(".")
            modPath = splits[0]
            if modPath not in self.modByPath:
                self.modByPath[modPath] = mod
            for name in splits[1:]:
                modPath = modPath + '.' + name if modPath else name
                mod = getattr(mod, name)
                if modPath not in self.modByPath:
                    self.modByPath[modPath] = mod
        for name in names:
            importee = Missing
            if hasattr(mod, name):
                importee = getattr(mod, name)
            else:
                # TODO keep functions by fnname by modname.
                for thingName in dir(mod):
                    thing = getattr(mod, thingName)
                    if isinstance(thing, jones._fn):
                        if thing.name == name:
                            importee = thing
                            break
                if importee is Missing:
                    raise BonesModuleImportError(f"Can't find '{name}' in {path}", ErrSite("Can't find name"))
            if isinstance(importee, BType):
                if symtab.hasT(name):
                    # OPEN: check that it's the same type else we need type namespaces implementing to handle this
                    pass
                else:
                    current = symtab.tMetaForGet(name)
                    if current is not Missing:
                        if importee is not current:
                            raise BonesModuleImportError(f"Trying to import '{name}'({importee}) but it is already defined as {current}")
                        else:
                            # already imported so nothing to do
                            pass
                    else:
                        symtab.defTMeta(name, importee)
            elif isinstance(importee, jones._fn):
                symtab.defFnMeta(name, importee.d._t, LOCAL_SCOPE)
                if isinstance(importee.d, tvfamily):
                    for overload in importee.d._overloadByNumArgs:
                        for _, tvfunc in overload.items():
                            style = tvfunc.style
                            currentStyle = self.styleByName.setdefault(name, style)
                            if style != currentStyle: raise BonesModuleImportError("oh dear")
                            symtab.bindFn(name, tvfunc)
                else:
                    style = importee.d.style
                    currentStyle = self.styleByName.setdefault(name, style)
                    if style != currentStyle: raise BonesModuleImportError("oh dear")
                    symtab.bindFn(name, importee.d)

            elif hasattr(importee, "_t"):

                if symtab.hasV(name):
                    # for the moment only import new names handle overloading later
                    pass
                else:
                    symtab.defVMeta(name, importee._t, LOCAL_SCOPE)
            else:
                raise ProgrammerError()


    def importValues(self, path, names, symtab):
        nvs = {}
        if (mod := self.modByPath.get(path, Missing)) is Missing:
            raise BonesModuleImportError(f"Can't import {names} because '{path}' has not been loaded.", ErrSite("Module not loaded"))
        for name in names:
            importee = Missing
            if hasattr(mod, name):
                importee = getattr(mod, name)
            else:
                # TODO keep functions by fnname by modname.
                for thingName in dir(mod):
                    thing = getattr(mod, thingName)
                    if isinstance(thing, jones._fn):
                        if thing.name == name:
                            importee = thing
                            break
                if importee is Missing:
                    raise BonesModuleImportError(f"Can't find '{name}' in {path}", ErrSite("Can't find name"))

            if isinstance(importee, (BType, jones._fn)):
                pass

            elif hasattr(importee, "_t"):
                # imports can only be done at module level, i.e. LOCAL_SCOPE
                symtab.defVMeta(name, importee._t, LOCAL_SCOPE)
                nvs[name] = importee

            else:
                raise ProgrammerError()

        return nvs

    def frameForSymTab(self, symtab):
        if (frame := self._frameBySymTab.get(symtab, Missing)) is Missing:
            self._frameBySymTab[symtab] = frame = bframe(symtab, Missing)
        return frame

    def blockframeForSymTab(self, symtab, parent, argnames, ):
        self.symtab, self.stack[-1], self.argnames, self._tArgs, self.frameForSymTab(self.symtab)

    def pushFrame(self, symtab):
        if self.stack:
            current = self.stack[-1]
        else:
            current = self.frameForSymTab(symtab)
        self.stack.append(frame := bframe(symtab, current))
        return frame

    def popFrame(self):
        self.stack = self.stack[:-1]

    def bind(self, symtab, scope, name, value):
        if scope == LOCAL_SCOPE and self.stack:
            frame = self.stack[-1]
        else:
            frame = self.frameForSymTab(symtab)
        frame[name] = value

    def getValue(self, symtab, scope, name):
        if scope == LOCAL_SCOPE and self.stack:
            frame = self.stack[-1]
        else:
            frame = self.frameForSymTab(symtab)
        return frame[name]

    def getReturn(self, symtab, scope, name):
        if scope == LOCAL_SCOPE and self.stack:
            frame = self.stack[-1]
        else:
            frame = self.frameForSymTab(symtab)
        return frame.values.get(name, Missing)

    def getOverload(self, symtab, scope, name, numargs):
        # check local frame first (as the function may have been passed as an argument)
        if scope == LOCAL_SCOPE:
            frame = self.stack[-1] if self.stack else self.frameForSymTab(symtab)
        else:
            raise NotImplementedError()
        if (ov := frame.values.get(name, Missing)) is Missing:
            # do the usual symtab search
            fnMeta = symtab.fMetaForGet(name, scope)  # get the meta using just the name
            ov = fnMeta.symtab.getOverload(name, numargs)  # get the fn using the name and number of args
            if ov is Missing: raise ProgrammerError()
        return ov

    # def getFamily(self, symtab, scope, name):
    #     # check local frame first (as the function may have been passed as an argument)
    #     if scope == LOCAL_SCOPE:
    #         frame = self.stack[-1] if self.stack else self.frameForSymTab(symtab)
    #     else:
    #         raise NotImplementedError()
    #     if (ov := frame.values.get(name, Missing)) is Missing:
    #         # do the usual symtab search
    #         fnMeta = symtab.fMetaForGet(name, scope)   # get the meta using just the name
    #         ov = fnMeta.symtab.getOverload(name, numargs)  # get the fn using the name and number of args
    #         if ov is Missing: raise ProgrammerError()
    #     return ov

    def parseLitInt(self, s):
        return litint(s)

    def parseLitNum(self, s):
        return litnum(s)

    def parseLitDate(self, s):
        raise NotYetImplemented()

    def parseLitDateTime(self, s):
        raise NotYetImplemented()

    def parseLitCityDateTime(self, s):
        raise NotYetImplemented()

    def parseLitTime(self, s):
        raise NotYetImplemented()

    def parseLitUtf8(self, s):
        return littxt(s[1:-1])  # OPEN: strip the quotes in lex instead

    def parseSym(self, s):
        return self.symbolManager.Sym(s)

    def parseLitSyms(self, ss):
        return litsyms([self.symbolManager.Sym(s) for s in ss])

    def executeTc(self, snippet):
        with context(kernel=self):
            answer = Void
            for i, n in enumerate(snippet.nodes):
                # context.tt  << i + 1
                answer = self.ex(n)
                if answer == None: answer = Void
        return answer

    def ex(self, n):
        if context.traceTcExec:
            print(f'Executing node: {n}')

        if isinstance(n, tcapply):
            # context.tt << f'tcapply {n}'
            numargs = len(n.argnodes)
            ov = self.getOverload(n.symtab, n.fnnode.scope, n.fnnode.name, numargs)
            args = [self.ex(argnode) for argnode in n.argnodes]
            if isinstance(ov, list):
                # the list thing needs sorting out
                ov = ov[numargs]

            if isinstance(ov, tvoverload):
                fn, schemaVars, distance = ov.selectFunction(*[_typeOf(arg) for arg in args])
            elif isinstance(ov, tcfunc):
                fn = ov
            else:
                raise ProgrammerError()

            if isinstance(fn, (tcfunc, tcblock)):
                return self.ex(fn)(*args)

            elif isinstance(fn, tvfunc):
                if fn.pass_tByT:
                    ret = fn(*args, tByT=schemaVars)
                else:
                    ret = fn(*args)
                return ret

            else:
                raise ProgrammerError(f"Unhandled  fn {{{type(fn)}}}")

        elif isinstance(n, tcbindval):
            # context.tt << f'tcbindval {n}'
            if n.accessors:
                raise NotYetImplemented()
            else:
                val = self.ex(n.vnode)
                self.bind(n.symtab, n.scope, n.name, val)
                return val

        elif isinstance(n, tcgetval):
            # context.tt << f'tcgetval {n}'
            v = self.getValue(n.symtab, n.scope, n.name)
            v = getattr(v, '_tv', Missing) or v                       # in case it is a boxed value
            for accessor in n.accessors:
                # OPEN: still a mess
                if hasattr(v, '__getitem__'):
                    v = v[self.symbolManager.Sym(accessor)]
                else:
                    v = getattr(v, accessor)
                v = getattr(v, '_tv', Missing) or v
            return v

        # elif isinstance(n, tcgetoverload):
        #     fnMeta = n.symtab.fMetaForGet(n.name, n.scope)
        #     return fnMeta.symtab.getOverload(n.name, n.numargs)

        elif isinstance(n, tcgetfamily):
            # context.tt << f'tcgetfamily {n}'
            fnMeta = n.symtab.fMetaForGet(n.name, n.scope)
            return fnMeta.symtab.getFamily(n.name)

        elif isinstance(n, tclit):
            return n.tv

        elif isinstance(n, tclitstruct):
            kvs = {}
            for k, v in n.tv._kvs():
                kvs[k] = self.ex(v)
            answer = self.litstructCons(n.tOut, kvs)
            return answer

        elif isinstance(n, tclittup):
            elems = [self.ex(e) for e in n.tv._v]
            answer = self.littupCons(n.tOut, elems)
            return answer

        elif isinstance(n, tclitbtype):
            return n.tOut

        elif isinstance(n, tcfunc):
            return n

        elif isinstance(n, tcblock):
            return n

        elif isinstance(n, tcbindfn):
            # only needed to be done at parse time
            pass

        elif isinstance(n, tcfromimport):
            # symbols, type holders and functions are gotten at parse time, but values must be loaded at execution time
            nvs = self.importValues(n.path, n.names, n.symtab)
            for name, v in nvs.items():
                self.bind(n.symtab, MODULE_SCOPE, name, v)

        else:
            raise NotYetImplemented(f"Unhandled node {{{n}}}")



handlersByErrSiteId.update({
    ('bones.kernel.core', Missing, 'importSymbols', "Can't find name") : '...',
    ('bones.kernel.core', Missing, 'importSymbols', "Module not loaded") : '...',
})

