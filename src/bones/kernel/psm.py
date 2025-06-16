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
from bones.kernel.core import LOCAL_SCOPE
from bones.lang.types import litnum, litint, litsym, litsyms, littxt, litdate
from bones.kernel.sym import SymManager


# The Storage Manager is responsible for storing values in bones
# and the library implementation languages. It stores the symbol tables, TC, BC, MC, etc and provides interfaces to
# the other components including grouper, parser, inferer, compilers, executer, inspectors and steppers
# defines how basic bones values are stored - provides the mechanism to allocate values
# defines the storage for N**T tuples, structs, etc. parses literal strings into values

# it does not control execution, stepping etc just provides some services they need



class PythonStorageManager:

    __slots__ = ('syms', '_holderByModPathByName', '_frameBySymTab', 'stack')

    def __init__(self):
        self.syms = SymManager()
        self._holderByModPathByName = {}
        self._frameBySymTab = {}
        self.stack = []

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
        return self.syms.Sym(s)

    def parseLitSyms(self, ss):
        return litsyms([self.syms.Sym(s) for s in ss])

    def newTuple(self):
        raise NotYetImplemented()

    def newStuct(self):
        raise NotYetImplemented()

    def newTable(self):
        raise NotYetImplemented()

    def frameForSymTab(self, symtab):
        if (frame := self._frameBySymTab.get(symtab, Missing)) is Missing:
            self._frameBySymTab[symtab] = frame = bframe(symtab, Missing)
        return frame

    def blockframeForSymTab(self, symtab, parent, argnames, ):
        self.symtab, k.sm.stack[-1], self.argnames, self._tArgs, k.sm.frameForSymTab(self.symtab)

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
            fnMeta = symtab.fMetaForGet(name, scope)   # get the meta using just the name
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


    

class bframe:
    def __init__(self, symtab, parent):
        self.symtab = symtab
        self.parent = parent
        self.values = {}
    def __setitem__(self, key, value):
        self.values[key] = value
    def __getitem__(self, key):
        return self.values[key]
    def __contains__(self, key):
        return key in self.values
    @property
    def depth(self):
        return self.parent.depth + 1 if self.parent else 1
    def __repr__(self):
        return f'bframe: [{self.depth}]{self.symtab.path}'


class blockframe:
    def __init__(self, symtab, parentFrame, argnames, lexicalParent):
        self.symtab = symtab
        self.parent = parent
        self.lexicalParent = lexicalParent
        self.values = {}
    def __setitem__(self, key, value):
        if key in self.values:
            raise RuntimeError(f'Not allowed to rebind argument {key} in block {self.symtab.path}')
        if key not in self.lexicalParent.values:
            raise RuntimeError(f'Not allowed to bind new name "{key}" in parent {self.parent.symtab.path}')
        self.parent.values[key] = value
    def __getitem__(self, key):
        if (v := self.values.get(key, Missing)) is Missing:
            v = self.parent.values[key]
        return v
    def __contains__(self, key):
        return key in self.values
    @property
    def depth(self):
        return self.parent.depth + 1 if self.parent else 1
    def __repr__(self):
        return f'bframe: [{self.depth}]{self.symtab.path}'



