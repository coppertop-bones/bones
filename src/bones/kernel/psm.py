# **********************************************************************************************************************
# Copyright 2025 David Briant, https://github.com/coppertop-bones. Licensed under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance with the License. You may obtain a copy of the  License at
# http://www.apache.org/licenses/LICENSE-2.0. Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY  KIND,
# either express or implied. See the License for the specific language governing permissions and limitations under the
# License. See the NOTICE file distributed with this work for additional information regarding copyright ownership.
# **********************************************************************************************************************

import builtins
from bones.core.sentinels import Missing
from bones.core.errors import NotYetImplemented, ProgrammerError
from bones.lang.core import LOCAL_SCOPE
from bones.lang.types import litdec, litint, litsym, litsyms, littxt, litdate
from bones.kernel.sym import SymManager


# The Storage Manager is responsible for storing values in bones
# and the library implementation languages. It stores the symbol tables, TC, BC, MC, etc and provides interfaces to
# the other components including grouper, parser, inferer, compilers, executer, inspectors and steppers
# defines how basic bones values are stored - provides the mechanism to allocate values
# defines the storage for N**T tuples, structs, etc. parses literal strings into values

# it does not control execution, stepping etc just provides some services they need



class PythonStorageManager:

    def __init__(self):
        self.syms = SymManager()
        self._holderByModPathByName = {}
        self.framesBySymTab = {}
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

    def framesForSymTab(self, st):
        if (frame := self.framesBySymTab.get(st, Missing)) is Missing:
            self.framesBySymTab[st] = frame = bframe(st, Missing)
        return frame

    def pushFrame(self, fnst):
        if self.stack:
            current = self.stack[-1]
        else:
            current = self.framesForSymTab(fnst)
        self.stack.append(frame := bframe(fnst, current))
        return frame

    def popFrame(self):
        self.stack = self.stack[:-1]

    def bind(self, st, scope, name, value):
        if scope == LOCAL_SCOPE and self.stack:
            frame = self.stack[-1]
        else:
            frame = self.framesForSymTab(st)
        frame[name] = value

    def getValue(self, st, scope, name):
        if scope == LOCAL_SCOPE and self.stack:
            frame = self.stack[-1]
        else:
            frame = self.framesForSymTab(st)
        return frame[name]

    def getReturn(self, st, scope, name):
        if scope == LOCAL_SCOPE and self.stack:
            frame = self.stack[-1]
        else:
            frame = self.framesForSymTab(st)
        return frame.values.get(name, Missing)

    def getOverload(self, st, scope, name, numargs):
        # check local frame first (as the function may have been passed as an argument)
        if scope == LOCAL_SCOPE:
            frame = self.stack[-1] if self.stack else self.framesForSymTab(st)
        else:
            raise NotImplementedError()
        if (ov := frame.values.get(name, Missing)) is Missing:
            # do the usual st search
            fnMeta = st.fMetaForGet(name, scope)   # get the meta using just the name
            ov = fnMeta.st.getOverload(name, numargs)  # get the fn using the name and number of args
            if ov is Missing: raise ProgrammerError()
        return ov



class bframe:
    def __init__(self, st, parent):
        self.st = st
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
        return f'bframe: [{self.depth}]{self.st.path}'



