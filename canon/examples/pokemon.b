

// https://www.moll.dev/projects/effective-multi-dispatch/
// https://news.ycombinator.com/item?id=27901244

NO_EFFECT:          0.0
NOT_VERY_EFFECTIVE: 0.5
NORMAL_EFFECTIVE:   1.0
SUPER_EFFECTIVE:    2.0

<:Pokestyle:>                           // ensures the atom Pokestyle exists

<:Fire:     Pokestyle & _Fire>          // ensures _Fire as well as Fire exists
<:Water:    Pokestyle & _Water>
<:Electric: Pokestyle & _Electric>
<:Grass:    Pokestyle & _Grass>
<:Ice:      Pokestyle & _Ice>
<:Fighting: Pokestyle & _Fighting>
<:Poison:   Pokestyle & _Poison>
<:Ground:   Pokestyle & _Ground>

eff: {[atk:Pokestyle & T1, def:Pokestyle & T2]  ..NORMAL_EFFECTIVE}     // T1 and T2 are residuals of decomposition

eff: {[atk:Fire,     def:Grass]     ..SUPER_EFFECTIVE}                  // .. is for accessing a module level variable
eff: {[atk:Fire,     def:Ice]       ..SUPER_EFFECTIVE}
eff: {[atk:Water,    def:Fire]      ..SUPER_EFFECTIVE}
eff: {[atk:Water,    def:Ground]    ..SUPER_EFFECTIVE}
eff: {[atk:Electric, def:Water]     ..SUPER_EFFECTIVE}
eff: {[atk:Grass,    def:Water]     ..SUPER_EFFECTIVE}
eff: {[atk:Grass,    def:Ground]    ..SUPER_EFFECTIVE}
eff: {[atk:Ice,      def:Grass]     ..SUPER_EFFECTIVE}
eff: {[atk:Ice,      def:Ground]    ..SUPER_EFFECTIVE}
eff: {[atk:Fighting, def:Normal]    ..SUPER_EFFECTIVE}
eff: {[atk:Fighting, def:Ice]       ..SUPER_EFFECTIVE}
eff: {[atk:Poison,   def:Grass]     ..SUPER_EFFECTIVE}
eff: {[atk:Ground,   def:Fire]      ..SUPER_EFFECTIVE}
eff: {[atk:Ground,   def:Electric]  ..SUPER_EFFECTIVE}
eff: {[atk:Ground,   def:Poison]    ..SUPER_EFFECTIVE}

eff: {[atk:Fire,     def:Water]     ..NOT_VERY_EFFECTIVE}
eff: {[atk:Water,    def:Grass]     ..NOT_VERY_EFFECTIVE}
eff: {[atk:Electric, def:Grass]     ..NOT_VERY_EFFECTIVE}
eff: {[atk:Grass,    def:Fire]      ..NOT_VERY_EFFECTIVE}
eff: {[atk:Grass,    def:Poison]    ..NOT_VERY_EFFECTIVE}
eff: {[atk:Ice,      def:Fire]      ..NOT_VERY_EFFECTIVE}
eff: {[atk:Ice,      def:Water]     ..NOT_VERY_EFFECTIVE}
eff: {[atk:Fighting, def:Poison]    ..NOT_VERY_EFFECTIVE}
eff: {[atk:Poison,   def:Ground]    ..NOT_VERY_EFFECTIVE}
eff: {[atk:Ground,   def:Grass]     ..NOT_VERY_EFFECTIVE}

eff: {[atk:Electric, def:Ground]    ..NO_EFFECT}


// adding the new type
<:Flying:   Pokestyle & _Flying>

// cases where where Flying is on defence
eff: {[atk:Electric, def:Flying]    ..SUPER_EFFECTIVE}
eff: {[atk:Grass,    def:Flying]    ..NOT_VERY_EFFECTIVE}
eff: {[atk:Ice,      def:Flying]    ..SUPER_EFFECTIVE}
eff: {[atk:Fighting, def:Flying]    ..NOT_VERY_EFFECTIVE}
eff: {[atk:Ground,   def:Flying]    ..NO_EFFECT}

// cases where Flying is attacking
eff: {[atk:Flying, def:Electric]    ..NOT_VERY_EFFECTIVE}
eff: {[atk:Flying, def:Grass]       ..SUPER_EFFECTIVE}
eff: {[atk:Flying, def:Fighting]    ..SUPER_EFFECTIVE}

// self-to-self case, apparently birds can't attack one another :/
eff: {[atk:Flying, def:Flying]      ..NO_EFFECT}

