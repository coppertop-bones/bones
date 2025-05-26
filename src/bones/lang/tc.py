# **********************************************************************************************************************
# Copyright 2025 David Briant, https://github.com/coppertop-bones. Licensed under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance with the License. You may obtain a copy of the  License at
# http://www.apache.org/licenses/LICENSE-2.0. Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY  KIND,
# either express or implied. See the License for the specific language governing permissions and limitations under the
# License. See the NOTICE file distributed with this work for additional information regarding copyright ownership.
# **********************************************************************************************************************

import sys
if hasattr(sys, '_TRACE_IMPORTS') and sys._TRACE_IMPORTS: print(__name__)

import itertools, collections
from bones.core.sentinels import Missing
from bones.core.errors import ProgrammerError, NotYetImplemented, handlersByErrSiteId
from bones.ts.metatypes import BType, BTFn, BTTuple
from bones.lang.types import void, TBI, null

_nodeseed = itertools.count(start=1)



# **********************************************************************************************************************
# tree code node
# **********************************************************************************************************************

class tcnode:
    __slots__ = ['id', 'tok1', 'tok2', 'st', 'tOut']
    def __init__(self, tok1, tok2, st):
        self.id = next(_nodeseed)
        self.tok1 = tok1
        self.tok2 = tok2
        self.st = st
        self.tOut = TBI
    def __eq__(self, other):
        if other.__class__ != self.__class__: return False
        return self.id == other.id
    def __hash__(self):
        return self.id
    def PPTC(self, depth, lines):
        raise NotImplementedError(f"Not implemented by {self.__class__}")
    def __repr__(self):
        return f'tcnode: {self.nodepath} has no repr {type(self)}'
    @property
    def nodepath(self):
        return f'{self.st.path}.{self.id}'


# **********************************************************************************************************************
# snippet - ordered list of nodes in same context
# **********************************************************************************************************************

class snippet(tcnode):
    __slots__ = ['nodes']
    def __init__(self, tok1, tok2, st, nodes):
        super().__init__(tok1, tok2, st)
        self.nodes = nodes
    def PPTC(self, depth, report):
        report << TcReportLine(self, depth, f'snippet: ')
        for node in self.nodes:
            node.PPTC(depth + 1, report)
    def __repr__(self):
        return f'snippet: {self.st.path}.{self.id}'


# **********************************************************************************************************************
# functions and application
# **********************************************************************************************************************

class apply(tcnode):
    __slots__ = ['fnnode', 'argnodes', '_tArgs']
    def __init__(self, tok1, tok2, st, fnnode, argnodes):
        super().__init__(tok1, tok2, st)
        self.fnnode = fnnode
        self.argnodes = argnodes
        self._tArgs = BTTuple(*[n.tOut for n in argnodes])
    def PPTC(self, depth, report):
        report << TcReportLine(self, depth, f'app')
        self.fnnode.PPTC(depth + 1, report)
        for argnode in self.argnodes:
            argnode.PPTC(depth + 1, report)
    def __repr__(self):
        return f'apply: {self.fnnode}({", ".join([repr(an) for an in self.argnodes])})'
    @property
    def tArgs(self):
        return self._tArgs

class block(tcnode):
    __slots__ = ['argnames', '_tArgs', 'numargs', 'body', '_t_']
    def __init__(self, tok1, tok2, st, argnames, tArgs, tRet, body):
        super().__init__(tok1, tok2, st)
        self.argnames = argnames
        if not isinstance(tArgs, BTTuple): raise ProgrammerError()
        self._tArgs = tArgs
        self.tOut = tRet
        self.numargs = len(argnames)
        self.body = body
        self._t_ = Missing
    def replaceTypes(self, tArgs, tRet):
        if not isinstance(tArgs, BTTuple): raise ProgrammerError()
        self._tArgs = tArgs
        self.tOut = tRet
        self._t_ = Missing
    @property
    def _t(self):
        if self._t_ is Missing:
            self._t_ = BTFn(self._tArgs, self.tOut)
        return self._t_
    @property
    def tRet(self):
        return self.tOut
    @property
    def tArgs(self):
        return self._tArgs
    def __call__(self, *args, **kwargs):
        raise NotYetImplemented()

