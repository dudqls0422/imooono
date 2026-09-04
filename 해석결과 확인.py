"""
구조해석 결과를 캡처하는 코드
"""
import requests
import os
import itertools
import time
import tkinter as tk
from tkinter import messagebox

BaseURL = "https://moa-engineers.midasit.com:443/gen"

# 캡처 저장 경로 (폴더는 미리 생성 필요)
EXPORT_DIR = r"C:\Users\KYB\Desktop\해석결과 캡쳐"
os.makedirs(EXPORT_DIR, exist_ok=True)

# ============ GUI로 입력받을 전역 변수 ============
MAPI_KEY = None
MATERIAL = "STL"      # 기본값: 철골
headers = None         # GUI 입력 후 채워짐


def start_gui():
    """MAPI-Key와 부재 종류(철골/RC)를 입력받는 팝업창"""
    global MAPI_KEY, MATERIAL, headers

    root = tk.Tk()
    root.title("MIDAS 캡처 설정")
    root.geometry("380x260")
    root.resizable(False, False)

    tk.Label(root, text="MAPI-Key 입력", font=("맑은 고딕", 11, "bold")).pack(pady=(20, 5))
    key_entry = tk.Entry(root, width=48, show="")
    key_entry.pack(pady=5)

    tk.Label(root, text="부재 종류 선택", font=("맑은 고딕", 11, "bold")).pack(pady=(20, 5))
    material_var = tk.StringVar(value="STL")

    frame = tk.Frame(root)
    frame.pack(pady=5)
    tk.Radiobutton(frame, text="철골 (STL)", variable=material_var, value="STL",
                   font=("맑은 고딕", 10)).pack(side="left", padx=15)
    tk.Radiobutton(frame, text="RC", variable=material_var, value="RC",
                   font=("맑은 고딕", 10)).pack(side="left", padx=15)

    def on_submit():
        global MAPI_KEY, MATERIAL, headers
        key = key_entry.get().strip()
        if not key:
            messagebox.showwarning("입력 오류", "MAPI-Key를 입력해주세요.")
            return
        MAPI_KEY = key
        MATERIAL = material_var.get()
        headers = {
            "Content-Type": "application/json",
            "MAPI-Key": MAPI_KEY
        }
        root.destroy()

    tk.Button(root, text="확인 및 실행", command=on_submit, width=22,
              bg="#4CAF50", fg="white", font=("맑은 고딕", 10, "bold")).pack(pady=25)

    root.mainloop()


# ============ 캡처 함수들 ============

def MAIN_MODLE(export_path):
    body_CAP = {
        "Argument": {
            "SET_MODE": "pre",
            "SET_HIDDEN": True,
            "EXPORT_PATH": export_path,
            "HEIGHT": 768,
            "WIDTH": 1280,
            "ACTIVE": {"ACTIVE_MODE": "All"},
            "ANGLE": {"HORIZONTAL": 30, "VERTICAL": 25},
            "DISPLAY": {
                "NODE": {"NODE": False, "NODE_NUMBER": False},
                "VIEW": {
                    "UCS_AXIS": False,
                    "VIEWPPORT_GIZMO": False,
                    "VIEW_POINT": False,
                    "DESCRIPTION": "구조해석모델",
                    "LABEL_ORIENTATION": 15
                }
            },
        }
    }
    r = requests.post(BaseURL + "/view/CAPTURE", headers=headers, json=body_CAP)
    print("  CAPTURE:", r.status_code, r.text[:200] if r.text else "")
    return r.status_code == 200


