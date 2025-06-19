# **********************************************************************************************************************
# Copyright 2025 David Briant, https://github.com/coppertop-bones. Licensed under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance with the License. You may obtain a copy of the  License at
# http://www.apache.org/licenses/LICENSE-2.0. Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY  KIND,
# either express or implied. See the License for the specific language governing permissions and limitations under the
# License. See the NOTICE file distributed with this work for additional information regarding copyright ownership.
# **********************************************************************************************************************

from bones.core.sentinels import Missing


class CodeManager:
    __slots__ = ('fns', '_next')
    def __init__(self):
        self.fns = [Missing] * 1000
        self._next = 0
    def reserve(self):
        if self.next >= len(self.fns):
            self.fns.extend([Missing] * 1000)
        offset = self._next
        self._next += 1
        return offset


