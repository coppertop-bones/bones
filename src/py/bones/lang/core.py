# **********************************************************************************************************************
# Copyright (c) 2022 David Briant. All rights reserved.
# This file is part of py-bones. For licensing contact David Briant.
# **********************************************************************************************************************

LOCAL_SCOPE = 1       # e.g. fred - r/w - may be polymorphic
PARENT_SCOPE = 2      # e.g. .fred - r/o
MODULE_SCOPE = 3      # e.g. ..MAX_ITER - r/o
CONTEXT_SCOPE = 4     # e.g. _.fred - r/w - fully typed as it may be confusing to type on first usage
GLOBAL_SCOPE = 5      # e.g. _..fred - r/w - fully typed as it may be confusing to type on first usage

GLOBAL = 'global'
SCRATCH = 'scratch'

RET_VAR_NAME = "__RET__"
MAX_NUM_ARGS = 10