def LOAD_DL_LL(export_path):
    body_UNIT = {
        "Assign": {"1": {"FORCE": "KN", "DIST": "M", "HEAT": "KCAL", "TEMPER": "C"}}
    }
    r1 = requests.put(BaseURL + "/db/UNIT", headers=headers, json=body_UNIT)
    print("  CAPTURE:", r1.status_code, r1.text[:200] if r1.text else "")

    body_CAP = {
        "Argument": {
            "SET_MODE": "pre",
            "SET_HIDDEN": False,
            "EXPORT_PATH": export_path,
            "HEIGHT": 768,
            "WIDTH": 1280,
            "ACTIVE": {"ACTIVE_MODE": "All"},
            "ANGLE": {"HORIZONTAL": 30, "VERTICAL": 25},
            "DISPLAY": {
                "NODE": {"NODE": False, "NODE_NUMBER": False},
                "VIEW": {
                    "UCS_AXIS": False,
                    "VIEWPPORT_GIZMO": False,
                    "VIEW_POINT": False,
                    "DESCRIPTION": "연직방향 하중입력",
                    "LABEL_ORIENTATION": 15
                },
                "LOAD": {
                    "CASE_SELECTION": {"TYPE": "st", "NAME": "DL"},
                    "LOAD_VALUE": {"FORMAT": "Fixed", "PLACE": 1},
                    "FLOOR_LOAD_NAME": True,
                    "NODLA_LOAD": True,
                }
            },
        }
    }
    r2 = requests.post(BaseURL + "/view/CAPTURE", headers=headers, json=body_CAP)
    print("  CAPTURE:", r2.status_code, r2.text[:200] if r2.text else "")
    return r2.status_code == 200


def LOAD_WX(export_path):
    body_CAP = {
        "Argument": {
            "SET_MODE": "pre",
            "SET_HIDDEN": False,
            "EXPORT_PATH": export_path,
            "HEIGHT": 768,
            "WIDTH": 1280,
            "ACTIVE": {"ACTIVE_MODE": "All"},
            "ANGLE": {"HORIZONTAL": 30, "VERTICAL": 25},
            "DISPLAY": {
                "NODE": {"NODE": False, "NODE_NUMBER": False},
                "VIEW": {
                    "UCS_AXIS": False,
                    "VIEWPPORT_GIZMO": False,
                    "VIEW_POINT": False,
                    "DESCRIPTION": "X방향 풍하중입력",
                    "LABEL_ORIENTATION": 15
                },
                "LOAD": {
                    "CASE_SELECTION": {"TYPE": "st", "NAME": "WX"},
                    "LOAD_VALUE": {"FORMAT": "Fixed", "PLACE": 1},
                    "FLOOR_LOAD_NAME": True,
                    "NODLA_LOAD": True,
                }
            },
        }
    }
    r = requests.post(BaseURL + "/view/CAPTURE", headers=headers, json=body_CAP)
    print("  CAPTURE:", r.status_code, r.text[:200] if r.text else "")
    return r.status_code == 200


def LOAD_WY(export_path):
    body_CAP = {
        "Argument": {
            "SET_MODE": "pre",
            "SET_HIDDEN": False,
            "EXPORT_PATH": export_path,
            "HEIGHT": 768,
            "WIDTH": 1280,
            "ACTIVE": {"ACTIVE_MODE": "All"},
            "ANGLE": {"HORIZONTAL": 30, "VERTICAL": 25},
            "DISPLAY": {
                "NODE": {"NODE": False, "NODE_NUMBER": False},
                "VIEW": {
                    "UCS_AXIS": False,
                    "VIEWPPORT_GIZMO": False,
                    "VIEW_POINT": False,
                    "DESCRIPTION": "Y방향 풍하중입력",
                    "LABEL_ORIENTATION": 15
                },
                "LOAD": {
                    "CASE_SELECTION": {"TYPE": "st", "NAME": "WY"},
                    "LOAD_VALUE": {"FORMAT": "Fixed", "PLACE": 1},
                    "FLOOR_LOAD_NAME": True,
                    "NODLA_LOAD": True,
                }
            },
        }
    }
    r = requests.post(BaseURL + "/view/CAPTURE", headers=headers, json=body_CAP)
    print("  CAPTURE:", r.status_code, r.text[:200] if r.text else "")
    return r.status_code == 200


