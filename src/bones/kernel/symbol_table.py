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
from coppertop.core import context, Missing, NotYetImplemented, ProgrammerError
from bones.kernel.errors import BonesScopeAccessError
from bones.lang.types import TBI
from bones.kernel.tc import tcfunc, tcblock
from bones.ts.select import tvfunc, tvoverload, tvfamily
from bones.kernel._core import MAX_NUM_ARGS, GLOBAL_SCOPE, LOCAL_SCOPE, PARENT_SCOPE, MODULE_SCOPE, CONTEXT_SCOPE


# The purpose of the symbol table is to map a name (symbol) into the overall structure of the program. For example, in
# C a name in a block could be defined in the block scope, the parent block scope, ..., enclosing function scope or
# global scope. In a Python a name in a function can be found in the function's env, in a parent function, ..., module.
# This resolution must happen after parsing (consider defining fred after fred has been gotten from a parent scope) and
# before the analysis step. It must also be done after the module (consider defining a name after a function). After
# parsing the symbol tables for the module and each function and block must be consolidated. After this consolidation
# the symbol tables know where each names lives - in the global, contextual, frame or code scopes - and can be called
# on to generate offsets (in the Python implementation) for those different scopes.

# in the REPL we can define a function called fred that refers to a module variable jow that hasn't been defined yet?
# in a modules source this is clearly possible.

# thus bones is multi pass and can refer to names defined later - which can make for nicer code organisation.

# The scope modifiers ".", "..", "_." and "_.." add a little more structure to the program's source code, in fact
# enough stucture that the only names that might need consolidating are block variables, which are always defined in
# the enclosing function's scope. Thus, we could have a consolidation step in bones (and should know where it comes in
# the PACE process) but we don't need one for now. If we added block locals or one level access then we would
# potentially need a consolidation step. If we allowed the parent scope modified to scan up the parent's parent all the
# way up to the module we would need a consolidation process and consolidation rules to handle ambiguities.

# Note block arguments may be the same name as names in the enclosing function scope. Thus this is allowable:

# {
#     x = 1
#     [1,2,3] collect [[x] x + 1]
# }


# getSlot(scope, name)
#  global (includes modules) must be done per thread - global ky value map
#  local - in stack-frame
#  contextual - heap - hash map?

# symbol table must know compilers understanding of the type of every name
# in union the slot must also keep the type (two slots for python system?) boxed by bones
# heap objects must be boxed

# module and global scope can get slot from a global generator
# function and block scopes can get slot from a local generator - one per




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




