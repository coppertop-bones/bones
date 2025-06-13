# **********************************************************************************************************************
# Copyright 2025 David Briant, https://github.com/coppertop-bones. Licensed under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance with the License. You may obtain a copy of the  License at
# http://www.apache.org/licenses/LICENSE-2.0. Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY  KIND,
# either express or implied. See the License for the specific language governing permissions and limitations under the
# License. See the NOTICE file distributed with this work for additional information regarding copyright ownership.
# **********************************************************************************************************************

import collections, itertools
from collections import namedtuple
from bones import jones
from bones.core.context import context
from bones.core.sentinels import Missing
from bones.core.errors import NotYetImplemented, ProgrammerError
from bones.core.errors import ScopeError
from bones.lang.types import _tvfunc, TBI
from bones.kernel.tc import tcfunc
from bones.ts.select import Overload, Family
from bones.kernel.core import MAX_NUM_ARGS, GLOBAL_SCOPE, LOCAL_SCOPE, PARENT_SCOPE, MODULE_SCOPE, CONTEXT_SCOPE



# SymbolTable
#   holds all information for symbols
#   holds the actual callable functions defined in it
#   (values are stored by the storage manager)
#   symbol tables can see other symbol tables - e.g. the global, module, contextual scope and lexicalParent
#
# scoping rules determine how the symbol table that defines a name is discovered - thus are behaviours not objects
#   types are only used inside <:..> etc and are stored in the global symbol table (the plan is to add type namespaces)
#   value scopes don't inherit - can access immediate parent with .fred and module with ..CONST
#   function scopes inherit from their lexical parent all the way up to module
#   functions are not allowed in global symbol table
#
# pipeline styles are kept globally in the kernel - so we know the set of function names, however we can have a local 
# name that refers to a value - so before accessing a name we ask for which symbol table is in and it's type
#
# consider
# {f(x)} - parser figures f is a function and can update the symtab accordingly, x is very ambiguous
# {x f} - this could be noun unary or noun noun - the parser must state it unaryOrNoun, and similarly for {x f y} and {x f y z}
#
# so by the time we are inferring, the fact of whether f is a function or a value has been determined
#
# when we are creating pins that f is function should already be known unless it is passed further
#
# in which case we go down the rabbit hole until we hit a usage of f and the valueOrFnNess ripples up the lexical scopes
#
# so before querying a name we need it's meta - what is it and which symtab does it belong to


# OPEN:
#  - function selection cache invalidation and refresh and reanalysis and recompilation of affected code



def ppScope(scope):
    if scope == LOCAL_SCOPE: return 'local'
    if scope == PARENT_SCOPE: return 'lexical_parent'
    if scope == MODULE_SCOPE: return 'module'
    if scope == CONTEXT_SCOPE: return 'contextual'
    if scope == GLOBAL_SCOPE: return 'global'


_anonSeed = itertools.count(start=1)


PYCHARM = False


class _Meta:
    __slots__ = ['t', 'symtab']
    def __init__(self, t, symtab):
        self.t = t
        self.symtab = symtab
    def __repr__(self):
        return f'{self.__class__.__name__}<t={self.t},symtab={self.symtab}>'

class VMeta(_Meta): pass
class FnMeta(_Meta): pass
class TMeta(_Meta): pass



