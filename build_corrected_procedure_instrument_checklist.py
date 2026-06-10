from __future__ import annotations

from pathlib import Path
import csv
import re

import openpyxl
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.table import Table, TableStyleInfo


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "需要的術式器械_更正版.xlsx"
OUTPUT_XLSX = ROOT / "procedure_instrument_checklist.xlsx"
FALLBACK_OUTPUT_XLSX = ROOT / "procedure_instrument_checklist_更正版.xlsx"
OUTPUT_CSV = ROOT / "procedure_instrument_checklist.csv"
SUMMARY_CSV = ROOT / "report_checklist_summary.csv"


PROCEDURES = [
    {
        "procedure": "PTA周邊動靜脈血管整形術",
        "department": "心臟血管外科",
        "image": "S__107593747_0.jpg",
        "trays": ["PTA"],
        "extra": [],
        "note": "依更正版對應：PTA",
    },
    {
        "procedure": "口腔腫瘤切除（Oral tumor excision）",
        "department": "口腔外科",
        "image": "S__107593748_0.jpg",
        "trays": ["Suture Set"],
        "extra": [("單包單邊張口器", "1", "人工追加：對應器械盤欄註記")],
        "note": "依更正版對應：suture set + 單包單邊張口器",
    },
    {
        "procedure": "白內障手術（Cataract）",
        "department": "眼科",
        "image": "S__107593749_0.jpg",
        "trays": ["Phaco Cata Set", "Phaco Handpiece Set"],
        "extra": [],
        "note": "依更正版對應：Phaco Cata Set + phaco Handpiece set",
    },
    {
        "procedure": "人工血管置放術（Port-A）",
        "department": "一般外科",
        "image": "S__107593750_0.jpg",
        "trays": ["Suture Set"],
        "extra": [("Towel clip", "5", "人工追加：對應器械盤欄註記 towel clip*5")],
        "note": "依更正版對應：suture set + towel clip*5",
    },
    {
        "procedure": "肛門膿瘍切開術",
        "department": "大腸直腸外科",
        "image": "S__107593751_0.jpg",
        "trays": ["Hemorrhoid Set"],
        "extra": [],
        "note": "依更正版對應：外科 Hemorrhoid Set",
    },
    {
        "procedure": "子宮肌瘤切除術（基本器械組）",
        "department": "婦產科",
        "image": "S__107593752_0.jpg",
        "trays": ["K-N 基本盤"],
        "extra": [],
        "note": "依更正版對應：K-N 基本盤（部分器械）",
    },
    {
        "procedure": "子宮肌瘤切除術（完整器械組）",
        "department": "婦產科",
        "image": "S__107593753_0.jpg",
        "trays": ["K-N 基本盤"],
        "extra": [],
        "note": "依更正版對應：K-N 基本盤（部分器械）",
    },
    {
        "procedure": "子宮肌瘤切除術（含 self-retractor）",
        "department": "婦產科",
        "image": "S__107593754_0.jpg",
        "trays": ["K-N 基本盤"],
        "extra": [("Self Retractor", "1", "人工追加：對應器械盤欄註記 self-retractor")],
        "note": "依更正版對應：K-N 基本盤 + self-retractor",
    },
    {
        "procedure": "子宮肌瘤切除術（含 self-retractor 進階）",
        "department": "婦產科",
        "image": "S__107593755_0.jpg",
        "trays": ["K-N 基本盤"],
        "extra": [("Self Retractor", "1", "人工追加：對應器械盤欄註記 self-retractor")],
        "note": "依更正版對應：K-N 基本盤 + self-retractor",
    },
    {
        "procedure": "動靜脈血管吻合術（A-V shunt）",
        "department": "心臟血管外科",
        "image": "S__107593757.jpg",
        "trays": ["A-V Shunt Set"],
        "extra": [],
        "note": "依更正版對應：CVS A-V Shunt Set2025(B)",
    },
]


CLASS_RULES = [
    ("needle_holder", "持針器", ["needle holder", "持針"]),
    ("scissors", "手術剪", ["scissor", "scissors", "剪", "metzenbaum", "myoscissor"]),
    ("forceps", "鑷子", ["forceps", "鑷", "adson", "teeth", "allis", "ring"]),
    ("hemostatic_forceps", "止血鉗", ["mosquito", "kelly", "kocher", "cocker", "小彎", "中彎", "大彎", "中直", "止血"]),
    ("retractor", "撐開器", ["retractor", "speculum", "張口器", "張眼器", "肛門鉤", "hook"]),
    ("clamp", "夾鉗", ["clamp", "clip", "towel", "satinsky", "cooley"]),
    ("scalpel_handle", "刀柄", ["knife handle", "刀柄", "3號刀柄"]),
    ("suction_tube", "吸引管或管路", ["suction", "吸引", "tip", "tube", "管"]),
    ("basin_bowl", "彎盆或碗盤", ["basin", "bowl", "彎盆", "碗"]),
    ("needle_probe", "探針或針類", ["probe", "sound", "dillator", "needle", "針", "串棒"]),
]


