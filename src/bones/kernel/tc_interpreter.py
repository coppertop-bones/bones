# **********************************************************************************************************************
# Copyright 2025 David Briant, https://github.com/coppertop-bones. Licensed under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance with the License. You may obtain a copy of the  License at
# http://www.apache.org/licenses/LICENSE-2.0. Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY  KIND,
# either express or implied. See the License for the specific language governing permissions and limitations under the
# License. See the NOTICE file distributed with this work for additional information regarding copyright ownership.
# **********************************************************************************************************************

from bones.kernel.tc import tcload, tcfromimport, tcbindval, tcapply, tcgetval, tcfunc, tclit, tcbindfn, tcgetfamily, \
    tcgetoverload, tclitstruct, tclittup, tclitbtype, tcblock
from bones.lang.types import _tvfunc
from bones.kernel._core import MODULE_SCOPE
from bones.kernel.symbol_table import Overload
from bones.core.sentinels import Missing, Void
from bones.core.errors import NotYetImplemented, ProgrammerError
from bones.core.utils import firstValue
from bones.ts.metatypes import BTTuple, updateSchemaVarsWith, fitsWithin, BType, BTypeError
from bones.core.context import context
from bones.ts.select import _typeOf
import bones.kernel.tc

# implements stepping and pure execution interfaces


def stepTc(tc, ctx, stepState):
    raise NotYetImplemented()

def executeBc(bc, ctx):
    raise NotYetImplemented()

def stepBc(bc, ctx, stepState):
    raise NotYetImplemented()

class NewTCInterpreter:

    # we use boxed values here as to do otherwise, e.g. only using type-tags for unions, would require a compilation
    # step to produce TC that optimally doesn't unnecessarily box

    def __init__(self, kernel, modulectx):
        self.k = kernel
        self.sm = kernel.sm

    def executeTc(self, snippet):
        bones.kernel.tc.k = self.k
        answer = Void
        for i, n in enumerate(snippet.nodes):
            # context.tt  << i + 1
            answer = self.ex(n)
            if answer == None: answer = Void
        bones.kernel.tc.k = Missing
        return answer

    def ex(self, n):
        if context.traceTcExec:
            print(f'Executing node: {n}')

        if isinstance(n, tcapply):
            # context.tt << f'tcapply {n}'
            sm = self.sm
            numargs = len(n.argnodes)
            ov = sm.getOverload(n.symtab, n.fnnode.scope, n.fnnode.name, numargs)
            args = [self.ex(argnode) for argnode in n.argnodes]
            if isinstance(ov, list):
                # the list thing needs sorting out
                ov = ov[numargs]
            if isinstance(ov, Overload):
                fn, schemaVars, distance = ov.selectFunction(*[_typeOf(arg) for arg in args])
            elif isinstance(ov, tcfunc):
                fn = ov
            else:
                raise ProgrammerError()

            if isinstance(fn, (tcfunc, tcblock)):
                return self.ex(fn)(*args)

            elif isinstance(fn, _tvfunc):
                if fn.pass_tByT:
                    ret = fn._v(*args, tByT=schemaVars)
                else:
                    ret = fn._v(*args)
                if hasattr(ret, '_t'):
                    if ret._t:
                        # check the actual return type fits the declared return type
                        if fn.tRet == py or fitsWithin(ret._t, fn.tRet):
                            return ret
                        else:
                            return ret
                            raise BTypeError(f"Return type mismatch: expected {fn.tRet}, got {ret._t}")
                    else:
                        return ret | fn.tRet
                else:
                    # use the coercer rather than impose construction with tv
                    if fitsWithin(_typeOf(ret), fn.tRet):
                        return ret
                    else:
                        return ret #| fn.tRet

            else:
                raise ProgrammerError(f"Unhandled  fn {{{type(fn)}}}")

        elif isinstance(n, tcbindval):
            # context.tt << f'tcbindval {n}'
            if n.accessors:
                raise NotYetImplemented()
            else:
                val = self.ex(n.vnode)
                self.sm.bind(n.symtab, n.scope, n.name, val)
                return val

        elif isinstance(n, tcgetval):
            # context.tt << f'tcgetval {n}'
            v = self.sm.getValue(n.symtab, n.scope, n.name)
            v = getattr(v, '_tv', Missing) or v                       # in case it is a boxed value
            for accessor in n.accessors:
                # OPEN: still a mess
                if hasattr(v, '__getitem__'):
                    v = v[self.sm.syms.Sym(accessor)]
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
            answer = self.k.litstructCons(n.tOut, kvs)
            return answer

        elif isinstance(n, tclittup):
            elems = [self.ex(e) for e in n.tv._v]
            answer = self.k.littupCons(n.tOut, elems)
            return answer

        elif isinstance(n, tclitbtype):
            return n.tOut

        elif isinstance(n, tcfunc):
            return n

        elif isinstance(n, tcblock):
            raise NotYetImplemented(f"tcblock {n}")
            return blockctx(n, self.sm.stack[-1])

        elif isinstance(n, tcbindfn):
            # only needed to be done at parse time
            pass

        elif isinstance(n, tcload):
            # only needed to be done at parse time
            pass

        elif isinstance(n, tcfromimport):
            # symbols, type holders and functions are gotten at parse time, but values must be loaded at execution time
            nvs = self.k.importValues(n.path, n.names, n.symtab)
            for name, v in nvs.items():
                self.sm.bind(n.symtab, MODULE_SCOPE, name, v)

        else:
            raise NotYetImplemented(f"Unhandled node {{{n}}}")