def LOAD_EX(export_path):
    body_CAP = {
        "Argument": {
            "SET_MODE": "pre",
            "SET_HIDDEN": False,
            "EXPORT_PATH": export_path,
            "HEIGHT": 768,
            "WIDTH": 1280,
            "ACTIVE": {"ACTIVE_MODE": "All"},
            "ANGLE": {"HORIZONTAL": 30, "VERTICAL": 25},
            "DISPLAY": {
                "NODE": {"NODE": False, "NODE_NUMBER": False},
                "VIEW": {
                    "UCS_AXIS": False,
                    "VIEWPPORT_GIZMO": False,
                    "VIEW_POINT": False,
                    "DESCRIPTION": "X방향 지진하중입력",
                    "LABEL_ORIENTATION": 15
                },
                "LOAD": {
                    "CASE_SELECTION": {"TYPE": "st", "NAME": "EX"},
                    "LOAD_VALUE": {"FORMAT": "Fixed", "PLACE": 1},
                    "SEISMIC_LOAD": True,
                }
            },
        }
    }
    r = requests.post(BaseURL + "/view/CAPTURE", headers=headers, json=body_CAP)
    print("  CAPTURE:", r.status_code, r.text[:200] if r.text else "")
    return r.status_code == 200


def LOAD_EY(export_path):
    body_CAP = {
        "Argument": {
            "SET_MODE": "pre",
            "SET_HIDDEN": False,
            "EXPORT_PATH": export_path,
            "HEIGHT": 768,
            "WIDTH": 1280,
            "ACTIVE": {"ACTIVE_MODE": "All"},
            "ANGLE": {"HORIZONTAL": 30, "VERTICAL": 25},
            "DISPLAY": {
                "NODE": {"NODE": False, "NODE_NUMBER": False},
                "VIEW": {
                    "UCS_AXIS": False,
                    "VIEWPPORT_GIZMO": False,
                    "VIEW_POINT": False,
                    "DESCRIPTION": "Y방향 지진하중입력",
                    "LABEL_ORIENTATION": 15
                },
                "LOAD": {
                    "CASE_SELECTION": {"TYPE": "st", "NAME": "EY"},
                    "LOAD_VALUE": {"FORMAT": "Fixed", "PLACE": 1},
                    "SEISMIC_LOAD": True,
                }
            },
        }
    }
    r = requests.post(BaseURL + "/view/CAPTURE", headers=headers, json=body_CAP)
    print("  CAPTURE:", r.status_code, r.text[:200] if r.text else "")
    return r.status_code == 200


def DEFORM_DL_LL(export_path):
    body_UNIT = {
        "Assign": {"1": {"FORCE": "KN", "DIST": "MM", "HEAT": "KCAL", "TEMPER": "C"}}
    }
    r1 = requests.put(BaseURL + "/db/UNIT", headers=headers, json=body_UNIT)
    print("  CAPTURE:", r1.status_code, r1.text[:200] if r1.text else "")

    body_COMB = {
        "Assign": {
            "9999": {
                "NO": 9999,
                "NAME": "SER",
                "ACTIVE": "ACTIVE",
                "bCB": False,
                "iTYPE": 0,
                "DESC": "",
                "vCOMB": [
                    {"ANAL": "ST", "LCNAME": "DL", "FACTOR": 1},
                    {"ANAL": "ST", "LCNAME": "LL", "FACTOR": 1}
                ]  
            }
        }
    }
    r2 = requests.put(BaseURL + "/db/LCOM-GEN", headers=headers, json=body_COMB)
    print("  CAPTURE:", r2.status_code, r2.text[:200] if r2.text else "")

    body_CAP = {
        "Argument": {
            "SET_MODE": "post",
            "SET_HIDDEN": False,
            "EXPORT_PATH": export_path,
            "HEIGHT": 768,
            "WIDTH": 1280,
            "ACTIVE": {"ACTIVE_MODE": "All"},
            "ANGLE": {"HORIZONTAL": 30, "VERTICAL": 25},
            "DISPLAY": {
                "NODE": {"NODE": False, "NODE_NUMBER": False},
                "VIEW": {
                    "UCS_AXIS": False,
                    "VIEWPPORT_GIZMO": False,
                    "VIEW_POINT": False,
                    "DESCRIPTION": "연직하중에 의한 변위",
                    "LABEL_ORIENTATION": 15
                },
            },
            "RESULT_GRAPHIC": {
                "CURRENT_MODE": "Displacement Contour",
                "LOAD_CASE_COMB": {
                    "TYPE": "CB", "MINMAX": "ALL", "NAME": "SER",
                    "STEP_INDEX": 1, "TH_OPTION": "Displacement"
                },
                "COMPONENTS": {"COMP": "DXYZ", "OPT_LOCAL_CHECK": False},
                "TYPE_OF_DISPLAY": {
                    "CONTOUR": {"OPT_CHECK": True},
                    "DEFORM": {"OPT_CHECK": True, "SCALE_FACTOR": 1, "REAL_DEFORM": False},
                    "VALUES": {"OPT_CHECK": True},
                    "LEGEND": {"OPT_CHECK": True, "POSITION": "right"}
                },
            }
        },
    }
    r3 = requests.post(BaseURL + "/view/CAPTURE", headers=headers, json=body_CAP)
    print("  CAPTURE:", r3.status_code, r3.text[:200] if r3.text else "")
    return r3.status_code == 200


