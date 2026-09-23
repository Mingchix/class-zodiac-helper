from datetime import date
from io import BytesIO

import pandas as pd

from utils.excel_utils import build_class_statistics, detect_excel_columns, process_import
from utils.export_utils import export_analysis_excel, export_html_report


def test_detect_birth_and_name_aliases_only():
    frame = pd.DataFrame(columns=["IDCard", "学生姓名", "出生年月日"])
    assert detect_excel_columns(frame) == {"name": "学生姓名", "birthday": "出生年月日"}


def test_birthday_import_formats_and_zodiac():
    frame = pd.DataFrame({"生日": ["2012/03/21", date(2012, 4, 20), "20120321", "2012-01-01"], "学生姓名": ["甲", "乙", "甲", None]})
    students, errors = process_import(frame, "学生姓名", "生日", reference_date=date(2024, 1, 1))
    assert list(students["zodiac"]) == ["白羊座", "金牛座", "白羊座"]
    assert students["duplicate_warning"].tolist() == [False, False, True]
    assert len(errors) == 2


def test_missing_birthdays_are_rejected():
    frame = pd.DataFrame({"姓名": ["测试学生"]})
    students, errors = process_import(frame, "姓名", reference_date=date(2024, 1, 1))
    assert students.empty
    assert errors["问题类型"].tolist() == ["生日为空"]


def test_duplicates_same_name_kept_when_birthdays_differ():
    frame = pd.DataFrame({"姓名": ["同名", "同名", "同名"], "生日": ["2012-03-21", "2012-04-20", "2012-03-21"]})
    students, errors = process_import(frame, "姓名", "生日", reference_date=date(2024, 1, 1))
    assert len(students) == 3
    assert students["duplicate_warning"].tolist() == [False, False, True]
    assert "可能重复" in errors["问题类型"].tolist()


def test_statistics_cover_12_signs_4_elements_and_all_months():
    empty = pd.DataFrame(columns=["zodiac", "element", "birthday", "age"])
    stats = build_class_statistics(empty, date(2024, 3, 1))
    assert len(stats["zodiac"]) == 12
    assert len(stats["element"]) == 4
    assert len(stats["months"]) == 12


def test_export_is_generated_in_memory_and_has_no_identity_field():
    frame = pd.DataFrame({"姓名": ["测试甲"], "生日": ["2012-03-21"]})
    students, errors = process_import(frame, "姓名", "生日", reference_date=date(2024, 1, 1))
    stats = build_class_statistics(students, date(2024, 1, 1))
    workbook = export_analysis_excel(students, stats, errors)
    html = export_html_report(students, stats)

    excel = pd.ExcelFile(BytesIO(workbook))
    headers = pd.read_excel(BytesIO(workbook), sheet_name="学生结果").columns.tolist()
    assert "身份证号" not in headers
    assert "Online 版仅支持姓名与出生日期" in html
    assert "身份证号" not in html
    assert not any(name in ("output.xlsx", "report.html", "temp.xlsx") for name in __import__("os").listdir("."))
    assert "学生结果" in excel.sheet_names