class bfunc(tcnode):
    # possibly could inherit from block - is a function anything more than a block with its own scope and style?
    # can also be called as a normal function from coppertop hence has _t, tRet, tArgs properties and __call__
    __slots__ = ['argnames', '_tArgs', 'numargs', 'body', '_t_', 'literalstyle']
    def __init__(self, tok1, tok2, st, argnames, tArgs, tRet, body, literalstyle):
        super().__init__(tok1, tok2, st)
        self.argnames = argnames
        if not isinstance(tArgs, BTTuple): raise ProgrammerError()
        self._tArgs = tArgs
        self.tOut = tRet
        self.numargs = len(argnames)
        self.body = body
        self._t_ = Missing
        self.literalstyle = literalstyle
    def replaceTypes(self, tArgs, tRet):
        if not isinstance(tArgs, BTTuple): raise ProgrammerError()
        self._tArgs = tArgs
        self.tOut = tRet
        self._t_ = Missing
    @property
    def _t(self):
        if self._t_ is Missing:
            self._t_ = BTFn(self._tArgs, self.tOut)
        return self._t_
    @property
    def tRet(self):
        return self.tOut
    def PPTC(self, depth, report):
        argPPs = []
        for argName, tArg in zip(self.argnames, self.tArgs):
            argPPs += [f'{argName}:{tArg}']
        report << TcReportLine(self, depth, f'bfunc {self.st.path} [{", ".join(argPPs)}] -> {self.tOut}')
        for phrase in self.body:
            phrase.PPTC(depth + 1, report)
    def __repr__(self):
        nameTs = [f'{name}:{t}' for name, t in zip(self.argnames, self.tArgs)]
        return f'bfunc: {self.fullSig()}'
    def fullSig(self):
        nameTs = [f'{name}:{t}' for name, t in zip(self.argnames, self.tArgs)]
        return f'{{[{", ".join(nameTs)}] -> {self.tOut}}}'
    @property
    def tArgs(self):
        return self._tArgs
    def __call__(self, *args, **kwargs):
        raise NotYetImplemented()

class assumedfunc(bfunc): pass


# **********************************************************************************************************************
# type checking and coercion
# **********************************************************************************************************************

class coerce(tcnode):
    __slots__ = ['lhnode']
    def __init__(self, tok1, tok2, st, lhnode, t):
        super().__init__(tok1, tok2, st)
        self.lhnode = lhnode
        self.tOut = t

class partialcheck(tcnode):
    __slots__ = ['lhnode']
    def __init__(self, tok1, st, lhnode, tOut):
        super().__init__(tok1, tok1, st)
        self.lhnode = lhnode
        self.tOut = tOut
    def PPTC(self, depth, report):
        report << TcReportLine(self, depth, f'partialcheck {self.nodepath}')
        self.lhnode.PPTC(depth + 1, report)
    def __repr__(self):
        return f'partialcheck: {self.nodepath}'


# **********************************************************************************************************************
# value accessing
# **********************************************************************************************************************

class bindval(tcnode):
    __slots__ = ['name', 'scope', 'lhnode']
    def __init__(self, tok1, tok2, st, name, lhnode, scope):
        super().__init__(tok1, tok2, st)
        self.name = name
        self.scope = scope
        self.lhnode = lhnode
    def PPTC(self, depth, report):
        report << TcReportLine(self, depth, f'bind {self.st.path}.{self.name}')
        self.lhnode.PPTC(depth + 1, report)
    @property
    def nodepath(self):
        return f'{self.st.path}.{self.name}.{self.id}'
    def __repr__(self):
        return f'bind: {self.nodepath} = {self.lhnode.nodepath}'

class getval(tcnode):
    __slots__ = ['name', 'scope']
    def __init__(self, tok1, st, name, scope):
        super().__init__(tok1, tok1, st)
        self.name = name
        self.scope = scope
    def PPTC(self, depth, report):
        report << TcReportLine(self, depth, f'get {self.st.path}.{self.name}')
    @property
    def nodepath(self):
        return f'{self.st.path}.{self.name}.{self.id}'
    def __repr__(self):
        return f"get: {self.nodepath}"

class getsubvalname(tcnode):
    __slots__ = ['lhnode', 'name']
    def __init__(self, tok1, st, lhnode, name):
        super().__init__(tok1, tok1, st)
        self.lhnode = lhnode
        self.name = name
    def PPTC(self, depth, report):
        report << TcReportLine(self, depth, f'subgetname {self.st.path}.{self.name}')
    def __repr__(self):
        return f"subgetname: {self.nodepath}"

class getsubvalindex(tcnode):
    __slots__ = ['lhnode', 'index']
    def __init__(self, tok1, st, lhnode, index):
        super().__init__(tok1, tok1, st)
        self.lhnode = lhnode
        self.index = index
    def PPTC(self, depth, report):
        report << TcReportLine(self, depth, f'getsubvalindex {self.st.path}.{self.index}')
    def __repr__(self):
        return f"getsubvalindex: {self.nodepath}"


# **********************************************************************************************************************
# function accessing
# **********************************************************************************************************************

class bindfn(tcnode):
    __slots__ = ['name', 'lhnode', 'scope']
    def __init__(self, tok1, tok2, st, name, lhnode, scope):
        super().__init__(tok1, tok2, st)
        self.name = name
        self.lhnode = lhnode
        self.scope = scope
        if isinstance(lhnode, bfunc) and lhnode.st.name.startswith('anon'): lhnode.st.name = name
    def PPTC(self, depth, report):
        report << TcReportLine(self, depth, f'bindfn {self.st.path}.{self.name}')
        self.lhnode.PPTC(depth + 1, report)
    @property
    def nodepath(self):
        return f'{self.st.path}.{self.name}.{self.id}'
    def __repr__(self):
        return f'bindfn: {self.nodepath} = {self.lhnode.nodepath}'

