"""풍/지진 적용조건 추출 → ``하중조건`` 시트용 행 리스트.

값 출처: 직접입력 / API조회 / 간접 / 미지원 / 미조회
"""
from __future__ import annotations

from typing import Dict, List

SRC_DIRECT = "직접입력"
SRC_API = "API조회"
SRC_INDIRECT = "간접"
SRC_UNSUPPORTED = "미지원"
SRC_NOTREAD = "미조회"

WIND_COLS = ["케이스ID", "케이스명", "기준코드", "기본풍속 Vo", "지표면조도구분",
             "지형계수/노풍도", "중요도계수 Iw", "가스트영향계수 Gf", "기준높이",
             "설계속도압", "풍력/풍압계수", "적용방향", "값 출처"]

SEIS_COLS = ["케이스ID", "케이스명", "기준코드", "해석법", "지역/지역계수",
             "유효지반가속도 EPA", "지반종류", "중요도계수", "반응수정계수 R",
             "근사주기 T", "우발편심(%)", "응답스펙트럼 함수명", "감쇠비",
             "적용방향", "값 출처"]

_EXP_CAT = {0: "A", 1: "B", 2: "C", 3: "D"}
_SITE_CLASS = {0: "S1", 1: "S2", 2: "S3", 3: "S4", 4: "S5", 5: "S6"}


def _num(v, nd=4):
    try:
        f = float(v)
        return round(f, nd) if f != int(f) else int(f)
    except (TypeError, ValueError):
        return v


def _wind_pressure_summary(prof):
    if not isinstance(prof, dict):
        return ""
    vals = []
    for dirk in ("X_DIR", "Y_DIR"):
        rows = prof.get(dirk) or []
        ps = [float(r.get("PRESSURE", 0) or 0) for r in rows if isinstance(r, dict)]
        ps = [p for p in ps if p > 0]
        if ps:
            vals.append(f"{dirk}: {min(ps):.3g}~{max(ps):.3g}")
    return " / ".join(vals)


def extract_wind(ctx) -> List[Dict]:
    rows: List[Dict] = []
    if ctx.swind:
        for cid, w in ctx.swind.items():
            p = w.get("PARAMETERS", {}) or {}
            topo = p.get("TOPOGRAPHIC_EFFECT", {}) or {}
            rows.append({
                "케이스ID": cid,
                "케이스명": w.get("DESC") or w.get("WIND_CODE") or f"SWIND {cid}",
                "기준코드": w.get("WIND_CODE") or p.get("WIND_CODE") or "",
                "기본풍속 Vo": _num(p.get("WIND_SPEED")),
                "지표면조도구분": _EXP_CAT.get(p.get("EXP_CATEGORY"), p.get("EXP_CATEGORY")),
                "지형계수/노풍도": ("사용" if topo.get("OPT_USE") else "미사용")
                + (f" KZT={_num(p.get('KZT'))}" if topo.get("OPT_USE") else ""),
                "중요도계수 Iw": _num(p.get("IMPORTANCE_FACTOR")),
                "가스트영향계수 Gf": f"X={_num(p.get('GUST_FACTOR_X'))}, "
                                  f"Y={_num(p.get('GUST_FACTOR_Y'))}",
                "기준높이": _num(p.get("ROOF_HEIGHT")),
                "설계속도압": _wind_pressure_summary(w.get("PROFILE", {})),
                "풍력/풍압계수": ("사용자입력"
                              if (p.get("FORCE_COEF", {}) or {}).get("OPT_USE")
                              else "자동"),
                "적용방향": "+".join(
                    d for d in ("X", "Y")
                    if (w.get("PROFILE", {}) or {}).get(f"{d}_DIR")),
                "값 출처": SRC_API,
            })
        return rows

    wind_cases = [c for c in ctx.stld.values()
                  if str(c.get("TYPE", "")).upper() in ("W", "WA", "WX", "WY")]
    if not wind_cases and not ctx.stor:
        return rows
    story_w = ""
    if ctx.stor:
        wx = [float(s.get("WIND_FLOOR_WIDTH_X", 0) or 0) for s in ctx.stor.values()]
        ex = [float(s.get("WIND_ECCENT_X", 0) or 0) for s in ctx.stor.values()]
        if wx:
            story_w = (f"층별 풍 폭_X {min(wx):.3g}~{max(wx):.3g}, "
                       f"편심_X {min(ex):.3g}~{max(ex):.3g}")
    for c in (wind_cases or [{"NO": "-", "NAME": "(케이스 없음)"}]):
        rows.append({
            "케이스ID": c.get("NO", "-"), "케이스명": c.get("NAME", ""),
            "기준코드": SRC_NOTREAD, "기본풍속 Vo": SRC_NOTREAD,
            "지표면조도구분": SRC_NOTREAD, "지형계수/노풍도": SRC_NOTREAD,
            "중요도계수 Iw": SRC_NOTREAD, "가스트영향계수 Gf": SRC_NOTREAD,
            "기준높이": SRC_NOTREAD, "설계속도압": SRC_NOTREAD,
            "풍력/풍압계수": SRC_NOTREAD, "적용방향": SRC_NOTREAD,
            "값 출처": f"{SRC_INDIRECT} / 직접 조회 실패 ({story_w})",
        })
    return rows


