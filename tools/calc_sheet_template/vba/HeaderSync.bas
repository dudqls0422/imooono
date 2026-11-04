Attribute VB_Name = "HeaderSync"
Option Explicit

' 구조계산서 양식 - 머리글 자동 반영
'
' "설정" 시트의 PROJECT_NAME / DOC_DATE 값을 읽어, 설정 시트를 뺀 모든 시트의
' 오른쪽 머리글(프로젝트명 / 작성일 / 페이지 번호)을 다시 쓰고 가운데 머리글은 비웁니다.
' 왼쪽 머리글(&G = 로고 + 문서명 합성 이미지)과 바닥글 이미지는 건드리지 않습니다.
'
' 원본은 tools/calc_sheet_template/vba/HeaderSync.bas (UTF-8) 입니다.
' build_template.py 가 아래 실측 상수를 그 PC 의 PDF 실측값으로 바꾼 뒤,
' 시스템 ANSI 코드페이지로 바꿔서 통합 문서에 가져옵니다.

Private Const DATE_LABEL As String = "작성일 : "

' 글꼴 크기 코드(&9 등)를 글꼴 이름 코드보다 먼저 둡니다.
' 글꼴 이름 코드는 따옴표로 끝나므로, 뒤에 오는 프로젝트명이 숫자로 시작해도
' "&9" + "123" 이 "&9123" 처럼 크기 코드로 잘못 읽히지 않습니다.
Private Const CODE_BOLD As String = "&""맑은 고딕,Bold"""
Private Const CODE_DATE_LINE As String = "&8&""맑은 고딕,Regular"""

' ---- build 가 PDF 실측으로 바꿔 넣는 값 (아래는 개발 PC 실측값) ----
' 프로젝트명이 들어갈 폭(머리글 이미지 오른쪽 끝 + 3mm ~ 오른쪽 끝)에 들어가는 "가중 글자 수" 경계.
' 가중 글자 수 = 한글 등 전각 글자 1, 영문·숫자·공백·기호 ASCII_WEIGHT.
Private Const CAP_9PT As Double = 28.90
Private Const CAP_8PT As Double = 32.50
Private Const CAP_7PT As Double = 37.60
Private Const ASCII_WEIGHT As Double = 0.55

' Excel 머리글 문자열 길이 제한: "&L(왼쪽)&C(가운데)&R(오른쪽)" 전체가 서식 코드 포함 255자 이하.
' Excel 2013 실측: 전체 256자부터는 오류 없이 구역이 뒤섞여 왼쪽 로고(&G)까지 지워지고,
' 한 구역이 255자를 넘으면 설정이 거부된다.
Private Const MAX_HEADER_LEN As Long = 255
Private Const LEFT_HEADER As String = "&G"
Private Const ELLIPSIS As String = "…"
Private Const MAX_DATE_TEXT As Long = 30

Public Sub UpdateHeaders()
    Dim settingsWs As Worksheet
    Dim projectName As String
    Dim dateText As String
    Dim rightText As String

    Set settingsWs = ThisWorkbook.Names("PROJECT_NAME").RefersToRange.Worksheet
    projectName = CellText(ThisWorkbook.Names("PROJECT_NAME").RefersToRange.Value)
    dateText = FormatDocDate(ThisWorkbook.Names("DOC_DATE").RefersToRange.Value)

    rightText = BuildRightHeader(projectName, dateText, _
        MAX_HEADER_LEN - Len("&L" & LEFT_HEADER & "&C" & "&R"))

    ' 머리글 텍스트는 PrintCommunication=True 상태에서 바로 넣는다(Plan 승인 우회).
    ' 실측(Excel 2013): PrintCommunication=False 로 모아서 반영하면, 전체 255자 안에 들어가는
    ' 긴 한글 머리글도 거부했다(오류 1004 "RightHeader 속성을 설정할 수 없습니다").
    If Not Application.PrintCommunication Then Application.PrintCommunication = True
    ApplyHeaders settingsWs, rightText
End Sub

Private Sub ApplyHeaders(ByVal settingsWs As Worksheet, ByVal rightText As String)
    Dim ws As Worksheet
    For Each ws In ThisWorkbook.Worksheets
        If Not ws Is settingsWs Then
            ws.PageSetup.CenterHeader = ""
            ws.PageSetup.RightHeader = rightText
        End If
    Next ws
End Sub

