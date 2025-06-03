# **********************************************************************************************************************
# Copyright 2025 David Briant, https://github.com/coppertop-bones. Licensed under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance with the License. You may obtain a copy of the  License at
# http://www.apache.org/licenses/LICENSE-2.0. Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY  KIND,
# either express or implied. See the License for the specific language governing permissions and limitations under the
# License. See the NOTICE file distributed with this work for additional information regarding copyright ownership.
# **********************************************************************************************************************

import itertools, sys, collections
from bones.core.sentinels import Missing, Void
from bones.core.errors import GrammarError, ProgrammerError, handlersByErrSiteId, ErrSite, ImportError
from bones.kernel.base import BaseKernel
from bones.lang import parse_phrase, parse_groups, lex
from bones.lang.infer import Simplifier, visit, InferenceLogger
from bones.lang.tc import TcReport
from bones.core.context import context
from coppertop.pipe import _Dispatcher
import coppertop.dm.pp
from coppertop.dm.pp import PP
from bones.lang.core import LOCAL_SCOPE
from bones.ts.metatypes import BType
from bones import jones


pace_res = collections.namedtuple('pace_res', 'tokens, types, result, error')


class BonesKernel(BaseKernel):

    __slots__ = [
        'srcById', 'linesById', 'nextSrcId', 'infercache', 'tcrunner', 'scratch', 'litdateCons', 'littupCons',
        'litstructCons', 'litframeCons'
    ]

    def __init__(self, sm, *, litdateCons, littupCons, litstructCons, litframeCons):
        super().__init__(sm)
        self.srcById = {}
        self.linesById = {}
        self.nextSrcId = itertools.count(start=1)
        self.infercache = set()
        self.sm = sm
        self.litdateCons = litdateCons
        self.littupCons = littupCons
        self.litstructCons = litstructCons
        self.litframeCons = litframeCons
        self.tcrunner = Missing
        self.scratch = Missing

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

        snippet = parse_groups.parseStructure(tokens, self.scratch)

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
                                typesReport.append((n, st:=s.trySimplify(t)))
                            allVars.extend(context.newVars)
                    except GrammarError as ex:
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


        # run
        run = True if context.run is Missing else context.run
        if run and not grammarError:
            answer = self.tcrunner.executeTc(snippetTc)
        else:
            answer = Void

        return pace_res(tokens, typesReport, answer, grammarError)



    def loadModules(self, paths):
        # i.e. searches PYTHON_PATH and BONES_PATH for bones/ex/ and load core.py or core.b
        for path in paths:
            root = __import__(path)
            names = path.split(".")
            modPath = names[0]
            mod = root
            if modPath not in self.modByPath:
                self.modByPath[modPath] = mod
            for name in names[1:]:
                modPath = modPath + '.' + name if modPath else name
                mod = getattr(mod, name)
                if modPath not in self.modByPath:
                    self.modByPath[modPath] = mod



    def importSymbols(self, path, names, ctx):
        if (mod := self.modByPath.get(path, Missing)) is Missing:
            raise ImportError(f"Can't import {names} because '{path}' has not been loaded.", ErrSite("Module not loaded"))
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
                    raise ImportError(f"Can't find '{name}' in {path}", ErrSite("Can't find name"))
            if isinstance(importee, BType):
                if ctx.hasT(name):
                    # for the moment only import new names handle overloading later
                    pass
                else:
                    current = ctx.tMetaForGet(name)
                    if current is not Missing:
                        if importee is not current:
                            raise ImportError(f"Trying to import '{name}'({importee}) but it is already defined as {current}")
                        else:
                            # already imported so nothing to do
                            pass
                    else:
                        ctx.defType(name, importee)
            elif isinstance(importee, jones._fn):
                if ctx.hasF(name):
                    # for the moment only import new names handle overloading later
                    pass
                else:
                    ctx.defFnMeta(name, importee.d._t, LOCAL_SCOPE)
                    if isinstance(importee.d, _Dispatcher):
                        for fnBySig in importee.d.fnBySigByNumArgs:
                            for d in fnBySig.values():
                                style = d.style
                                currentStyle = self.styleByName.setdefault(name, style)
                                if style != currentStyle: raise ImportError("oh dear")
                                ctx.bindFn(name, d)
                    else:
                        style = importee.d.style
                        currentStyle = self.styleByName.setdefault(name, style)
                        if style != currentStyle: raise ImportError("oh dear")
                        ctx.bindFn(name, importee.d)

            elif hasattr(importee, "_t"):

                if ctx.hasV(name):
                    # for the moment only import new names handle overloading later
                    pass
                else:
                    ctx.defVMeta(name, importee._t, LOCAL_SCOPE)
            else:
                raise ProgrammerError()

    def importedValues(self, path, names):
        if (mod := self.modByPath.get(path, Missing)) is Missing:
            raise ImportError(f"Can't import {names} because '{path}' has not been loaded.", ErrSite("Module not loaded"))
        nvs = {}
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
                    raise ImportError(f"Can't find '{name}' in {path}", ErrSite("Can't find name"))

            if isinstance(importee, (BType, jones._fn)):
                pass

            elif hasattr(importee, "_t"):
                nvs[name] = importee

            else:
                raise ProgrammerError()
        return nvs


handlersByErrSiteId.update({
    ('bones.kernel.bones', Missing, 'importSymbols', "Can't find name") : '...',
    ('bones.kernel.bones', Missing, 'importSymbols', "Module not loaded") : '...',
})

