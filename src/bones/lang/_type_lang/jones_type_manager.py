# **********************************************************************************************************************
# Copyright (c) 2025 David Briant. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance
# with the License. You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
# on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
# the specific language governing permissions and limitations under the License.
# **********************************************************************************************************************

import traceback

from bones.core.errors import NotYetImplemented

from bones.lang.core import TLError, bmterr, bmtatm, bmtint, bmtuni, bmttup, bmtstr, bmtrec, bmtseq, bmtmap, bmtfnc, bmtsvr



class JonesTypeManager:

    def onErrRollback(self):
        return OnErrorRollback(self)

    def checkpoint(self):
        pass

    def commit(self):
        pass

    def rollback(self):
        pass

    def __getitem__(self, varname):
        return self._btypeById[self._idByVarname[varname]]

    def atom(self, explicit, spacenode, implicitly, varname):
        raise NotYetImplemented()


class OnErrorRollback:

    def __init__(self, tm):
        self.tm = tm
        self.et = None
        self.ev = None
        self.tb = None

    def __enter__(self):
        self.tm.checkpoint()
        return self

    def __exit__(self, et, ev, tb):
        self.et = et
        self.ev = ev
        self.tb = tb
        if et is None:
            # no exception was raised
            self.tm.commit()
            return True
        else:
            # print the tb to make it easier to figure what happened
            self.tm.rollback()
            traceback.print_tb(tb)
            raise ev