' 오른쪽 머리글: 1행 프로젝트명(굵게, 길이에 따라 9 → 8 → 7pt) / 2행 "작성일 : yyyy.mm.dd   n / N"(8pt).
' 작성일이 비어 있으면 2행은 페이지 번호만.
' 7pt 로도 폭을 넘거나 budget(머리글 전체 255자 중 남은 글자 수)을 넘으면 프로젝트명 끝을 잘라 "…" 를 붙인다.
Public Function BuildRightHeader(ByVal projectName As String, ByVal dateText As String, _
                                 ByVal budget As Long) As String
    Dim tail As String
    Dim p As String
    Dim s As String
    Dim size As Long
    Dim cut As Boolean

    If Len(dateText) > MAX_DATE_TEXT Then dateText = Left$(dateText, MAX_DATE_TEXT - 1) & ELLIPSIS
    tail = vbLf & CODE_DATE_LINE
    If Len(dateText) > 0 Then tail = tail & DATE_LABEL & EscapeHeader(dateText) & "   "
    tail = tail & "&P / &N"

    p = SingleLine(projectName)
    size = ProjectFontSize(WeightedLen(p))
    If size = 0 Then
        size = 7
        cut = True
        Do While Len(p) > 0 And WeightedLen(RTrim$(p)) + 1 > CAP_7PT
            p = Left$(p, Len(p) - 1)
        Loop
    End If

    s = ProjectLine(size, p, cut) & tail
    Do While Len(s) > budget And Len(p) > 0
        p = Left$(p, Len(p) - 1)
        cut = True
        s = ProjectLine(size, p, cut) & tail
    Loop
    BuildRightHeader = s
End Function

Private Function ProjectLine(ByVal size As Long, ByVal p As String, ByVal cut As Boolean) As String
    If cut Then p = RTrim$(p) & ELLIPSIS
    ProjectLine = "&" & size & CODE_BOLD & EscapeHeader(p)
End Function

' 가중 글자 수에 맞는 프로젝트명 글꼴 크기. 7pt 로도 넘으면 0.
Public Function ProjectFontSize(ByVal weighted As Double) As Long
    If weighted <= CAP_9PT Then
        ProjectFontSize = 9
    ElseIf weighted <= CAP_8PT Then
        ProjectFontSize = 8
    ElseIf weighted <= CAP_7PT Then
        ProjectFontSize = 7
    Else
        ProjectFontSize = 0
    End If
End Function

' 가중 글자 수: 한글·한자 등 전각(U+1100 이상)은 1, 그 밖의 영문·숫자·공백·기호는 ASCII_WEIGHT.
' (잘라서 붙이는 "…" 은 BuildRightHeader 에서 1 로 따로 더한다)
Public Function WeightedLen(ByVal s As String) As Double
    Dim i As Long
    Dim c As Long
    For i = 1 To Len(s)
        c = AscW(Mid$(s, i, 1)) And &HFFFF&
        If c >= &H1100& Then
            WeightedLen = WeightedLen + 1
        Else
            WeightedLen = WeightedLen + ASCII_WEIGHT
        End If
    Next i
End Function

' 셀 안 줄바꿈은 공백으로 (머리글 줄 수가 늘어 본문과 겹치는 것을 막음)
Private Function SingleLine(ByVal s As String) As String
    s = Replace(s, vbCrLf, " ")
    s = Replace(s, vbCr, " ")
    SingleLine = Replace(s, vbLf, " ")
End Function

' 머리글 코드 문자 '&' 를 '&&' 로 바꾸고, 줄바꿈은 공백으로 바꿉니다.
Public Function EscapeHeader(ByVal s As String) As String
    EscapeHeader = Replace(SingleLine(s), "&", "&&")
End Function

' 작성일 셀 값을 yyyy.mm.dd 로 바꿉니다.
' 비어 있으면 빈 문자열(작성일 부분을 빼고 페이지 번호만 표시),
' 날짜가 아닌 글자로 적혀 있으면 적힌 그대로 씁니다.
Public Function FormatDocDate(ByVal v As Variant) As String
    If IsEmpty(v) Or IsError(v) Then Exit Function
    If VarType(v) = vbDate Then
        FormatDocDate = Year(v) & "." & Right$("0" & Month(v), 2) & "." & Right$("0" & Day(v), 2)
    Else
        FormatDocDate = Trim$(CStr(v))
    End If
End Function

Private Function CellText(ByVal v As Variant) As String
    If IsEmpty(v) Or IsError(v) Then Exit Function
    CellText = Trim$(CStr(v))
End Function
