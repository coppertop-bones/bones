# **********************************************************************************************************************
# Copyright 2025 David Briant, https://github.com/coppertop-bones. Licensed under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance with the License. You may obtain a copy of the  License at
# http://www.apache.org/licenses/LICENSE-2.0. Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY  KIND,
# either express or implied. See the License for the specific language governing permissions and limitations under the
# License. See the NOTICE file distributed with this work for additional information regarding copyright ownership.
# **********************************************************************************************************************

# tcsnippet - ordered list of nodes in same context
# tcapply, tcblock, tcfunc
# tccoerce
# tcpartialcheck
# tcbindval, tcgetval, tcbindfn, tcgetfamily, tcgetoverload
# tclit, tclittup, tclitstruct, tclitframe, tclitbtype
# tcvoidphrase
# tcload, tcfromimport


import sys
if hasattr(sys, '_TRACE_IMPORTS') and sys._TRACE_IMPORTS: print(__name__)

import itertools, collections
from bones.core.sentinels import Missing
from bones.core.errors import ProgrammerError, NotYetImplemented, handlersByErrSiteId
from bones.ts.metatypes import BType, BTFn, BTTuple
from bones.lang.types import void, TBI, null
from bones.kernel.core import LOCAL_SCOPE, RET_VAR_NAME

_nodeseed = itertools.count(start=1)

k = Missing



# **********************************************************************************************************************
# tree code node
# **********************************************************************************************************************

class tcnode:
    __slots__ = ['id', 'tok1', 'tok2', 'symtab', 'tOut']
    def __init__(self, tok1, tok2, symtab):
        self.id = next(_nodeseed)
        self.tok1 = tok1
        self.tok2 = tok2
        self.symtab = symtab
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
        return f'{self.symtab.path}.{self.id}'
    def setTOut(self, tOut):
        if not isinstance(tOut, BType): raise ProgrammerError(f"tOut must be a BType, not {type(tOut)}")
        self.tOut = tOut
        return self


# **********************************************************************************************************************
# tcsnippet - ordered list of nodes in same context
# **********************************************************************************************************************

class tcsnippet(tcnode):
    __slots__ = ['nodes']
    def __init__(self, tok1, tok2, symtab, nodes):
        super().__init__(tok1, tok2, symtab)
        self.nodes = nodes
    def PPTC(self, depth, report):
        report << TcReportLine(self, depth, f'snippet: ')
        for node in self.nodes:
            node.PPTC(depth + 1, report)
    def __repr__(self):
        return f'tcsnippet: {self.symtab.path}.{self.id}'


# **********************************************************************************************************************
# functions and application
# **********************************************************************************************************************

class tcapply(tcnode):
    __slots__ = ['fnnode', 'argnodes', '_tArgs']
    def __init__(self, tok1, tok2, symtab, fnnode, argnodes):
        super().__init__(tok1, tok2, symtab)
        self.fnnode = fnnode
        self.argnodes = argnodes
        self._tArgs = BTTuple(*[n.tOut for n in argnodes])
    def PPTC(self, depth, report):
        report << TcReportLine(self, depth, f'app')
        self.fnnode.PPTC(depth + 1, report)
        for argnode in self.argnodes:
            argnode.PPTC(depth + 1, report)
    def __repr__(self):
        return f'tcapply: {self.fnnode}({", ".join([repr(an) for an in self.argnodes])})'
    @property
    def tArgs(self):
        return self._tArgs

class tcblock(tcnode):
    # OPEN: Are _t, tRet, tArgs properties need for analysis or just to allow tcfunc to be callable from Python
    __slots__ = ['argnames', '_tArgs', 'numargs', 'body', '_t_']
    @classmethod
    def TCName(cls):
        return 'block'
    def __init__(self, tok1, tok2, symtab, argnames, tArgs, tRet, body):
        super().__init__(tok1, tok2, symtab)
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
    def tArgs(self):
        return self._tArgs
    @property
    def tRet(self):
        return self.tOut
    def PPTC(self, depth, report):
        argPPs = []
        for argName, tArg in zip(self.argnames, self.tArgs):
            argPPs += [f'{argName}:{tArg}']
        report << TcReportLine(self, depth, f'{self.TCName()} {self.symtab.path} [{", ".join(argPPs)}] -> {self.tOut}')
        for phrase in self.body:
            phrase.PPTC(depth + 1, report)
    def __repr__(self):
        nameTs = [f'{name}:{t}' for name, t in zip(self.argnames, self.tArgs)]
        return f'{type(self).__name__}: {self.fullSig()}'
    def fullSig(self):
        nameTs = [f'{name}:{t}' for name, t in zip(self.argnames, self.tArgs)]
        return f'{{[{", ".join(nameTs)}] -> {self.tOut}}}'