def clean(value) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value).replace("\n", " ")).strip()


def infer_class(name: str) -> tuple[str, str, str]:
    lower = name.lower()
    for english, chinese, keywords in CLASS_RULES:
        if any(keyword.lower() in lower for keyword in keywords):
            return english, chinese, "yes"
    return "other", "其他", "manual_check"


def extract_items(workbook, sheet_name: str) -> list[dict[str, str]]:
    if sheet_name not in workbook.sheetnames:
        return []

    sheet = workbook[sheet_name]
    header_row = None
    name_col = None
    qty_col = None

    for row_idx in range(1, min(sheet.max_row, 8) + 1):
        values = [clean(sheet.cell(row_idx, col).value) for col in range(1, sheet.max_column + 1)]
        for col_idx, value in enumerate(values, start=1):
            if value == "序":
                header_row = row_idx
                for offset in range(1, 4):
                    candidate = values[col_idx - 1 + offset] if col_idx - 1 + offset < len(values) else ""
                    if name_col is None and ("品" in candidate or "名" in candidate or "器" in candidate):
                        name_col = col_idx + offset
                    if qty_col is None and "數" in candidate:
                        qty_col = col_idx + offset
                break
        if header_row:
            break

    if not header_row or not name_col or not qty_col:
        return []

    items = []
    for row_idx in range(header_row + 1, sheet.max_row + 1):
        serial = clean(sheet.cell(row_idx, 1).value)
        name = clean(sheet.cell(row_idx, name_col).value)
        qty = clean(sheet.cell(row_idx, qty_col).value)
        if not serial or not name or not re.fullmatch(r"\d+", serial):
            continue
        if "總件數" in name:
            continue
        english, chinese, visibility = infer_class(name)
        items.append(
            {
                "source_tray": sheet_name,
                "serial": serial,
                "name": name,
                "quantity": qty,
                "yolo_en": english,
                "yolo_zh": chinese,
                "visibility": visibility,
                "source_type": "器械盤明細",
                "note": "",
            }
        )
    return items


def append_table(sheet, table_name: str) -> None:
    if sheet.max_row < 2:
        return
    ref = f"A1:{openpyxl.utils.get_column_letter(sheet.max_column)}{sheet.max_row}"
    table = Table(displayName=table_name, ref=ref)
    table.tableStyleInfo = TableStyleInfo(name="TableStyleMedium2", showRowStripes=True, showColumnStripes=False)
    sheet.add_table(table)


def style(sheet, widths: dict[str, int]) -> None:
    fill = PatternFill("solid", fgColor="1F4E79")
    font = Font(color="FFFFFF", bold=True)
    side = Side(style="thin", color="D9E2F3")
    for cell in sheet[1]:
        cell.fill = fill
        cell.font = font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    for row in sheet.iter_rows():
        for cell in row:
            cell.border = Border(bottom=side)
            cell.alignment = Alignment(vertical="top", wrap_text=True)
    for col, width in widths.items():
        sheet.column_dimensions[col].width = width
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = sheet.dimensions


