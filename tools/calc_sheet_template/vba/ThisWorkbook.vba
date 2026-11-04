' ThisWorkbook 코드 모듈 (build_template.py 가 AddFromString 으로 넣습니다)
Option Explicit

Private Sub Workbook_Open()
    HeaderSync.UpdateHeaders
End Sub

Private Sub Workbook_BeforePrint(Cancel As Boolean)
    HeaderSync.UpdateHeaders
End Sub