class tcfunc(tcblock):
    __slots__ = ['literalstyle']
    @classmethod
    def TCName(cls):
        return 'func'
    def __init__(self, tok1, tok2, symtab, argnames, tArgs, tRet, body, literalstyle):
        super().__init__(tok1, tok2, symtab, argnames, tArgs, tRet, body)
        self.literalstyle = literalstyle
    def __call__(self, *args, **kwargs):
        # this allows the function to be called as a normal function from puthon
        frame = k.sm.pushFrame(self.symtab)
        for name, arg in zip(self.argnames, args):
            k.sm.bind(frame.symtab, LOCAL_SCOPE, name, arg)
        for n2 in self.body:
            val = k.tcrunner.ex(n2)
        if (ret := k.sm.getReturn(frame.symtab, LOCAL_SCOPE, RET_VAR_NAME)) is Missing: ret = val
        k.sm.popFrame()
        return ret

class tcassumedfunc(tcfunc): pass


# **********************************************************************************************************************
# type checking and coercion
# **********************************************************************************************************************

class tccoerce(tcnode):
    __slots__ = ['lhnode']
    def __init__(self, tok1, tok2, symtab, lhnode, t):
        super().__init__(tok1, tok2, symtab)
        self.lhnode = lhnode
        self.tOut = t

class tcpartialcheck(tcnode):
    __slots__ = ['lhnode']
    def __init__(self, tok1, symtab, lhnode, tOut):
        super().__init__(tok1, tok1, symtab)
        self.lhnode = lhnode
        self.tOut = tOut
    def PPTC(self, depth, report):
        report << TcReportLine(self, depth, f'partialcheck {self.nodepath}')
        self.lhnode.PPTC(depth + 1, report)
    def __repr__(self):
        return f'tcpartialcheck: {self.nodepath}'


# **********************************************************************************************************************
# value accessing
# **********************************************************************************************************************

class tcbindval(tcnode):
    __slots__ = ['vnode', 'scope', 'name', 'accessors']
    def __init__(self, tok1, tok2, symtab, vnode, scope, name, accessors):
        super().__init__(tok1, tok2, symtab)
        self.vnode = vnode
        self.scope = scope
        self.name = name
        self.accessors = accessors
    def PPTC(self, depth, report):
        report << TcReportLine(self, depth, f'bind {self.symtab.path}.{self.name}')
        self.vnode.PPTC(depth + 1, report)
    @property
    def nodepath(self):
        return f'{self.symtab.path}.{self.name}.{self.id}'
    def __repr__(self):
        return f'tcbindval: {self.nodepath} = {self.vnode.nodepath}'

class tcgetval(tcnode):
    __slots__ = ['scope', 'name', 'accessors']
    def __init__(self, tok1, symtab, scope, name, accessors):
        super().__init__(tok1, tok1, symtab)
        self.scope = scope
        self.name = name
        self.accessors = accessors
    def PPTC(self, depth, report):
        names = [self.symtab.path, self.name]
        if self.accessors: names.extend(self.accessors)
        report << TcReportLine(self, depth, f'getval {".".join(names)}')
    @property
    def nodepath(self):
        return f'{self.symtab.path}.{self.name}.{self.id}'
    def __repr__(self):
        return f"tcgetval: {self.nodepath}"


# **********************************************************************************************************************
# function accessing
# **********************************************************************************************************************

class tcbindfn(tcnode):
    __slots__ = ['fnode', 'scope', 'name']
    def __init__(self, tok1, tok2, symtab, name, fnode, scope):
        super().__init__(tok1, tok2, symtab)
        self.name = name
        self.fnode = fnode
        self.scope = scope
        if isinstance(fnode, tcfunc) and fnode.symtab.name.startswith('anon'): fnode.symtab.name = name
    def PPTC(self, depth, report):
        report << TcReportLine(self, depth, f'bindfn {self.symtab.path}.{self.name}')
        self.fnode.PPTC(depth + 1, report)
    @property
    def nodepath(self):
        return f'{self.symtab.path}.{self.name}.{self.id}'
    def __repr__(self):
        return f'tcbindfn: {self.nodepath} = {self.fnode.nodepath}'

