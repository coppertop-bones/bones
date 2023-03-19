# **********************************************************************************************************************
# Copyright (c) 2022 David Briant. All rights reserved.
# This file is part of py-bones. For licensing contact David Briant.
# **********************************************************************************************************************

import collections, itertools
from collections import namedtuple
from bones import jones
from bones.core.sentinels import Missing
from bones.core.errors import NotYetImplemented, ProgrammerError
from coppertop.pipe import _Function, _Dispatcher
from bones.core.errors import ScopeError
from bones.lang.core import MAX_NUM_ARGS
from bones.lang.types import TBI
from bones.lang.tc import bfunc
from bones.lang.metatypes import BTUnion, BTFn, BTOverload
from bones.lang.core import LOCAL_SCOPE, PARENT_SCOPE, MODULE_SCOPE, CONTEXT_SCOPE, GLOBAL_SCOPE

# Ctx
#   holds all the type information for an environment / context
#   holds the actual callable functions defined in it
#   (values are stored by the storage manager)
#   contexts can see other contexts - e.g. the global, module, context scope context and lexicalParent
#
# scoping rules determine how the context that defines a name is discovered - thus are behaviours not objects
#   types are only used inside <:..> etc and are stored in the global context (we may add module types if needed later)
#   value scopes don't inherit - can access immediate parent with .fred and module with ..CONST
#   function scopes inherit from their lexical parent all the way up to modules
#   functions are not allowed in global context
#
# pipeline styles are kept globally in the kernel - so we know the set of function names, however we can have a local 
# name that refers to a value - so before accessing a name we ask for which context is in and it's type
#
# consider
# {f(x)} - parser figures f is a function and can update the ctx accordingly, x is very ambiguous
# {x f} - this could be noun unary or noun noun - the parser must state it unaryOrNoun, and similarly for {x f y} and {x f y z}
#
# so by the time we are inferring, the fact of whether f is a function or a value has been determined
#
# when we are creating pins that f is function should already be known unless it is passed further
#
# in which case we go down the rabbit hole until we hit a usage of f and the valueOrFnNess ripples up the lexical scopes
#
# so before querying a name we need it's meta - what is it and which ctx does it belong to



def ppScope(scope):
    if scope == LOCAL_SCOPE: return 'local'
    if scope == PARENT_SCOPE: return 'lexical_parent'
    if scope == MODULE_SCOPE: return 'module'
    if scope == CONTEXT_SCOPE: return 'contextual'
    if scope == GLOBAL_SCOPE: return 'global'

VMeta = namedtuple('VMeta', ['t', 'ctx'])
FnMeta = namedtuple('FnMeta', ['t', 'ctx'])         # actual type schemas are kept in the overloads
TMeta = namedtuple('TMeta', ['t', 'ctx'])

_anonSeed = itertools.count(start=1)


PYCHARM = False

def tOverload(): pass


# Overload and Family are for managing collections of functions - we can optimise later, and these should be
# integrated with the dispatchers in the piping

class Family(object):
    __slots__ = ['name', 'overloads', '_t_']

    def __init__(self, name, overloads):
        self.name = name
        self.overloads = overloads
        self._t_ = Missing

    @property
    def _t(self):
        if self._t_ is Missing or PYCHARM:
            tFns = []
            for ov in self.overloads:
                if ov is not Missing:
                    for sig, fn in ov._fnBySig.items():
                        tFns.append(fn._t)
            self._t_ = BTOverload(*tFns)
        return self._t_


class Overload(object):
    # holds a collection of functions for a given name and number of args

    __slots__ = ['name', 'numargs', '_fnsTBI', '_t_', '_tUpperBounds_', '_fnBySig']

    def __init__(self, name, numargs):
        self.name = name
        self.numargs = numargs
        self._fnsTBI = _TBIQueue()
        self._t_ = Missing
        self._tUpperBounds_ = Missing           # set else where
        self._fnBySig = {}

    @property
    def _t(self):
        if self._t_ is Missing:
            self._t_ = BTOverload(*[fn._t for fn in self._fnBySig.values()])
        return self._t_

    def __setitem__(self, sig, fn):
        if fn.numargs != self.numargs: raise ProgrammerError()
        self._t_ = Missing
        self._tUpperBounds_ = Missing
        needsInferring = False
        for tArg in fn.tArgs:
            if tArg == TBI:
                needsInferring = True
                break
        if fn.tRet == TBI:
            needsInferring = True
        if needsInferring:
            # if any arg needs to be inferred then it cannot be added to the overload yet and that can only be done
            # post inference so let's trying queuing it?
            self._fnsTBI << fn
        else:
            if fn in self._fnsTBI:
                self._fnsTBI.remove(fn)
            self._fnBySig[sig] = fn

    def __getitem__(self, sig):
        return self._fnBySig[sig]

    def __repr__(self):
        answer = f'{self.name}_{self.numargs}'
        ppT = ''
        try:
            ppT = repr(self._t)
        except:
            1/0
            try:
                tArgs = []
                tRets = []
                # collate the types for each arg
                for i in range(self.numargs):
                    tArgsN = []
                    for fn in self._fnsTBI:
                        tArgsN.append(fn.tArgs.types[i])
                    tArgs.append(BTUnion(*tArgsN) if len(tArgsN) != 1 else tArgsN[0])
                # collate the tRets
                for fn in self._fnsTBI:
                    tRets.append(fn.tRet)
                tRet = BTUnion(*tRets) if len(tRets) > 1 else tRets[0]
                ppT = repr(BTFn(tArgs, tRet))
            except:
                ppT = 'Error calc _tUpper'

        return f'{answer} ({ppT})'