class SymbolTable:

    __slots__ = [
        'name', 'kernel',
        '_lexicalParentSymTab', '_contextSymTab', '_moduleSymTab', '_globalSymTab',
        '_vMetaByName', '_fnMetaByName', '_tMetaByName', '_overloadsByNumArgs',
        '_newVMetaByName', '_newFnMetaByName', '_newTMetaByName', '_newFamilyByName',
        'implicitParams', 'inferring', '_localGets', '_parentGets', '_moduleGets', '_contextGets',
        '_globalGets', '_localSets', '_contextSets', '_globalSets'
    ]

    @property
    def _pycharmVars(self):
        return dict(name=self.name, kernel=self.kernel)

    def __init__(self, kernel, lexicalParentSt, contextSt, moduleSt, globalSt, name):
        # if a module then moduleSt and lexicalParentSt will be missing
        # if a top level function then lexicalParentSt will be missing
        self.name = 'anon'+str(next(_anonSeed)) if name is Missing else name
        self.kernel = kernel
        self._lexicalParentSymTab = lexicalParentSt
        self._contextSymTab = contextSt
        self._moduleSymTab = moduleSt
        self._globalSymTab = globalSt

        self._vMetaByName = {}
        self._fnMetaByName = {}
        self._tMetaByName = Missing if globalSt else {}     # protect ourselves slightly here
        self._overloadsByNumArgs = [{} for i in range(MAX_NUM_ARGS + 1)]

        self._newVMetaByName = {}
        self._newFnMetaByName = {}
        self._newTMetaByName = Missing if globalSt else {}  # and here
        self._newFamilyByName = {}

        self.implicitParams = []
        self.inferring = InferringHelper([], [])

        self._localGets = set()
        self._parentGets = set()
        self._moduleGets = set()
        self._contextGets = set()
        self._globalGets = set()
        self._localSets = set()
        self._contextSets = set()
        self._globalSets = set()


    def styleOfName(self, name):
        return self.kernel.styleForName(name)

    def hasF(self, name):
        return name in self._newFnMetaByName or name in self._fnMetaByName

    def hasV(self, name):
        return name in self._newVMetaByName or name in self._vMetaByName

    def hasT(self, name):
        return (name in self._globalSymTab._newTMetaByName) or (name in self._globalSymTab._tMetaByName)

    def noteGets(self, name, scope):
        if scope == LOCAL_SCOPE:
            self._localGets.add(name)
        elif scope == PARENT_SCOPE:
            self._parentGets.add(name)
        elif scope == MODULE_SCOPE:
            self._moduleGets.add(name)
        elif scope == CONTEXT_SCOPE:
            self._contextGets.add(name)
        elif scope == GLOBAL_SCOPE:
            self._globalGets.add(name)
        else:
            raise ProgrammerError("Unknown scope '%s'" % scope)

    def noteSets(self, name, scope):
        if scope == LOCAL_SCOPE:
            self._localSets.add(name)
        elif scope == CONTEXT_SCOPE:
            self._contextSets.add(name)
        elif scope == GLOBAL_SCOPE:
            self._globalSets.add(name)
        else:
            raise ProgrammerError("Unknown scope '%s'" % scope)

    def vMetaForGet(self, name, scope):
        if scope == LOCAL_SCOPE:
            m = self._newVMetaByName.get(name, Missing)
            if m is Missing:
                m = self._vMetaByName.get(name, Missing)
            if m is Missing and context.catchImplicitParams and len(name) == 1:
                m = self.defVMeta(name, TBI, scope)
                self.implicitParams.append(name)
            return m
        elif scope == PARENT_SCOPE:
            raise NotYetImplemented()
        elif scope == MODULE_SCOPE:
            raise NotYetImplemented()
        elif scope == CONTEXT_SCOPE:
            raise NotYetImplemented()
        elif scope == GLOBAL_SCOPE:
            m = self._globalSymTab.vMetaForGet(name, LOCAL_SCOPE)
            return m

    def fMetaForGet(self, name, scope):
        if scope == LOCAL_SCOPE:
            m = self._newFnMetaByName.get(name, Missing)
            if m is Missing:
                m = self._fnMetaByName.get(name, Missing)
            if m is Missing and self._lexicalParentSymTab is not Missing:
                m = self._lexicalParentSymTab.fMetaForGet(name, LOCAL_SCOPE)         # this will go all the way up to the module
            if m is Missing and self._moduleSymTab is not Missing:
                m = self._moduleSymTab.fMetaForGet(name, LOCAL_SCOPE)
            return m
        elif scope == CONTEXT_SCOPE:
            raise NotYetImplemented()
        else:
            raise ProgrammerError()

    def tMetaForGet(self, name):
        m = self._globalSymTab._newTMetaByName.get(name, Missing)
        if m is Missing:
            m = self._globalSymTab._tMetaByName.get(name, Missing)
        return m

    def fOrVMetaForGet(self, name, scope):
        if (m := self.fMetaForGet(name, scope)): return m
        return self.vMetaForGet(name, scope)


    def vMetaForBind(self, name, scope):
        if scope == LOCAL_SCOPE:
            m = self._newVMetaByName.get(name, Missing)
            if m is Missing:
                m = self._vMetaByName.get(name, Missing)
            if m in self.parsing.inferredArgnames:
                raise ProgrammerError(f'{name} has already been inferred as an argname')
            return m
        elif scope == CONTEXT_SCOPE:
            raise NotYetImplemented()
        elif scope == GLOBAL_SCOPE:
            m = self._globalSymTab.vMetaForGet(name, LOCAL_SCOPE)
            return m
        else:
            raise ProgrammerError()

    def fMetaForBind(self, name, scope):
        if scope == LOCAL_SCOPE:
            m = self._newFnMetaByName.get(name, Missing)
            if m is Missing:
                m = self._fnMetaByName.get(name, Missing)
            return m
        elif scope == CONTEXT_SCOPE:
            raise NotYetImplemented()
        else:
            raise ProgrammerError()

    def tMetaForBind(self, name):
        m = self._globalSymTab._newTMetaByName.get(name, Missing)
        if m is Missing:
            m = self._globalSymTab._tMetaByName.get(name, Missing)
        return m

    def defVMeta(self, name, t, scope):
        if scope == LOCAL_SCOPE:
            currentMeta = self._newVMetaByName.get(name, Missing)
            if currentMeta is Missing: currentMeta = self._vMetaByName.get(name, Missing)
            if currentMeta is not Missing and currentMeta.t != t:
                raise NotYetImplemented("Can't merge or redefine the types of values yet")
            if name in self._newFnMetaByName or name in self._fnMetaByName:
                self.changeFnMetaToVMeta(name)      # change the fn meta to a value meta
                # raise NotYetImplemented("A name can only refer to a value or an fn")
            meta = VMeta(t, self)
            self._newVMetaByName[name] = meta
            return meta
        elif scope == CONTEXT_SCOPE:
            raise NotYetImplemented()
        elif scope == GLOBAL_SCOPE:
            if name in self._globalSymTab._vMetaByName or name in self._globalSymTab._newVMetaByName: raise NotYetImplemented("Can't merge or redefine the types of values yet")
            meta = VMeta(t, self._globalSymTab)
            self._globalSymTab._newVMetaByName[name] = meta
            return meta
        else:
            raise ProgrammerError()

    def defFnMeta(self, name, t, scope):
        if self._globalSymTab is Missing: raise ScopeError("Can't define function in global scope")
        if scope == LOCAL_SCOPE:
            if name in self._vMetaByName or name in self._newVMetaByName: raise ScopeError("A name can only refer to a value or an fn")
            if name not in self._fnMetaByName or name not in self._newFnMetaByName:
                self._newFnMetaByName[name] = FnMeta(t, self)
        elif scope == CONTEXT_SCOPE:
            raise NotYetImplemented()
        else:
            raise ProgrammerError()

    def defTMeta(self, name, t):
        if name in self._globalSymTab._newTMetaByName or name in self._globalSymTab._tMetaByName: raise ProgrammerError()
        self._globalSymTab._newTMetaByName[name] = t


    def commitChanges(self):
        # raise NotYetImplemented()
        pass

    def bindFn(self, name, fn):
        if not self.hasF(name): raise ProgrammerError()
        if not isinstance(fn, (jones._nullary, jones._unary, jones._binary, jones._ternary, _tvfunc, Family, tcfunc)) and fn != TBI: raise ProgrammerError()
        if self._globalSymTab is Missing: raise ScopeError("Missing global scope")
        if name in self._vMetaByName or name in self._newVMetaByName: raise ScopeError("A name can only refer to a value or an fn")
        overload = self.getOverload(name, fn.numargs)
        overload[fn.tArgs] = fn
        return overload

    def getOverload(self, name, numargs):
        # MUSTDO merge the new ones with the old ones
        return self.getFamily(name).getOverload(numargs)

    def getFamily(self, name):
        if (family := self._newFamilyByName.get(name, Missing)) is Missing:
            self._newFamilyByName[name] = family = Family.newForMutation(name=name)
        return family

    @property
    def path(self):
        answer = ''
        if self._lexicalParentSymTab is not Missing:
            answer += self._lexicalParentSymTab.path
        elif self._moduleSymTab is not Missing:
            answer += self._moduleSymTab.path
        return self.name if answer == '' else answer + '.' + self.name

    def __repr__(self):
        return f'SymbolTable<{self.path}>'

    def updateMetaType(self, name, currentMeta, t):
        if isinstance(currentMeta, VMeta):
            if self._newVMetaByName[name].t != TBI: raise ProgrammerError()
            self._newVMetaByName[name] = VMeta(t, self)
        elif isinstance(currentMeta, FnMeta):
            self._newFnMetaByName[name] = FnMeta(t, self)
        else:
            raise ProgrammerError()

    def changeVMetaToFnMeta(self, name):
        oldT = self._newVMetaByName[name].t
        assert oldT == TBI
        del self._newVMetaByName[name]
        self.defFnMeta(name, TBI, LOCAL_SCOPE)
        return self._newFnMetaByName[name]

    def changeFnMetaToVMeta(self, name):
        oldT = self._newFnMetaByName[name].t
        assert oldT == TBI
        del self._newFnMetaByName[name]
        self.defVMeta(name, TBI, LOCAL_SCOPE)
        return self._newVMetaByName[name]



def fnSymTab(lexicalParentSt):
    if lexicalParentSt._globalSymTab is Missing:
        raise ProgrammerError()
    return SymbolTable(lexicalParentSt.kernel, lexicalParentSt, lexicalParentSt._contextSymTab, lexicalParentSt._moduleSymTab, lexicalParentSt._globalSymTab, Missing)

def blockSymTab(lexicalParentSt):
    # OPEN: implement properly - args are local all others are shared
    return lexicalParentSt


InferringHelper = collections.namedtuple('InferringHelper', ['typeVariables', 'fnVariables'])
