# **********************************************************************************************************************
# Copyright 2025 David Briant, https://github.com/coppertop-bones. Licensed under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance with the License. You may obtain a copy of the  License at
# http://www.apache.org/licenses/LICENSE-2.0. Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY  KIND,
# either express or implied. See the License for the specific language governing permissions and limitations under the
# License. See the NOTICE file distributed with this work for additional information regarding copyright ownership.
# **********************************************************************************************************************

from bones.core.sentinels import Missing



class StackManager:
    __slots__ = ('stack', 'current', '_next')
    def __init__(self):
        self.stack = [Missing] * 1000
        self.current = Missing
        self._next = 0
    def push(self, numslots):
        if (self._next + numslots) >= len(self.stack):
            self.stack.extend([Missing] * 1000)


class bframe:
    def __init__(self, symtab, parent):
        self.symtab = symtab
        self.parent = parent
        self.values = {}

    def __setitem__(self, key, value):
        self.values[key] = value

    def __getitem__(self, key):
        return self.values[key]

    def __contains__(self, key):
        return key in self.values

    @property
    def depth(self):
        return self.parent.depth + 1 if self.parent else 1

    def __repr__(self):
        return f'bframe: [{self.depth}]{self.symtab.path}'


class blockframe:
    def __init__(self, symtab, parentFrame, argnames, lexicalParent):
        self.symtab = symtab
        self.parent = parentFrame
        self.lexicalParent = lexicalParent
        self.values = {}

    def __setitem__(self, key, value):
        if key in self.values:
            raise RuntimeError(f'Not allowed to rebind argument {key} in block {self.symtab.path}')
        if key not in self.lexicalParent.values:
            raise RuntimeError(f'Not allowed to bind new name "{key}" in parent {self.parent.symtab.path}')
        self.parent.values[key] = value

    def __getitem__(self, key):
        if (v := self.values.get(key, Missing)) is Missing:
            v = self.parent.values[key]
        return v

    def __contains__(self, key):
        return key in self.values

    @property
    def depth(self):
        return self.parent.depth + 1 if self.parent else 1

    def __repr__(self):
        return f'bframe: [{self.depth}]{self.symtab.path}'