def DEFORM_WX(export_path):
    body_CAP = {
        "Argument": {
            "SET_MODE": "post",
            "SET_HIDDEN": False,
            "EXPORT_PATH": export_path,
            "HEIGHT": 768,
            "WIDTH": 1280,
            "ACTIVE": {"ACTIVE_MODE": "All"},
            "ANGLE": {"HORIZONTAL": 30, "VERTICAL": 25},
            "DISPLAY": {
                "NODE": {"NODE": False, "NODE_NUMBER": False},
                "VIEW": {
                    "UCS_AXIS": False,
                    "VIEWPPORT_GIZMO": False,
                    "VIEW_POINT": False,
                    "DESCRIPTION": "풍하중에 의한 X방향 변위",
                    "LABEL_ORIENTATION": 15
                },
            },
            "RESULT_GRAPHIC": {
                "CURRENT_MODE": "Displacement Contour",
                "LOAD_CASE_COMB": {
                    "TYPE": "ST", "MINMAX": "ALL", "NAME": "WX",
                    "STEP_INDEX": 1, "TH_OPTION": "Displacement"
                },
                "COMPONENTS": {"COMP": "DXYZ", "OPT_LOCAL_CHECK": False},
                "TYPE_OF_DISPLAY": {
                    "CONTOUR": {"OPT_CHECK": True},
                    "DEFORM": {"OPT_CHECK": True, "SCALE_FACTOR": 1, "REAL_DEFORM": False},
                    "VALUES": {"OPT_CHECK": True},
                    "LEGEND": {"OPT_CHECK": True, "POSITION": "right"}
                },
            }
        },
    }
    r = requests.post(BaseURL + "/view/CAPTURE", headers=headers, json=body_CAP)
    print("  CAPTURE:", r.status_code, r.text[:200] if r.text else "")
    return r.status_code == 200


def DEFORM_WY(export_path):
    body_CAP = {
        "Argument": {
            "SET_MODE": "post",
            "SET_HIDDEN": False,
            "EXPORT_PATH": export_path,
            "HEIGHT": 768,
            "WIDTH": 1280,
            "ACTIVE": {"ACTIVE_MODE": "All"},
            "ANGLE": {"HORIZONTAL": 30, "VERTICAL": 25},
            "DISPLAY": {
                "NODE": {"NODE": False, "NODE_NUMBER": False},
                "VIEW": {
                    "UCS_AXIS": False,
                    "VIEWPPORT_GIZMO": False,
                    "VIEW_POINT": False,
                    "DESCRIPTION": "풍하중에 의한 Y방향 변위",
                    "LABEL_ORIENTATION": 15
                },
            },
            "RESULT_GRAPHIC": {
                "CURRENT_MODE": "Displacement Contour",
                "LOAD_CASE_COMB": {
                    "TYPE": "ST", "MINMAX": "ALL", "NAME": "WY",
                    "STEP_INDEX": 1, "TH_OPTION": "Displacement"
                },
                "COMPONENTS": {"COMP": "DXYZ", "OPT_LOCAL_CHECK": False},
                "TYPE_OF_DISPLAY": {
                    "CONTOUR": {"OPT_CHECK": True},
                    "DEFORM": {"OPT_CHECK": True, "SCALE_FACTOR": 1, "REAL_DEFORM": False},
                    "VALUES": {"OPT_CHECK": True},
                    "LEGEND": {"OPT_CHECK": True, "POSITION": "right"}
                },
            }
        },
    }
    r = requests.post(BaseURL + "/view/CAPTURE", headers=headers, json=body_CAP)
    print("  CAPTURE:", r.status_code, r.text[:200] if r.text else "")
    return r.status_code == 200


