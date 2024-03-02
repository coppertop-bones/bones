
# define:
# u8
# index
# count
# ascii
# bool
#
# +
# *
# -
# /
# **
# ==
# !=
#
# check (T1, (T1*T2)^bool
# equals (T1, T2) -> bool, (N**T1, N**T2) -> bool
# both (N**T1, N**T1) -> N**T1
# collect (N**T1, T1^T2) -> N**T2
# select (N**T1, T1^bool) -> N**T1
# ifTrue (bool, ()^T1) -> T1
# ifFalse (bool, ()^T1) -> T1
# ifTrue:ifFalse: (bool, ()^T1, ()^T2) -> T1+T2
# if(bool, ()^T1) -> T1, if(bool, ()^T1, ()^T2) -> T1+T2
# do (N**T1, T1^T2) -> N**T2+void
#
# __atOrdinal__ (N**T1, index) -> T1
# __atKey__ (T1**T2, T1) -> T2
