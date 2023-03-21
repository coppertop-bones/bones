# **********************************************************************************************************************
# Copyright (c) 2022 David Briant. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance
# with the License. You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
# on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
# the specific language governing permissions and limitations under the License.
# **********************************************************************************************************************

import builtins
from bones.core.sentinels import Missing
from bones.core.errors import NotYetImplemented, ProgrammerError
from bones.lang.core import LOCAL_SCOPE
from bones.lang.types import litdec, litint, litsym, litsyms, littxt, litdate
from bones.kernel.sym import SymTable


# The Storage Manager is responsible for storing values in bones
# and the library implementation languages. It stores the symbol tables, TC, BC, MC, etc and provides interfaces to
# the other components including grouper, parser, inferer, compilers, executer, inspectors and steppers
# defines how basic bones values are stored - provides the mechanism to allocate values
# defines the storage for N**T tuples, structs, etc. parses literal strings into values

# it does not control execution, stepping etc just provides some services they need



class PythonStorageManager(object):

    def __init__(self):
        self.syms = SymTable()
        self._holderByModPathByName = {}
        self.framesByContext = {}
        self.stack = []

    def parseLitInt(self, s):
        return litint, builtins.int(s)

    def parseLitDec(self, s):
        return litdec, float(s)

    def parseLitDate(self, s):
        raise NotYetImplemented()

    def parseLitDateTime(self, s):
        raise NotYetImplemented()

    def parseLitCityDateTime(self, s):
        raise NotYetImplemented()

    def parseLitTime(self, s):
        raise NotYetImplemented()

    def parseLitUtf8(self, s):
        return littxt, s

    def parseLitSym(self, s):
        return litsym, self.syms.Sym(s)

    def parseLitSyms(self, ss):
        return litsyms, [self.syms.Sym(s) for s in ss]

    def newTuple(self):
        raise NotYetImplemented()

    def newStuct(self):
        raise NotYetImplemented()

    def newTable(self):
        raise NotYetImplemented()

    def frameForCtx(self, ctx):
        if (frame := self.framesByContext.get(ctx, Missing)) is Missing:
            self.framesByContext[ctx] = frame = bframe(ctx, Missing)
        return frame

    def pushFrame(self, fnctx):
        if self.stack:
            current = self.stack[-1]
        else:
            current = self.frameForCtx(fnctx)
        self.stack.append(frame := bframe(fnctx, current))
        return frame

    def popFrame(self):
        self.stack = self.stack[:-1]

    def bind(self, ctx, scope, name, value):
        if scope == LOCAL_SCOPE and self.stack:
            frame = self.stack[-1]
        else:
            frame = self.frameForCtx(ctx)
        frame[name] = value

    def getValue(self, ctx, scope, name):
        if scope == LOCAL_SCOPE and self.stack:
            frame = self.stack[-1]
        else:
            frame = self.frameForCtx(ctx)
        return frame[name]

    def getReturn(self, ctx, scope, name):
        if scope == LOCAL_SCOPE and self.stack:
            frame = self.stack[-1]
        else:
            frame = self.frameForCtx(ctx)
        return frame.values.get(name, Missing)

    def getOverload(self, ctx, scope, name, numargs):
        # check local frame first (as the function may have been passed as an argument)
        if scope == LOCAL_SCOPE:
            frame = self.stack[-1] if self.stack else self.frameForCtx(ctx)
        else:
            raise NotImplementedError()
        if (ov := frame.values.get(name, Missing)) is Missing:
            # do the usual ctx search
            fnMeta = ctx.fMetaForGet(name, scope)   # get the meta using just the name
            ov = fnMeta.ctx.getOverload(name, numargs)  # get the fn using the name and number of args
            if ov is Missing: raise ProgrammerError()
        return ov



class bframe(object):
    def __init__(self, ctx, parent):
        self.ctx = ctx
        self.parent = parent
        self.values = {}
    def __setitem__(self, key, value):
        self.values[key] = value
    def __getitem__(self, key):
        return self.values[key]
    def __contains__(self, item):
        return item in self.values
    @property
    def depth(self):
        return self.parent.depth + 1 if self.parent else 1
    def __repr__(self):
        return f'bframe: [{self.depth}]{self.ctx.path}'



