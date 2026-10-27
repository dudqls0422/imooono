"""시트별 작도 함수 모음. BUILDERS[시트ID](canvas, spec) 로 호출한다."""
from __future__ import annotations

from .c1_capstone import BUILDERS as _C1
from .m1_draw import BUILDERS as _M1
from .m2_modify import BUILDERS as _M2

BUILDERS = {**_M1, **_M2, **_C1}