class _SymTab:

    __slots__ = [
        'name',
        '_vMetaByName', '_fnMetaByName', '_tMetaByName', '_overloadsByNumArgs',
        '_newVMetaByName', '_newFnMetaByName', '_newTMetaByName', '_newFamilyByName',
        'implicitParams', 'inferring'
    ]

    # @property
    # def _pycharmVars(self):
    #     return dict(name=self.name, kernel=self.kernel)

    def __init__(self, name):

        self.name = 'anon'+str(next(_anonSeed)) if name is Missing else name

        self._vMetaByName = {}
        self._fnMetaByName = {}
        self._tMetaByName = {}
        self._overloadsByNumArgs = [{} for i in range(MAX_NUM_ARGS + 1)]

        self._newVMetaByName = {}
        self._newFnMetaByName = {}
        self._newTMetaByName = {}
        self._newFamilyByName = {}

        self.implicitParams = []
        self.inferring = InferringHelper([], [])


    def hasF(self, name):
        return name in self._newFnMetaByName or name in self._fnMetaByName

    def hasV(self, name):
        return name in self._newVMetaByName or name in self._vMetaByName

    def hasT(self, name):
        raise NotYetImplemented()

    def tMetaForBind(self, name):
        raise NotImplementedError()

    def tMetaForGet(self, name):
        raise NotImplementedError()

    def fOrVMetaForGet(self, name, scope):
        if (m := self.fMetaForGet(name, scope)): return m
        return self.vMetaForGet(name, scope)

    def vMetaForBind(self, name, scope):
        if scope == LOCAL_SCOPE:
            m = self._newVMetaByName.get(name, Missing)
            if m is Missing:
                m = self._vMetaByName.get(name, Missing)
            return m
        elif scope == CONTEXT_SCOPE:
            raise NotYetImplemented()
        else:
            raise ProgrammerError()

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

    def fMetaForGet(self, name, scope):
        raise NotImplementedError()

    def defVMeta(self, name, t, scope):
        raise NotImplementedError()

    def defFnMeta(self, name, t, scope):
        raise NotImplementedError()

    def defTMeta(self, name, t):
        if name in self._globalSymTab._newTMetaByName or name in self._globalSymTab._tMetaByName: raise ProgrammerError()
        self._globalSymTab._newTMetaByName[name] = t

    def commitChanges(self):
        # raise NotYetImplemented()
        pass

    def bindFn(self, name, fn):
        if not self.hasF(name): raise ProgrammerError()
        if not isinstance(fn, (jones._nullary, jones._unary, jones._binary, jones._ternary, tvfunc, tvfamily, tcfunc, tcblock)) and fn != TBI:
            raise ProgrammerError()
        if self._globalSymTab is Missing: raise BonesScopeAccessError('Missing global scope')
        if name in self._vMetaByName or name in self._newVMetaByName: raise BonesScopeAccessError('A name can only refer to a value or an fn')
        overload = self.getOverload(name, fn.numargs)
        overload[fn.tArgs.types] = fn
        return overload

    def getOverload(self, name, numargs):
        # MUSTDO merge the new ones with the old ones
        return self.getFamily(name).getOverload(numargs)

    def getFamily(self, name):
        if (family := self._newFamilyByName.get(name, Missing)) is Missing:
            self._newFamilyByName[name] = family = tvfamily.newForMutation(name=name)
        return family

    @property
    def path(self):
        raise NotImplementedError()

    @property
    def parentPath(self):
        answer = ''
        if self._lexicalParentSymTab is not Missing:
            answer += self._lexicalParentSymTab.path
        elif self._moduleSymTab is not Missing:
            answer += self._moduleSymTab.path
        return answer

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


        
class GlobalSymTab(_SymTab):
    __slots__ = []

    def __init__(self, name):
        super().__init__(name)
        
    def __repr__(self):
        return f'GlobalSymTab<{self.path}>'

    @property
    def path(self):
        return self.name

    def hasT(self, name):
        return (name in self._newTMetaByName) or (name in self._tMetaByName)

    def tMetaForBind(self, name):
        m = self._newTMetaByName.get(name, Missing)
        if m is Missing:
            m = self._tMetaByName.get(name, Missing)
        return m

    def tMetaForGet(self, name):
        raise NotImplementedError()

    def fMetaForGet(self, name, scope):
        if scope == LOCAL_SCOPE:
            m = self._newFnMetaByName.get(name, Missing)
            if m is Missing:
                m = self._fnMetaByName.get(name, Missing)
            return m
        elif scope == CONTEXT_SCOPE:
            raise NotYetImplemented()
        else:
            raise ProgrammerError()

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
        else:
            raise ProgrammerError()

    def defFnMeta(self, name, t, scope):
        raise BonesScopeAccessError('Can\'t define function in global scope')



class CtxSymTab(_SymTab):  # as soon as we access a contextual scope we need analysis / code gen for each situation
    __slots__ = ['_enclosingSymTab']

    def __init__(self, enclosingSt):
        super().__init__('Ctx')
        _enclosingSymTab = enclosingSt

    def __repr__(self):
        return f'CtxSymTab<{self.path}>'

    @property
    def path(self):
        return self.name

    def tMetaForBind(self, name):
        raise BonesScopeAccessError('Can\'t define type in contextual scope')

    def tMetaForGet(self, name):
        raise NotImplementedError()

    def fMetaForGet(self, name, scope):
        if scope == LOCAL_SCOPE:
            m = self._newFnMetaByName.get(name, Missing)
            if m is Missing:
                m = self._fnMetaByName.get(name, Missing)
            return m
        elif scope == CONTEXT_SCOPE:
            raise NotYetImplemented()
        else:
            raise ProgrammerError()

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
        else:
            raise ProgrammerError()

    def defFnMeta(self, name, t, scope):
        raise BonesScopeAccessError('Can\'t define function in contextual scope')