class Ctx(object):

    __slots__ = [
        'name', 'kernel',
        '_lexicalParentCtx', '_contextCtx', '_moduleCtx', '_globalCtx',
        '_vMetaByName', '_fnMetaByName', '_tMetaByName', '_overloadsByNumArgs',
        '_newVMetaByName', '_newFnMetaByName', '_newTMetaByName', '_newOverloadsByNumArgs',
        'argCatcher', 'inferring'
    ]

    def __init__(self, kernel, lexicalParentCtx, contextCtx, moduleCtx, globalCtx, name):
        # if a module then moduleCtx and lexicalParentCtx will be missing
        # if a top level function then lexicalParentCtx will be missing
        self.name = 'anon'+str(next(_anonSeed)) if name is Missing else name
        self.kernel = kernel
        self._lexicalParentCtx = lexicalParentCtx
        self._contextCtx = contextCtx
        self._moduleCtx = moduleCtx
        self._globalCtx = globalCtx

        self._vMetaByName = {}
        self._fnMetaByName = {}
        self._tMetaByName = Missing if globalCtx else {}     # protect ourselves slightly here
        self._overloadsByNumArgs = [{} for i in range(MAX_NUM_ARGS + 1)]

        self._newVMetaByName = {}
        self._newFnMetaByName = {}
        self._newTMetaByName = Missing if globalCtx else {}  # and here
        self._newOverloadsByNumArgs = [{} for i in range(MAX_NUM_ARGS + 1)]

        self.argCatcher = Missing
        self.inferring = InferringHelper([], [])


    def styleOfName(self, name):
        return self.kernel.styleForName(name)

    def hasF(self, name):
        return name in self._newFnMetaByName or name in self._fnMetaByName

    def hasV(self, name):
        return name in self._newVMetaByName or name in self._vMetaByName

    def hasT(self, name):
        return name in self._newTMetaByName or name in self._tMetaByName


    def vMetaForGet(self, name, scope):
        if scope == LOCAL_SCOPE:
            m = self._newVMetaByName.get(name, Missing)
            if m is Missing:
                m = self._vMetaByName.get(name, Missing)
            if m is Missing and self.argCatcher and len(name) == 1:
                m = self.defVMeta(name, TBI, scope)
                self.argCatcher.inferredArgnames.append(name)
            return m
        elif scope == PARENT_SCOPE:
            raise NotYetImplemented()
        elif scope == MODULE_SCOPE:
            raise NotYetImplemented()
        elif scope == CONTEXT_SCOPE:
            raise NotYetImplemented()
        elif scope == GLOBAL_SCOPE:
            m = self._globalCtx.vMetaForGet(name, LOCAL_SCOPE)
            return m

    def fMetaForGet(self, name, scope):
        if scope == LOCAL_SCOPE:
            m = self._newFnMetaByName.get(name, Missing)
            if m is Missing:
                m = self._fnMetaByName.get(name, Missing)
            if m is Missing and self._lexicalParentCtx is not Missing:
                m = self._lexicalParentCtx.fMetaForGet(name, LOCAL_SCOPE)         # this will go all the way up to the module
            if m is Missing and self._moduleCtx is not Missing:
                m = self._moduleCtx.fMetaForGet(name, LOCAL_SCOPE)
            return m
        elif scope == CONTEXT_SCOPE:
            raise NotYetImplemented()
        else:
            raise ProgrammerError()

    def tMetaForGet(self, name):
        m = self._globalCtx._newTMetaByName.get(name, Missing)
        if m is Missing:
            m = self._globalCtx._tMetaByName.get(name, Missing)
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
            m = self._globalCtx.vMetaForGet(name, LOCAL_SCOPE)
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
        m = self._globalCtx._newTMetaByName.get(name, Missing)
        if m is Missing:
            m = self._globalCtx._tMetaByName.get(name, Missing)
        return m


    def defVMeta(self, name, t, scope):
        if scope == LOCAL_SCOPE:
            if name in self._newVMetaByName or name in self._vMetaByName: raise NotYetImplemented("Can't merge or redefine the types of values yet")
            if name in self._newFnMetaByName or name in self._fnMetaByName: raise NotYetImplemented("A name can only refer to a value or an fn")
            meta = VMeta(t, self)
            self._newVMetaByName[name] = meta
            return meta
        elif scope == CONTEXT_SCOPE:
            raise NotYetImplemented()
        elif scope == GLOBAL_SCOPE:
            if name in self._globalCtx._vMetaByName or name in self._globalCtx._newVMetaByName: raise NotYetImplemented("Can't merge or redefine the types of values yet")
            meta = VMeta(t, self._globalCtx)
            self._globalCtx._newVMetaByName[name] = meta
            return meta
        else:
            raise ProgrammerError()

    def defFnMeta(self, name, t, scope):
        if self._globalCtx is Missing: raise ScopeError("Can't define function in global scope")
        if scope == LOCAL_SCOPE:
            if name in self._vMetaByName or name in self._newVMetaByName: raise ScopeError("A name can only refer to a value or an fn")
            if name not in self._fnMetaByName or name not in self._newFnMetaByName:
                self._newFnMetaByName[name] = FnMeta(t, self)
        elif scope == CONTEXT_SCOPE:
            raise NotYetImplemented()
        else:
            raise ProgrammerError()

    def defTMeta(self, name, t):
        if name in self._globalCtx._newTMetaByName or name in self._globalCtx._tMetaByName: raise ProgrammerError()
        self._globalCtx._newTMetaByName[name] = t


    def commitChanges(self):
        # raise NotYetImplemented()
        pass

    def bindFn(self, name, fn):
        if name not in self._fnMetaByName and name not in self._newFnMetaByName: raise ProgrammerError()
        if not isinstance(fn, (jones._nullary, jones._unary, jones._binary, jones._ternary, jones._rau, _Function, _Dispatcher, bfunc)) and fn != TBI: raise ProgrammerError()
        if self._globalCtx is Missing: raise ScopeError("Can't define function in global scope")
        if name in self._vMetaByName or name in self._newVMetaByName: raise ScopeError("A name can only refer to a value or an fn")
        if not self.hasF(name): raise ProgrammerError()
        numargs = fn.numargs
        overloadsByName = self._newOverloadsByNumArgs[numargs]
        if (overload := overloadsByName.get(name, Missing)) is Missing: overload = overloadsByName[name] = Overload(name, numargs)
        overload[fn.tArgs] = fn
        return overload

    def getOverload(self, name, numargs):
        # MUSTDO merge the new ones with the old ones
        return self._newOverloadsByNumArgs[numargs][name]

    def getOverloadFamily(self, name):
        ovs = [Missing for i in range(MAX_NUM_ARGS + 1)]
        for i, m in enumerate(self._newOverloadsByNumArgs):
            # MUSTDO merge the new ones with the old ones
            if (ov := m.get(name, Missing)) is not Missing:
                ovs[i] = ov
        return Family(name, ovs)

    @property
    def path(self):
        answer = ''
        if self._lexicalParentCtx is not Missing:
            answer += self._lexicalParentCtx.path
        elif self._moduleCtx is not Missing:
            answer += self._moduleCtx.path
        return self.name if answer == '' else answer + '.' + self.name

    def __repr__(self):
        return f'Ctx<{self.path}>'

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



def newFnCtx(lexicalParentCtx):
    if lexicalParentCtx._globalCtx is Missing:
        raise ProgrammerError()
    return Ctx(lexicalParentCtx.kernel, lexicalParentCtx, lexicalParentCtx._contextCtx, lexicalParentCtx._moduleCtx, lexicalParentCtx._globalCtx, Missing)



class _TBIQueue(object):
    def __init__(self):
        self._fns = []   # need a queue as potentially the parser could add more than one before types are inferred
    def __lshift__(self, f):   # self << f
        self._fns.append(f)
    def __contains__(self, f):
        return f in self._fns
    def remove(self, f):
        self._fns.remove(f)
    def __repr__(self):
        return f'<{", ".join([repr(e) for e in self._fns])}>'
    def __len__(self):
        return len(self._fns)
    # def first(self):
    #     return self._fns[0]
    def __iter__(self):
        return iter(self._fns)


ArgCatcher = collections.namedtuple('ArgCatcher', ['inferredArgnames'])
InferringHelper = collections.namedtuple('InferringHelper', ['typeVariables', 'fnVariables'])