class tcgetfamily(tcnode):
    __slots__ = ['name', 'scope']
    def __init__(self, tok1, symtab, name, scope):
        super().__init__(tok1, tok1, symtab)
        self.name = name >> assertIs(str)
        self.scope = scope
    def PPTC(self, depth, report):
        report << TcReportLine(self, depth, f'getfamily {self.symtab.path}.{self.name}')
    @property
    def nodepath(self):
        return f'{self.symtab.path}.{self.name}.{self.id}'
    def __repr__(self):
        return f'tcgetfamily: {self.nodepath} {self.name}'

class tcgetoverload(tcnode):
    __slots__ = ['name', 'scope', 'numargs']
    def __init__(self, tok1, symtab, name, numargs, scope):
        super().__init__(tok1, tok1, symtab)
        self.name = name >> assertIs(str)
        self.numargs = numargs >> assertIs(int)
        self.scope = scope
    def PPTC(self, depth, report):
        report << TcReportLine(self, depth, f'getoverload {self.symtab.path}.{self.name}')
    @property
    def nodepath(self):
        return f'{self.symtab.path}.{self.name}_{self.numargs}.{self.id}'
    def __repr__(self):
        return f'tcgetoverload: {self.nodepath}'


# **********************************************************************************************************************
# literals
# **********************************************************************************************************************

class tclit(tcnode):
    __slots__ = ['tv']
    def __init__(self, tok1, symtab, tv):
        super().__init__(tok1, tok1, symtab)
        self.tOut = tv._t
        self.tv = tv
    def PPTC(self, depth, report):
        report << TcReportLine(self, depth, f'lit {self.tv._v}')
    def __repr__(self):
        return f"tclit: {self.nodepath} {self.tOut}"
    @property
    def _t(self):
        return self.tOut

class tclittup(tcnode):
    __slots__ = ['tv']
    def __init__(self, tok1, tok2, symtab, tv):
        super().__init__(tok1, tok2, symtab)
        self.tv = tv
    def PPTC(self, depth, report):
        report << TcReportLine(self, depth, f'littup {self.tv}')
    def __repr__(self):
        return f"tclittup: {self.nodepath} {self.tOut}"

class tclitstruct(tcnode):
    __slots__ = ['tv']
    def __init__(self, tok1, tok2, symtab, tv):
        super().__init__(tok1, tok2, symtab)
        self.tv = tv
        self.tOut = tv._t
    def PPTC(self, depth, report):
        report << TcReportLine(self, depth, f'litstruct {self.tv}')
    def __repr__(self):
        return f"tclitstruct: {self.nodepath} {self.tOut}"

class tclitframe(tcnode):
    __slots__ = ['tv']
    def __init__(self, tok1, tok2, symtab, tv):
        super().__init__(tok1, tok2, symtab)
        self.tv = tv
    def PPTC(self, depth, report):
        report << TcReportLine(self, depth, f'litframe {self.tv}')
    def __repr__(self):
        return f"tclitframe: {self.nodepath} {self.tOut}"

class tclitbtype(tcnode):
    __slots__ = []
    def __init__(self, tok1, tok2, symtab, t):
        super().__init__(tok1, tok2, symtab)
        self.tOut = t
    def PPTC(self, depth, report):
        report << TcReportLine(self, depth, f'btype {self.tOut}')
    def __repr__(self):
        return f"tclitbtype: {self.nodepath} {self.tOut}"


# **********************************************************************************************************************
# misc
# **********************************************************************************************************************

class tcvoidphrase(tcnode):
    def __init__(self, tok1, tok2, symtab):
        super().__init__(tok1, tok2, symtab)
        self.tOut = void

class tcload(tcnode):
    def __init__(self, tok1, tok2, symtab, paths):
        super().__init__(tok1, tok2, symtab)
        self.tOut = void
        self.paths = paths
    def PPTC(self, depth, report):
        report << TcReportLine(self, depth, f'load {self.paths}')
    def __repr__(self):
        return f"tcload: {self.nodepath}"

class tcfromimport(tcnode):
    __slots__ = ['path', 'names']
    def __init__(self, tok1, tok2, symtab, path, names):
        super().__init__(tok1, tok2, symtab)
        self.tOut = void
        self.path = path
        self.names = names
    def PPTC(self, depth, report):
        report << TcReportLine(self, depth, f"from {self.path} import {', '.join(self.names)}")
    def __repr__(self):
        return f"tcfromimport: {self.nodepath}"


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
    ('bones.kernel.tc', Missing, 'importSymbols', "Can't find name") : '...'
})