class ModSymTab(_SymTab):
    __slots__ = ['_globalSymTab', '_contextSymTab']

    def __init__(self, name, globalSt):
        super().__init__(name)
        self._globalSymTab = globalSt
        self._contextSymTab = CtxSymTab(self)

    def __repr__(self):
        return f'ModSymTab<{self.path}>'

    @property
    def path(self):
        return self.name

    @property
    def _moduleSymTab(self):
        return self

    def hasT(self, name):
        return (name in self._globalSymTab._newTMetaByName) or (name in self._globalSymTab._tMetaByName)

    def tMetaForBind(self, name):
        m = self._globalSymTab._newTMetaByName.get(name, Missing)
        if m is Missing:
            m = self._globalSymTab._tMetaByName.get(name, Missing)
        return m

    def tMetaForGet(self, name):
        m = self._globalSymTab._newTMetaByName.get(name, Missing)
        if m is Missing:
            m = self._globalSymTab._tMetaByName.get(name, Missing)
        return m

    def vMetaForBind(self, name, scope):
        if scope == LOCAL_SCOPE:
            m = self._newVMetaByName.get(name, Missing)
            if m is Missing:
                m = self._vMetaByName.get(name, Missing)
            return m
        elif scope == CONTEXT_SCOPE:
            raise NotYetImplemented()
        elif scope == GLOBAL_SCOPE:
            m = self._globalSymTab.vMetaForGet(name, LOCAL_SCOPE)
            return m
        else:
            raise ProgrammerError()

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
            return m
        elif scope == CONTEXT_SCOPE:
            raise NotYetImplemented()
        else:
            raise ProgrammerError()

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
        if scope == LOCAL_SCOPE:
            if name in self._vMetaByName or name in self._newVMetaByName: raise BonesScopeAccessError('A name can only refer to a value or an fn')
            if name not in self._fnMetaByName or name not in self._newFnMetaByName:
                self._newFnMetaByName[name] = FnMeta(t, self)
        elif scope == CONTEXT_SCOPE:
            raise NotYetImplemented()
        else:
            raise ProgrammerError()



# at the moment we intend to pass .x on the stack (possibly by register) rather than as a closure (which requires
# memory access for sure), _lexicalParentSymTab is needed for analysis
class FnSymTab(_SymTab):
    __slots__ = ['_globalSymTab', '_moduleSymTab', '_lexicalParentSymTab', '_contextSymTab']

    def __init__(self, name, globalSt, moduleSt, lexicalParentSt):
        super().__init__(name)
        self._globalSymTab = globalSt
        self._moduleSymTab = moduleSt
        self._lexicalParentSymTab = lexicalParentSt
        self._contextSymTab = CtxSymTab(self)

    def __repr__(self):
        return f'FnSymTab<{self.path}>'

    @property
    def path(self):
        answer = ''
        if self._lexicalParentSymTab is not Missing:
            answer += self._lexicalParentSymTab.path
        elif self._moduleSymTab is not Missing:
            answer += self._moduleSymTab.path
        return self.name if answer == '' else answer + '.' + self.name

    def hasT(self, name):
        return (name in self._globalSymTab._newTMetaByName) or (name in self._globalSymTab._tMetaByName)

    def tMetaForBind(self, name):
        m = self._globalSymTab._newTMetaByName.get(name, Missing)
        if m is Missing:
            m = self._globalSymTab._tMetaByName.get(name, Missing)
        return m

    def tMetaForGet(self, name):
        m = self._globalSymTab._newTMetaByName.get(name, Missing)
        if m is Missing:
            m = self._globalSymTab._tMetaByName.get(name, Missing)
        return m

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

    def vMetaForBind(self, name, scope):
        if scope == LOCAL_SCOPE:
            m = self._newVMetaByName.get(name, Missing)
            if m is Missing:
                m = self._vMetaByName.get(name, Missing)
            return m
        elif scope == CONTEXT_SCOPE:
            raise NotYetImplemented()
        elif scope == GLOBAL_SCOPE:
            m = self._globalSymTab.vMetaForGet(name, LOCAL_SCOPE)
            return m
        else:
            raise ProgrammerError()

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
        if scope == LOCAL_SCOPE:
            if name in self._vMetaByName or name in self._newVMetaByName: raise BonesScopeAccessError('A name can only refer to a value or an fn')
            if name not in self._fnMetaByName or name not in self._newFnMetaByName:
                self._newFnMetaByName[name] = FnMeta(t, self)
        elif scope == CONTEXT_SCOPE:
            raise NotYetImplemented()
        else:
            raise ProgrammerError()