def BEAM_DIAGRAMS_M(export_path):
    body_UNIT = {
        "Assign": {"1": {"FORCE": "KN", "DIST": "M", "HEAT": "KCAL", "TEMPER": "C"}}
    }
    r1 = requests.put(BaseURL + "/db/UNIT", headers=headers, json=body_UNIT)
    print("  CAPTURE:", r1.status_code, r1.text[:200] if r1.text else "")

    body_CAP = {
        "Argument": {
            "SET_MODE": "post",
            "SET_HIDDEN": True,
            "EXPORT_PATH": export_path,
            "HEIGHT": 768,
            "WIDTH": 1280,
            "ACTIVE": {"ACTIVE_MODE": "All"},
            "ANGLE": {"HORIZONTAL": 30, "VERTICAL": 25},
            "DISPLAY": {
                "NODE": {"NODE": False, "NODE_NUMBER": False},
                "VIEW": {
                    "UCS_AXIS": False,
                    "VIEWPPORT_GIZMO": False,
                    "VIEW_POINT": False,
                    "DESCRIPTION": "휨모멘트(ENV_STR)",
                    "LABEL_ORIENTATION": 15
                }
            },
            "RESULT_GRAPHIC": {
                "CURRENT_MODE": "BeamDiagrams",
                "LOAD_CASE_COMB": {"TYPE": "CB", "MINMAX": "All", "NAME": f"{MATERIAL} ENV_STR", "OPT_MAXMIN_DIAGRAM": False},
                "COMPONENTS": {"PART": "Total", "COMP": "My"},
                "DISPLAY_OPTIONS": {"FIDELITY": "5Points", "FILL": "Solid", "SCALE": 1},
                "TYPE_OF_DISPLAY": {
                    "CONTOUR": {"OPT_CHECK": True},
                    "LEGEND": {"OPT_CHECK": True, "POSITION": "right"},
                },
            },
        }
    }
    r2 = requests.post(BaseURL + "/view/CAPTURE", headers=headers, json=body_CAP)
    print("  CAPTURE:", r2.status_code, r2.text[:200] if r2.text else "")
    return r2.status_code == 200


def BEAM_DIAGRAMS_S(export_path):
    body_CAP = {
        "Argument": {
            "SET_MODE": "post",
            "SET_HIDDEN": True,
            "EXPORT_PATH": export_path,
            "HEIGHT": 768,
            "WIDTH": 1280,
            "ACTIVE": {"ACTIVE_MODE": "All"},
            "ANGLE": {"HORIZONTAL": 30, "VERTICAL": 25},
            "DISPLAY": {
                "NODE": {"NODE": False, "NODE_NUMBER": False},
                "VIEW": {
                    "UCS_AXIS": False,
                    "VIEWPPORT_GIZMO": False,
                    "VIEW_POINT": False,
                    "DESCRIPTION": "전단력도(ENV_STR)",
                    "LABEL_ORIENTATION": 15
                }
            },
            "RESULT_GRAPHIC": {
                "CURRENT_MODE": "BeamDiagrams",
                "LOAD_CASE_COMB": {"TYPE": "CB", "MINMAX": "All", "NAME": f"{MATERIAL} ENV_STR", "OPT_MAXMIN_DIAGRAM": False},
                "COMPONENTS": {"PART": "Total", "COMP": "Fz"},
                "DISPLAY_OPTIONS": {"FIDELITY": "5Points", "FILL": "Solid", "SCALE": 1},
                "TYPE_OF_DISPLAY": {
                    "CONTOUR": {"OPT_CHECK": True},
                    "LEGEND": {"OPT_CHECK": True, "POSITION": "right"},
                },
            },
        }
    }
    r = requests.post(BaseURL + "/view/CAPTURE", headers=headers, json=body_CAP)
    print("  CAPTURE:", r.status_code, r.text[:200] if r.text else "")
    return r.status_code == 200


