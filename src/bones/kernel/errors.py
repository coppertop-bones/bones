# **********************************************************************************************************************
# Copyright 2025 David Briant, https://github.com/coppertop-bones. Licensed under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance with the License. You may obtain a copy of the  License at
# http://www.apache.org/licenses/LICENSE-2.0. Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY  KIND,
# either express or implied. See the License for the specific language governing permissions and limitations under the
# License. See the NOTICE file distributed with this work for additional information regarding copyright ownership.
# **********************************************************************************************************************

from bones.core.sentinels import Missing
from bones.core.errors import handlersByErrSiteId, CPTBError


class BonesProvenanceError(CPTBError): pass

class BonesError(CPTBError):
    def __init__(self, msg, errSite):
        super().__init__(msg)
        self._site = errSite
        if (desc := handlersByErrSiteId.get(errSite.id, Missing)) is Missing:
            print(f'Unknown ErrSiteId - {errSite.id}')
            raise BonesProvenanceError()
        elif desc.endswith('...'):
            pass
            # print(f'{errSite.id} needs work:')
            # print(desc)

class BonesLexError(BonesError): pass                       # ne spelling error

class BonesGroupingError(BonesError):
    def __init__(self, msg, errSite, group, token):
        super().__init__(msg, errSite)
        self._group = group
        self._token = token

class BonesPhraseError(BonesError): pass                    # ne sentence error

class BonesIncompatibleTypesError(BonesError): pass         # ne grammar error

class BonesUnknownNameError(BonesError): pass               # ne dictionary error

class BonesAmbiguousOverloadError(BonesError): pass

class BonesUnknownOverloadError(BonesError): pass

class BonesModuleLoadError(BonesError): pass                # load tool.kit

class BonesModuleImportError(BonesError): pass              # e.g. from tools.bag import x - x doesn't exist

class BonesScopeAccessError(BonesError): pass               # e.g. trying to get from or set in the wrong scope