class BlockSymTab(_SymTab):
    __slots__ = ['_globalSymTab', '_moduleSymTab', '_lexicalParentSymTab', '_contextSymTab']

    def __init__(self, name, globalSt, moduleSt, lexicalParentSt):
        super().__init__(name)
        self._globalSymTab = globalSt
        self._moduleSymTab = moduleSt
        self._lexicalParentSymTab = lexicalParentSt
        self._contextSymTab = lexicalParentSt._contextSymTab

    def __repr__(self):
        return f'BlockSymTab<{self.path}>'

    @property
    def path(self):
        answer = ''
        if self._lexicalParentSymTab is not Missing:
            answer += self._lexicalParentSymTab.path
        elif self._moduleSymTab is not Missing:
            answer += self._moduleSymTab.path
        return self.name if answer == '' else answer + '.' + self.name

    def hasT(self, name):
        return (name in self._globalSymTab._newTMetaByName) or (name in self._globalSymTab._tMetaByName)

    def tMetaForBind(self, name):
        m = self._globalSymTab._newTMetaByName.get(name, Missing)
        if m is Missing:
            m = self._globalSymTab._tMetaByName.get(name, Missing)
        return m

    def tMetaForGet(self, name):
        m = self._globalSymTab._newTMetaByName.get(name, Missing)
        if m is Missing:
            m = self._globalSymTab._tMetaByName.get(name, Missing)
        return m

    def vMetaForBind(self, name, scope):
        if scope == LOCAL_SCOPE:
            m = self._newVMetaByName.get(name, Missing)
            if m is Missing:
                m = self._vMetaByName.get(name, Missing)
            return m
        elif scope == CONTEXT_SCOPE:
            raise NotYetImplemented()
        elif scope == GLOBAL_SCOPE:
            m = self._globalSymTab.vMetaForGet(name, LOCAL_SCOPE)
            return m
        else:
            raise ProgrammerError()

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
        if scope == LOCAL_SCOPE:
            if name in self._vMetaByName or name in self._newVMetaByName: raise BonesScopeAccessError('A name can only refer to a value or an fn')
            if name not in self._fnMetaByName or name not in self._newFnMetaByName:
                self._newFnMetaByName[name] = FnMeta(t, self)
        elif scope == CONTEXT_SCOPE:
            raise NotYetImplemented()
        else:
            raise ProgrammerError()



def fnSymTab(lexicalParentSt):
    return FnSymTab(Missing, lexicalParentSt._globalSymTab, lexicalParentSt._moduleSymTab, lexicalParentSt)



def blockSymTab(lexicalParentSt):
    return BlockSymTab(Missing, lexicalParentSt._globalSymTab, lexicalParentSt._moduleSymTab, lexicalParentSt)



InferringHelper = collections.namedtuple('InferringHelper', ['typeVariables', 'fnVariables'])
