# **********************************************************************************************************************
# Copyright 2025 David Briant, https://github.com/coppertop-bones. Licensed under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance with the License. You may obtain a copy of the  License at
# http://www.apache.org/licenses/LICENSE-2.0. Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY  KIND,
# either express or implied. See the License for the specific language governing permissions and limitations under the
# License. See the NOTICE file distributed with this work for additional information regarding copyright ownership.
# **********************************************************************************************************************

GLOBAL_CTX = 'global'
SCRATCH_CTX = 'scratch'

RET_VAR_NAME = "__RET__"

LOCAL_SCOPE = 1       # e.g. fred - r/w - may be polymorphic
PARENT_SCOPE = 2      # e.g. .fred - r/o
MODULE_SCOPE = 3      # e.g. ..MAX_ITER - r/o
CONTEXT_SCOPE = 4     # e.g. _.fred - r/w - fully typed as it may be confusing to type on first usage
GLOBAL_SCOPE = 5      # e.g. _..fred - r/w - fully typed as it may be confusing to type on first usage

MAX_NUM_ARGS = 10
