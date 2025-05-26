# **********************************************************************************************************************
# Copyright 2025 David Briant, https://github.com/coppertop-bones. Licensed under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance with the License. You may obtain a copy of the  License at
# http://www.apache.org/licenses/LICENSE-2.0. Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY  KIND,
# either express or implied. See the License for the specific language governing permissions and limitations under the
# License. See the NOTICE file distributed with this work for additional information regarding copyright ownership.
# **********************************************************************************************************************

from coppertop.pipe import _Function
from bones.lang.tc import load, fromimport, bindval, apply, getval, bfunc, lit, bindfn, getfamily, getoverload, litstruct, littup
from bones.lang.core import LOCAL_SCOPE, RET_VAR_NAME
from bones.lang.symbol_table import Overload
from bones.core.sentinels import Missing, Void
from bones.core.errors import NotYetImplemented, ProgrammerError
from bones.core.utils import firstValue
from bones.ts.metatypes import BTTuple, updateSchemaVarsWith, fitsWithin
from bones.core.context import context

# implements stepping and pure execution interfaces


def stepTc(tc, ctx, stepState):
    raise NotYetImplemented()

def executeBc(bc, ctx):
    raise NotYetImplemented()

def stepBc(bc, ctx, stepState):
    raise NotYetImplemented()



class TCInterpreter:

    # we use boxed values here as to do otherwise, e.g. only using type-tags for unions, would require a compilation
    # step to produce TC that optimally doesn't unnecessarily box

    def __init__(self, kernel, modulectx):
        self.k = kernel
        self.sm = kernel.sm

    def executeTc(self, snippet):
        for i, n in enumerate(snippet.nodes):
            # context.tt  << i + 1
            answer = self.ex(n)
            if answer == None: answer = Void
        return answer

    def ex(self, n):
        if isinstance(n, apply):
            # context.tt << f'apply {n}'
            sm = self.sm
            numargs = len(n.argnodes)
            ov = sm.getOverload(n.st, n.fnnode.scope, n.fnnode.name, numargs)
            args = [self.ex(argnode) for argnode in n.argnodes]
            if isinstance(ov, list):
                # the list thing needs sorting out
                ov = ov[numargs]
            if isinstance(ov, Overload):
                if len(ov._fnBySig) == 1:
                    fn = firstValue(ov._fnBySig)
                    if not fn:
                        raise ProgrammerError()
                elif len(ov._fnBySig) > 1:
                    sig = BTTuple(*(a._t for a in args) )
                    fn = ov._fnBySig.get(sig, Missing)
                    if not fn:
                        fn = getFnFromOverload(ov, sig)

                else:
                    raise ProgrammerError()
            else:
                raise ProgrammerError()
            if isinstance(fn, bfunc):
                frame = sm.pushFrame(fn.st)
                for name, arg in zip(fn.argnames, args):
                    sm.bindval(frame.st, LOCAL_SCOPE, name, arg)
                for n2 in fn.body:
                    val = self.ex(n2)
                if (ret := sm.getReturn(frame.st, LOCAL_SCOPE, RET_VAR_NAME)) is Missing: ret = val
                sm.popFrame()
                return ret
            elif isinstance(fn, _Function):
                ret = fn.fn(*(a._v for a in args))
                if hasattr(ret, '_t'):
                    if ret._t:
                        # check the actual return type fits the declared return type
                        if fitsWithin(ret._t, fn.tRet):
                            return ret
                        else:
                            raise BTypeError(f"Return type mismatch: expected {fn.tRet}, got {ret._t}")
                    else:
                        return ret | fn.tRet
                else:
                    # use the coercer rather than impose construction with tv
                    return ret | fn.tRet
            else:
                raise ProgrammerError(f"Unhandled  fn {{{type(fn)}}}")

        elif isinstance(n, bindval):
            # context.tt << f'bindval {n}'
            val = self.ex(n.lhnode)
            self.sm.bindval(n.st, n.scope, n.name, val)
            return val

        elif isinstance(n, getval):
            # context.tt << f'getval {n}'
            return self.sm.getValue(n.st, n.scope, n.name)

        # elif isinstance(n, getoverload):
        #     fnMeta = n.st.fMetaForGet(n.name, n.scope)
        #     return fnMeta.st.getOverload(n.name, n.numargs)

        elif isinstance(n, getfamily):
            # context.tt << f'getfamily {n}'
            fnMeta = n.st.fMetaForGet(n.name, n.scope)
            return fnMeta.st.getOverloadFamily(n.name)

        elif isinstance(n, lit):
            return n

        elif isinstance(n, litstruct):
            return n

        elif isinstance(n, littup):
            return n

        elif isinstance(n, bindfn):
            # unlikely but we could potentially right bind a fn and call it immediately
            return n.fnnode

        elif isinstance(n, (load, fromimport)):
            # these are handled during parsing
            pass

        else:
            raise NotImplementedError(f"Unhandled node {{{n}}}")



def getFnFromOverload(ov, sig):
    # we will have to do a coppertop style multidispatch (i.e. fitswithin with metric)
    # however it should be much simpler
    for s, fn in ov._fnBySig.items():
        match = True
        results = []
        schemaVars = {}
        distance = 0
        for tArg, tSig in zip(sig, fn._tArgs):
            fits = fitsWithin(tArg, tSig)
            if not fits:
                match = False
                break
            schemaVars, distance = updateSchemaVarsWith(schemaVars, distance, fits)
            results.append(fits)
        if match:
            return fn
    raise ProgrammerError()


