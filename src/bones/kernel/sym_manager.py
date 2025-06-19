# **********************************************************************************************************************
# Copyright 2025 David Briant, https://github.com/coppertop-bones. Licensed under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance with the License. You may obtain a copy of the  License at
# http://www.apache.org/licenses/LICENSE-2.0. Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY  KIND,
# either express or implied. See the License for the specific language governing permissions and limitations under the
# License. See the NOTICE file distributed with this work for additional information regarding copyright ownership.
# **********************************************************************************************************************

from bones.core.sentinels import Missing


class Sym:
    __slots__ = ['_id', '_st']
    def __init__(self, id, symtab):
        self._id = id
        self._st = symtab
    def __repr__(self):
        return '`%s'%(self._st._strings[self._id])
    def __str__(self):
        return self._st._strings[self._id]
    def __eq__(self, other):
        return self is other
    def __ne__(self, other):
        return self is not other
    def __lt__(self, other):
        return self._st._lt(self, other)
    def __gt__(self, other):
        return self._st._gt(self, other)
    def __le__(self, other):
        return self._st._le(self, other)
    def __ge__(self, other):
        return self._st._ge(self, other)
    def __cmp__(self, other):
        return self._st._cmp(self, other)
    def __hash__(self):
        return self._id


class SymManager:

    def __init__(self):
        self._symByString = {}
        self._syms = []
        self._strings = []
        self._isSorted = False
        self._sortOrder = []
        self._toBeSorted = []

    def Sym(self, string):
        # if it exists return it
        sym = self._symByString.get(string, Missing)
        if sym is not Missing: return sym

        # if it doesn't exist create it, add to the toBeSortedCollection and return it
        sym = Sym(len(self._strings), self)
        self._symByString[string] = sym
        self._strings.append(string)
        self._toBeSorted.append(sym)
        self._isSorted = False
        return sym

    def _sort(self):
        # I can come up with faster ways of doing this for my needs at the moment we'll just do it the easy way
        # e.g. sort the _toBeSorted then merge the two lists, could investigate how to sort large sets of strings
        # e.g. timsort, radix sort, etc
        strings = self._strings
        sortedSyms = sorted(self._syms + self._toBeSorted, key=lambda x:strings[x._id])      # syms is in order of id, i.e. adding order
        num = len(sortedSyms)
        self._sortOrder = [None] * num
        for position, sym in enumerate(sortedSyms):
            self._sortOrder[sym._id] = position
        self._syms.extend(self._toBeSorted)
        self._toBeSorted = []
        self._isSorted = True

    def _lt(self, a, b):
        if not self._isSorted: self._sort()
        return self._sortOrder[a._id] < self._sortOrder[b._id]
    def _gt(self, a, b):
        if not self._isSorted: self._sort()
        return self._sortOrder[a._id] > self._sortOrder[b._id]
    def _le(self, a, b):
        if not self._isSorted: self._sort()
        return self._sortOrder[a._id] <= self._sortOrder[b._id]
    def _ge(self, a, b):
        if not self._isSorted: self._sort()
        return self._sortOrder[a._id] >= self._sortOrder[b._id]
    def _cmp(self, a, b):
        if a is b:
            return 0
        if self._sortOrder[a._id] < self._sortOrder[b._id]:
            return -1
        return 1