def _spfc_by_name(ctx):
    return {str(v["NAME"]): v for v in ctx.spfc.values() if v.get("NAME")}


def extract_seismic(ctx) -> List[Dict]:
    rows: List[Dict] = []
    spfc = _spfc_by_name(ctx)

    for cid, s in ctx.sseis.items():
        p = s.get("PARAMETERS", {}) or {}
        rx, ry = p.get("RESPONSE_MOD_FACTOR_X"), p.get("RESPONSE_MOD_FACTOR_Y")
        # 정적(ESA) 지진의 R 은 SSEIS.PARAMETERS.RESPONSE_MOD_FACTOR_X/Y 만 사용한다.
        # SPFC.VAL.R_ 는 응답스펙트럼(RS) 함수의 R 이므로 정적 행에 붙이지 않는다.
        r_txt = f"X={_num(rx)}, Y={_num(ry)}"
        rows.append({
            "케이스ID": cid,
            "케이스명": s.get("DESC") or s.get("SEIS_CODE") or f"SSEIS {cid}",
            "기준코드": s.get("SEIS_CODE", ""),
            "해석법": "정적(ESA)",
            "지역/지역계수": f"Zone={p.get('SEIS_ZONE')}"
            + (f", Sds={_num(p.get('SDS'))}, Sd1={_num(p.get('SD1'))}"
               if p.get("SDS") is not None else ""),
            "유효지반가속도 EPA": _num(p.get("EPA")),
            "지반종류": _SITE_CLASS.get(p.get("SITE_CLASS"), p.get("SITE_CLASS")),
            "중요도계수": _num(p.get("IMPORTANCE_FACTOR")),
            "반응수정계수 R": r_txt,
            "근사주기 T": (f"근사 X={_num(p.get('PERIOD_APPR_X'))}, "
                        f"Y={_num(p.get('PERIOD_APPR_Y'))}"
                        if p.get("PERIOD_METHOD") == 1
                        else f"해석 X={_num(p.get('PERIOD_ANALYSIS_X'))}, "
                             f"Y={_num(p.get('PERIOD_ANALYSIS_Y'))}"),
            "우발편심(%)": ("5 (우발비틀림 적용)" if s.get("ACCIDENT_TORSION") else "0"),
            "응답스펙트럼 함수명": "-",
            "감쇠비": SRC_UNSUPPORTED,
            "적용방향": "+".join(d for d, k in (("X", "SCALE_FACTOR_X"),
                                              ("Y", "SCALE_FACTOR_Y"))
                              if float(s.get(k, 0) or 0) != 0),
            "값 출처": SRC_API,
        })

    for cid, sp in ctx.splc.items():
        funcs = sp.get("aFUNCNAME", []) or []
        _ecc = sp.get("ACCECC_PERTCENT")
        ecc_txt = (_num(_ecc) if sp.get("bACCECC") and _ecc is not None
                   else "0")
        damp = SRC_UNSUPPORTED
        for fn in funcs:
            f = spfc.get(str(fn))
            if f and f.get("DRATIO") is not None:
                damp = f"{_num(f.get('DRATIO'))} ({SRC_API})"
                break
        f0 = spfc.get(str(funcs[0])) if funcs else None
        val = ((f0 or {}).get("VAL", {})) or {}
        opt = ((f0 or {}).get("OPT", {})) or {}
        rows.append({
            "케이스ID": cid,
            "케이스명": sp.get("NAME", f"SPLC {cid}"),
            "기준코드": ", ".join(funcs) or ((f0 or {}).get("DESC", "")),
            "해석법": f"응답스펙트럼(RSA, {sp.get('COMTYPE', '')})",
            "지역/지역계수": (f"ZoneFactor={_num(val.get('ZONEFACTOR'))}"
                         if val.get("ZONEFACTOR") is not None else "-"),
            "유효지반가속도 EPA": (_num(val.get("ZONEFACTOR"))
                            if val.get("ZONEFACTOR") is not None else "-"),
            "지반종류": _SITE_CLASS.get(opt.get("SC_"), opt.get("SC_", "-")),
            "중요도계수": _num(val.get("IE")) if val.get("IE") is not None else "-",
            "반응수정계수 R": _num(val.get("R_")) if val.get("R_") is not None else "-",
            "근사주기 T": "-",
            "우발편심(%)": ecc_txt,
            "응답스펙트럼 함수명": ", ".join(funcs) or "-",
            "감쇠비": damp,
            "적용방향": sp.get("DIR", "-"),
            "값 출처": SRC_API,
        })
    return rows