def BEAM_DIAGRAMS_F(export_path):
    body_CAP = {
        "Argument": {
            "SET_MODE": "post",
            "SET_HIDDEN": True,
            "EXPORT_PATH": export_path,
            "HEIGHT": 768,
            "WIDTH": 1280,
            "ACTIVE": {"ACTIVE_MODE": "All"},
            "ANGLE": {"HORIZONTAL": 30, "VERTICAL": 25},
            "DISPLAY": {
                "NODE": {"NODE": False, "NODE_NUMBER": False},
                "VIEW": {
                    "UCS_AXIS": False,
                    "VIEWPPORT_GIZMO": False,
                    "VIEW_POINT": False,
                    "DESCRIPTION": "축력도(ENV_STR)",
                    "LABEL_ORIENTATION": 15
                }
            },
            "RESULT_GRAPHIC": {
                "CURRENT_MODE": "BeamDiagrams",
                "LOAD_CASE_COMB": {"TYPE": "CB", "MINMAX": "All", "NAME": f"{MATERIAL} ENV_STR", "OPT_MAXMIN_DIAGRAM": False},
                "COMPONENTS": {"PART": "Total", "COMP": "Fx"},
                "DISPLAY_OPTIONS": {"FIDELITY": "5Points", "FILL": "Solid", "SCALE": 1},
                "TYPE_OF_DISPLAY": {
                    "CONTOUR": {"OPT_CHECK": True},
                    "LEGEND": {"OPT_CHECK": True, "POSITION": "right"},
                },
            },
        }
    }
    r = requests.post(BaseURL + "/view/CAPTURE", headers=headers, json=body_CAP)
    print("  CAPTURE:", r.status_code, r.text[:200] if r.text else "")
    return r.status_code == 200


def TRUSS_FORCE(export_path):
    body_CAP = {
        "Argument": {
            "SET_MODE": "post",
            "SET_HIDDEN": False,
            "EXPORT_PATH": export_path,
            "HEIGHT": 768,
            "WIDTH": 1280,
            "ACTIVE": {"ACTIVE_MODE": "All"},
            "ANGLE": {"HORIZONTAL": 30, "VERTICAL": 25},
            "DISPLAY": {
                "NODE": {"NODE": False, "NODE_NUMBER": False},
                "VIEW": {
                    "UCS_AXIS": False,
                    "VIEWPPORT_GIZMO": False,
                    "VIEW_POINT": False,
                    "DESCRIPTION": "가새 인장력(ENV_STR)",
                    "LABEL_ORIENTATION": 15
                }
            },
            "RESULT_GRAPHIC": {
                "CURRENT_MODE": "TrussForces",
                "LOAD_CASE_COMB": {"TYPE": "CB", "MINMAX": "All", "NAME": f"{MATERIAL} ENV_STR", "STEP_INDEX": 1},
                "COMPONENTS": {"COMP": "Tens."},
                "TYPE_OF_DISPLAY": {
                    "CONTOUR": {"OPT_CHECK": True},
                    "LEGEND": {"OPT_CHECK": True, "POSITION": "right"},
                    "VALUES": {"OPT_CHECK": True,  "DECIMAL_PT": 0}
                },
                "OUTPUT_SECT_LOCATION": {"OPT_I_J_MAX_ALL": "Max"},
            },
        }
    }
    r = requests.post(BaseURL + "/view/CAPTURE", headers=headers, json=body_CAP)
    print("  CAPTURE:", r.status_code, r.text[:200] if r.text else "")
    return r.status_code == 200