class getoverload(tcnode):
    __slots__ = ['name', 'scope', 'numargs']
    def __init__(self, tok1, st, name, numargs, scope):
        super().__init__(tok1, tok1, st)
        self.name = name >> assertIs(str)
        self.numargs = numargs >> assertIs(int)
        self.scope = scope
    def PPTC(self, depth, report):
        report << TcReportLine(self, depth, f'getoverload {self.st.path}.{self.name}')
    @property
    def nodepath(self):
        return f'{self.st.path}.{self.name}_{self.numargs}.{self.id}'
    def __repr__(self):
        return f"getoverload: {self.nodepath}"

class getfamily(tcnode):
    __slots__ = ['name', 'scope']
    def __init__(self, tok1, st, name, scope):
        super().__init__(tok1, tok1, st)
        self.name = name >> assertIs(str)
        self.scope = scope
    def PPTC(self, depth, report):
        report << TcReportLine(self, depth, f'getfamily {self.st.path}.{self.name}')
    @property
    def nodepath(self):
        return f'{self.st.path}.{self.name}.{self.id}'
    def __repr__(self):
        return f"getfamily: {self.nodepath} {self.name}"


# **********************************************************************************************************************
# literals
# **********************************************************************************************************************

class lit(tcnode):
    # acts as a tv
    __slots__ = ['_v']
    def __init__(self, tok1, st, t, v):
        super().__init__(tok1, tok1, st)
        self.tOut = t
        self._v = v
    def PPTC(self, depth, report):
        report << TcReportLine(self, depth, f'lit {self._v}')
    def __repr__(self):
        return f"lit: {self.nodepath} {self.tOut}"
    @property
    def _t(self):
        return self.tOut

class littup(tcnode):
    __slots__ = ['_tv']
    def __init__(self, tok1, tok2, st, tv):
        super().__init__(tok1, tok2, st)
        self._tv = tv
    def PPTC(self, depth, report):
        report << TcReportLine(self, depth, f'littup {self._tv}')
    def __repr__(self):
        return f"littup: {self.nodepath} {self.tOut}"

class litstruct(tcnode):
    __slots__ = ['_tv']
    def __init__(self, tok1, tok2, st, tv):
        super().__init__(tok1, tok2, st)
        self._tv = tv
    def PPTC(self, depth, report):
        report << TcReportLine(self, depth, f'litstruct {self._tv}')
    def __repr__(self):
        return f"litstruct: {self.nodepath} {self.tOut}"

class litframe(tcnode):
    __slots__ = ['_tv']
    def __init__(self, tok1, tok2, st, tv):
        super().__init__(tok1, tok2, st)
        self._tv = tv
    def PPTC(self, depth, report):
        report << TcReportLine(self, depth, f'litframe {self._tv}')
    def __repr__(self):
        return f"litframe: {self.nodepath} {self.tOut}"


# **********************************************************************************************************************
# foreign functions
# **********************************************************************************************************************

class foreignfunc(tcnode): pass         # OPEN: to think through how to describe in bones itself how a call into a foreign language

class pfunc(foreignfunc): pass          # i.e. a different use case than using @coppertop in py-bones

class dfunc(foreignfunc): pass

class cfunc(foreignfunc): pass

class ffunc(foreignfunc): pass          # fortran func


# **********************************************************************************************************************
# misc
# **********************************************************************************************************************

class voidPhrase(tcnode):
    def __init__(self, tok1, tok2, st):
        super().__init__(tok1, tok2, st)
        self.tOut = void

class load(tcnode):
    def __init__(self, tok1, tok2, st, paths):
        super().__init__(tok1, tok2, st)
        self.tOut = void
        self.paths = paths
    def PPTC(self, depth, report):
        report << TcReportLine(self, depth, f'load {self.paths}')
    def __repr__(self):
        return f"load: {self.nodepath}"

class fromimport(tcnode):
    __slots__ = ['path', 'names']
    def __init__(self, tok1, tok2, st, path, names):
        super().__init__(tok1, tok2, st)
        self.tOut = void
        self.path = path
        self.names = names
    def PPTC(self, depth, report):
        report << TcReportLine(self, depth, f"from {self.path} import {', '.join(self.names)}")
    def __repr__(self):
        return f"fromimport: {self.nodepath}"


# **********************************************************************************************************************
# utils
# **********************************************************************************************************************

TcReportLine = collections.namedtuple("TcReportLine", ['node', 'depth', 'pp'])
class TcReport(list):
    def __lshift__(self, other):    # self << other
        self.append(other)
        return self
    def __add__(self, other):       # self + other (collection)
        for e in other:
            self.append(e)
        return self

class assertIs:
    def __init__(self, type):
        self.type = type
    def __rrshift__(self, lhs):     # lhs >> self
        if not isinstance(lhs, self.type): raise ValueError()
        return lhs


handlersByErrSiteId.update({
    ('bones.lang.tc', Missing, 'importSymbols', "Can't find name") : '...'
})
