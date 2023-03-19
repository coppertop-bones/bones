# **********************************************************************************************************************
# Copyright (c) 2022 David Briant. All rights reserved.
# This file is part of py-bones. For licensing contact David Briant.
# **********************************************************************************************************************

from coppertop.pipe import _Function
from bones.lang.tc import load, fromimport, bindval, apply, getval, bfunc, lit, bindfn, getfamily, getoverload, litstruct, littup
from bones.lang.core import LOCAL_SCOPE, RET_VAR_NAME
from bones.lang.ctx import Overload
from bones.core.sentinels import Missing, Void
from bones.core.errors import NotYetImplemented, ProgrammerError
from bones.core.utils import firstValue
from bones.lang.metatypes import BTTuple, cacheAndUpdate, fitsWithin
from bones.lang.structs import tv
from bones.core.context import context

# implements stepping and pure execution interfaces



def stepTc(tc, ctx, stepState):
    raise NotYetImplemented()

def executeBc(bc, ctx):
    raise NotYetImplemented()

def stepBc(bc, ctx, stepState):
    raise NotYetImplemented()



class TCInterpreter(object):

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
            ov = sm.getOverload(n.ctx, n.fnnode.scope, n.fnnode.name, numargs)
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
                frame = sm.pushFrame(fn.ctx)
                for name, arg in zip(fn.argnames, args):
                    sm.bindval(frame.ctx, LOCAL_SCOPE, name, arg)
                for n2 in fn.body:
                    val = self.ex(n2)
                if (ret := sm.getReturn(frame.ctx, LOCAL_SCOPE, RET_VAR_NAME)) is Missing: ret = val
                sm.popFrame()
                return ret
            elif isinstance(fn, _Function):
                ret = fn.fn(*(a._v for a in args))
                return tv(fn.tRet, ret)
            else:
                raise ProgrammerError(f"Unhandled  fn {{{type(fn)}}}")

        elif isinstance(n, bindval):
            # context.tt << f'bindval {n}'
            val = self.ex(n.lhnode)
            self.sm.bindval(n.ctx, n.scope, n.name, val)
            return val

        elif isinstance(n, getval):
            # context.tt << f'getval {n}'
            return self.sm.getValue(n.ctx, n.scope, n.name)

        # elif isinstance(n, getoverload):
        #     fnMeta = n.ctx.fMetaForGet(n.name, n.scope)
        #     return fnMeta.ctx.getOverload(n.name, n.numargs)

        elif isinstance(n, getfamily):
            # context.tt << f'getfamily {n}'
            fnMeta = n.ctx.fMetaForGet(n.name, n.scope)
            return fnMeta.ctx.getOverloadFamily(n.name)

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
        argDistances = []
        tByT = {}
        for tArg, tSig in zip(sig, fn._tArgs):
            doesFit, tByTLocal, argDistance = cacheAndUpdate(fitsWithin(tArg, tSig, False), tByT, 0)
            if not doesFit:
                match = False
                break
            tByT = tByTLocal
            argDistances.append(argDistance)
        if match:
            return fn
    raise ProgrammerError()