def REACTION_FORCES_STR(export_path):
    body_CAP = {
        "Argument": {
            "SET_MODE": "post",
            "SET_HIDDEN": False,
            "EXPORT_PATH": export_path,
            "HEIGHT": 768,
            "WIDTH": 1280,
            "ACTIVE": {"ACTIVE_MODE": "All"},
            "ANGLE": {"HORIZONTAL": 30, "VERTICAL": 25},
            "DISPLAY": {
                "NODE": {"NODE": False, "NODE_NUMBER": False},
                "VIEW": {
                    "UCS_AXIS": False,
                    "VIEWPPORT_GIZMO": False,
                    "VIEW_POINT": False,
                    "DESCRIPTION": "지점반력(ENV_STR)",
                    "LABEL_ORIENTATION": 15
                }
            },
            "RESULT_GRAPHIC": {
                "CURRENT_MODE": "ReactionForces/Moments",
                "LOAD_CASE_COMB": {"TYPE": "CB", "MINMAX": "All", "NAME": f"{MATERIAL} ENV_STR"},
                "COMPONENTS": {"COMP": "Fxyz"},
                "DISPLAY_OPTIONS": {"FIDELITY": "5Points", "FILL": "Solid", "SCALE": 1},
                "TYPE_OF_DISPLAY": {
                    "VALUES": {"OPT_CHECK": True, "ARROW_SCALE_FACTOR": 0.7},
                    "LEGEND": {"OPT_CHECK": True, "POSITION": "right"},
                },
            },
        }
    }
    r = requests.post(BaseURL + "/view/CAPTURE", headers=headers, json=body_CAP)
    print("  CAPTURE:", r.status_code, r.text[:200] if r.text else "")
    return r.status_code == 200


def REACTION_FORCES_SER(export_path):
    body_CAP = {
        "Argument": {
            "SET_MODE": "post",
            "SET_HIDDEN": False,
            "EXPORT_PATH": export_path,
            "HEIGHT": 768,
            "WIDTH": 1280,
            "ACTIVE": {"ACTIVE_MODE": "All"},
            "ANGLE": {"HORIZONTAL": 30, "VERTICAL": 25},
            "DISPLAY": {
                "NODE": {"NODE": False, "NODE_NUMBER": False},
                "VIEW": {
                    "UCS_AXIS": False,
                    "VIEWPPORT_GIZMO": False,
                    "VIEW_POINT": False,
                    "DESCRIPTION": "지점반력(ENV_SER)",
                    "LABEL_ORIENTATION": 15
                }
            },
            "RESULT_GRAPHIC": {
                "CURRENT_MODE": "ReactionForces/Moments",
                "LOAD_CASE_COMB": {"TYPE": "CB", "MINMAX": "All", "NAME": f"{MATERIAL} ENV_SER"},
                "COMPONENTS": {"COMP": "Fxyz"},
                "DISPLAY_OPTIONS": {"FIDELITY": "5Points", "FILL": "Solid", "SCALE": 1},
                "TYPE_OF_DISPLAY": {
                    "VALUES": {"OPT_CHECK": True, "ARROW_SCALE_FACTOR": 0.7},
                    "LEGEND": {"OPT_CHECK": True, "POSITION": "right"},
                },
            },
        }
    }
    r = requests.post(BaseURL + "/view/CAPTURE", headers=headers, json=body_CAP)
    print("  CAPTURE:", r.status_code, r.text[:200] if r.text else "")
    return r.status_code == 200


# ============ 캡쳐 반복 실행 ============

_counter = itertools.count(1)

def next_export_path():
    idx = next(_counter)
    fname = f"model_{idx:03d}.jpg"
    return os.path.join(EXPORT_DIR, fname)

def main():
    steps = [
        MAIN_MODLE,
        LOAD_DL_LL,
        LOAD_WX,
        LOAD_WY,
        LOAD_EX,
        LOAD_EY,
        DEFORM_DL_LL,
        DEFORM_WX,
        DEFORM_WY,
        BEAM_DIAGRAMS_M,
        BEAM_DIAGRAMS_S,
        BEAM_DIAGRAMS_F,
        TRUSS_FORCE,
        REACTION_FORCES_STR,
        REACTION_FORCES_SER,
    ]

    for step in steps:
        export_path = next_export_path()
        step(export_path)

    print("\nDone.")


if __name__ == "__main__":
    start_gui()          # MAPI-Key, 재질 종류 입력받는 창 실행
    if MAPI_KEY:
        main()
    else:
        print("MAPI-Key가 입력되지 않아 종료합니다.")