class TCInterpreter:

    # we use boxed values here as to do otherwise, e.g. only using type-tags for unions, would require a compilation
    # step to produce TC that optimally doesn't unnecessarily box

    def __init__(self, kernel, modulectx):
        self.k = kernel
        self.sm = kernel.sm

    def executeTc(self, snippet):
        bones.kernel.tc.k = self.k
        answer = Void
        for i, n in enumerate(snippet.nodes):
            # context.tt  << i + 1
            answer = self.ex(n)
            if answer == None: answer = Void
        bones.kernel.tc.k = Missing
        return answer

    def ex(self, n):
        if context.traceTcExec:
            print(f'Executing node: {n}')

        if isinstance(n, tcapply):
            # context.tt << f'tcapply {n}'
            sm = self.sm
            numargs = len(n.argnodes)
            ov = sm.getOverload(n.symtab, n.fnnode.scope, n.fnnode.name, numargs)
            args = [self.ex(argnode) for argnode in n.argnodes]
            if isinstance(ov, list):
                # the list thing needs sorting out
                ov = ov[numargs]
            if isinstance(ov, Overload):
                fn, schemaVars, distance = ov.selectFunction(*[_typeOf(arg) for arg in args])
            elif isinstance(ov, tcfunc):
                fn = ov
            else:
                raise ProgrammerError()

            if isinstance(fn, (tcfunc, tcblock)):
                return self.ex(fn)(*args)

            elif isinstance(fn, _tvfunc):
                if fn.pass_tByT:
                    ret = fn._v(*args, tByT=schemaVars)
                else:
                    ret = fn._v(*args)
                if hasattr(ret, '_t'):
                    if ret._t:
                        # check the actual return type fits the declared return type
                        if fn.tRet == py or fitsWithin(ret._t, fn.tRet):
                            return ret
                        else:
                            return ret
                            raise BTypeError(f"Return type mismatch: expected {fn.tRet}, got {ret._t}")
                    else:
                        return ret | fn.tRet
                else:
                    # use the coercer rather than impose construction with tv
                    if fitsWithin(_typeOf(ret), fn.tRet):
                        return ret
                    else:
                        return ret #| fn.tRet

            else:
                raise ProgrammerError(f"Unhandled  fn {{{type(fn)}}}")

        elif isinstance(n, tcbindval):
            # context.tt << f'tcbindval {n}'
            if n.accessors:
                raise NotYetImplemented()
            else:
                val = self.ex(n.vnode)
                self.sm.bind(n.symtab, n.scope, n.name, val)
                return val

        elif isinstance(n, tcgetval):
            # context.tt << f'tcgetval {n}'
            v = self.sm.getValue(n.symtab, n.scope, n.name)
            v = getattr(v, '_tv', Missing) or v                       # in case it is a boxed value
            for accessor in n.accessors:
                # OPEN: still a mess
                if hasattr(v, '__getitem__'):
                    v = v[self.k.symbolManager.Sym(accessor)]
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
            answer = self.k.litstructCons(n.tOut, kvs)
            return answer

        elif isinstance(n, tclittup):
            elems = [self.ex(e) for e in n.tv._v]
            answer = self.k.littupCons(n.tOut, elems)
            return answer

        elif isinstance(n, tclitbtype):
            return n.tOut

        elif isinstance(n, tcfunc):
            return n

        elif isinstance(n, tcblock):
            raise NotYetImplemented(f"tcblock {n}")
            return blockctx(n, self.sm.stack[-1])

        elif isinstance(n, tcbindfn):
            # only needed to be done at parse time
            pass

        elif isinstance(n, tcload):
            # only needed to be done at parse time
            pass

        elif isinstance(n, tcfromimport):
            # symbols, type holders and functions are gotten at parse time, but values must be loaded at execution time
            nvs = self.k.importValues(n.path, n.names, n.symtab)
            for name, v in nvs.items():
                self.sm.bind(n.symtab, MODULE_SCOPE, name, v)

        else:
            raise NotYetImplemented(f"Unhandled node {{{n}}}")

# class blockctx:
#     def __init__(self, tcblock, sm, enclosingFrame):
#         self.block = block
#         self.sm = sm
#         self.parent = parentFrame
#     def __call__(self, *args, **kwargs):
#         # this allows the block to be called as a normal function from Python
#         frame = self.sm.blockframe(self.symtab, k.sm.stack[-1], self.argnames, self._tArgs,
#                           s               k.sm.frameForSymTab(self.symtab))
#
#         for name, arg in zip(self.argnames, args):
#             k.sm.bind(frame.symtab, LOCAL_SCOPE, name, arg)
#         for n in self.body:
#             val = k.tcrunner.ex(n)
#         if (ret := k.sm.getReturn(frame.symtab, LOCAL_SCOPE, RET_VAR_NAME)) is Missing: ret = val
#         return ret
#
#     def __repr__(self):
#         return f'blockctx({self.block}, {self.parent}, {self.argnames}, {self.tArgs}, {self.frame})'


py = BType('py')

