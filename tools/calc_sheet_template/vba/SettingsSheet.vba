' "설정" 시트 코드 모듈 (build_template.py 가 AddFromString 으로 넣습니다)
Option Explicit

Private Sub Worksheet_Change(ByVal Target As Range)
    Dim watched As Range
    Set watched = Union(ThisWorkbook.Names("PROJECT_NAME").RefersToRange, _
                        ThisWorkbook.Names("DOC_DATE").RefersToRange)
    If Not Intersect(Target, watched) Is Nothing Then HeaderSync.UpdateHeaders
End Sub