def write_csv(path: Path, headers: list[str], rows: list[list[str]]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.writer(file)
        writer.writerow(headers)
        writer.writerows(rows)


def main() -> None:
    source_wb = load_workbook(SOURCE, data_only=True, read_only=False)
    headers = [
        "術式",
        "科別",
        "圖片檔名",
        "對應器械盤",
        "來源類型",
        "序號",
        "器械名稱",
        "數量",
        "是否必要",
        "YOLO英文類別",
        "YOLO中文類別",
        "影像辨識建議",
        "備註",
    ]
    checklist_rows: list[list[str]] = []
    summary_rows: list[list[str]] = []
    todo_rows: list[list[str]] = []

    for proc in PROCEDURES:
        count = 0
        tray_names = []
        for tray in proc["trays"]:
            tray_names.append(tray)
            items = extract_items(source_wb, tray)
            if not items:
                todo_rows.append([proc["procedure"], proc["department"], proc["image"], f"找不到器械盤工作表：{tray}"])
            for item in items:
                count += 1
                checklist_rows.append(
                    [
                        proc["procedure"],
                        proc["department"],
                        proc["image"],
                        item["source_tray"],
                        item["source_type"],
                        item["serial"],
                        item["name"],
                        item["quantity"],
                        "yes",
                        item["yolo_en"],
                        item["yolo_zh"],
                        item["visibility"],
                        item["note"],
                    ]
                )

        for extra_index, (name, qty, note) in enumerate(proc["extra"], start=1):
            english, chinese, visibility = infer_class(name)
            count += 1
            checklist_rows.append(
                [
                    proc["procedure"],
                    proc["department"],
                    proc["image"],
                    " + ".join(proc["trays"]) + " + 人工追加",
                    "人工追加",
                    f"extra-{extra_index}",
                    name,
                    qty,
                    "yes",
                    english,
                    chinese,
                    visibility,
                    note,
                ]
            )
            tray_names.append(name)

        summary_rows.append(
            [
                proc["procedure"],
                proc["department"],
                proc["image"],
                " + ".join(tray_names),
                count,
                proc["note"],
            ]
        )
        if "部分器械" in proc["note"]:
            todo_rows.append([proc["procedure"], proc["department"], proc["image"], "目前以整份 K-N 基本盤列出，請確認實際只需要哪些部分器械。"])

    wb = Workbook()

    summary = wb.active
    summary.title = "專案術式總表"
    summary.append(["術式", "科別", "圖片檔名", "對應器械盤", "器械項目數", "更正依據"])
    for row in summary_rows:
        summary.append(row)
    append_table(summary, "ProcedureSummary")
    style(summary, {"A": 34, "B": 16, "C": 24, "D": 48, "E": 12, "F": 52})

    checklist = wb.create_sheet("術式器械清單")
    checklist.append(headers)
    for row in checklist_rows:
        checklist.append(row)
    append_table(checklist, "ProcedureInstrumentChecklist")
    style(checklist, {"A": 34, "B": 14, "C": 24, "D": 34, "E": 14, "F": 10, "G": 38, "H": 10, "I": 10, "J": 22, "K": 18, "L": 16, "M": 42})

    class_sheet = wb.create_sheet("YOLO類別對照")
    class_sheet.append(["YOLO英文類別", "中文類別", "關鍵字"])
    for english, chinese, keywords in CLASS_RULES:
        class_sheet.append([english, chinese, "；".join(keywords)])
    class_sheet.append(["other", "其他", "不確定或不適合影像辨識"])
    append_table(class_sheet, "YoloClassMap")
    style(class_sheet, {"A": 24, "B": 18, "C": 70})

    todo = wb.create_sheet("明天待確認")
    todo.append(["術式", "科別", "圖片檔名", "待確認事項"])
    for row in todo_rows:
        todo.append(row)
    if todo.max_row == 1:
        todo.append(["", "", "", "目前無系統解析錯誤；仍建議臨床確認必要器械與數量。"])
    append_table(todo, "TomorrowTodo")
    style(todo, {"A": 34, "B": 16, "C": 24, "D": 70})

    report = wb.create_sheet("報告摘要")
    report.append(["項目", "內容"])
    report_rows = [
        ["資料來源", "需要的術式器械.xlsx，以及醫院目前器械盤明細"],
        ["整理術式數", str(len(PROCEDURES))],
        ["已整理器械項目數", str(len(checklist_rows))],
        ["更正重點", "對應器械盤已依使用者 2026-06-09 更正版更新，含 Suture Set、Phaco Handpiece Set、K-N 基本盤、A-V Shunt Set(B) 等。"],
        ["建議報告方向", "以術式標準器械清單為主，YOLO 作為明顯器械輔助辨識，降低完整器械桌逐支框選的困難。"],
    ]
    for row in report_rows:
        report.append(row)
    style(report, {"A": 20, "B": 100})

    output_xlsx = OUTPUT_XLSX
    try:
        wb.save(output_xlsx)
    except PermissionError:
        output_xlsx = FALLBACK_OUTPUT_XLSX
        wb.save(output_xlsx)
    write_csv(OUTPUT_CSV, headers, checklist_rows)
    write_csv(SUMMARY_CSV, ["術式", "科別", "圖片檔名", "對應器械盤", "器械項目數", "更正依據"], summary_rows)

    print(f"output={output_xlsx}")
    print(f"csv={OUTPUT_CSV}")
    print(f"summary={SUMMARY_CSV}")
    print(f"rows={len(checklist_rows)}")
    print(f"todo={len(todo_rows)}")


if __name__ == "__main__":
    main()
