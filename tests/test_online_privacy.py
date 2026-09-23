from datetime import date
from io import BytesIO
from pathlib import Path
import inspect

import pandas as pd
from streamlit.testing.v1 import AppTest

from utils.excel_utils import detect_excel_columns, process_import, read_online_excel
from utils.export_utils import export_analysis_excel, export_html_report
from utils.excel_utils import build_class_statistics


ROOT = Path(__file__).resolve().parents[1]


def workbook_bytes(columns, rows):
    buffer = BytesIO()
    pd.DataFrame(rows, columns=columns).to_excel(buffer, index=False)
    buffer.seek(0)
    return buffer


def test_online_app_has_no_identity_upload_controls_or_parser():
    source = (ROOT / "app.py").read_text(encoding="utf-8")
    assert "Online 版不支持身份证号上传" in source
    for forbidden in ("身份证列", "下载身份证模板", "id_col", "extract_birthday_from_id", "validate_chinese_id", "mask_sensitive_preview"):
        assert forbidden not in source
    assert not (ROOT / "utils" / "idcard.py").exists()
    assert not (ROOT / "tests" / "test_idcard.py").exists()
    assert not list((ROOT / "templates").glob("*身份证*"))


def test_sensitive_excel_columns_are_excluded_before_loading_values():
    marker = "SYNTHETIC-SENSITIVE-COLUMN-CONTENT-DO-NOT-LOAD"
    uploaded = workbook_bytes(
        ["姓名", "出生日期", "身份证号"],
        [["测试甲", "2012-03-21", marker]],
    )
    safe_frame, excluded_headers = read_online_excel(uploaded)

    assert safe_frame.columns.tolist() == ["姓名", "出生日期"]
    assert excluded_headers == ["身份证号"]
    assert marker not in safe_frame.to_string()
    assert detect_excel_columns(safe_frame) == {"name": "姓名", "birthday": "出生日期"}

    students, errors = process_import(safe_frame, "姓名", "出生日期", reference_date=date(2024, 1, 1))
    assert len(students) == 1 and errors.empty
    stats = build_class_statistics(students, date(2024, 1, 1))
    xlsx = export_analysis_excel(students, stats, errors)
    html = export_html_report(students, stats)
    loaded = pd.read_excel(BytesIO(xlsx), sheet_name="学生结果").fillna("")
    assert marker not in loaded.to_string()
    assert "身份证号" not in loaded.columns
    assert marker not in html and "身份证号" not in html


def test_workbook_with_only_identity_column_is_rejected_for_missing_birthday():
    uploaded = workbook_bytes(["姓名", "身份证号"], [["测试甲", "SYNTHETIC-NOT-A-REAL-ID"]])
    safe_frame, excluded_headers = read_online_excel(uploaded)

    assert safe_frame.columns.tolist() == ["姓名"]
    assert excluded_headers == ["身份证号"]
    detected = detect_excel_columns(safe_frame)
    assert "birthday" not in detected
    assert "id" not in detected
    students, errors = process_import(safe_frame, detected.get("name"), reference_date=date(2024, 1, 1))
    assert students.empty
    assert errors["问题类型"].tolist() == ["生日为空"]
    assert "仅支持“姓名 + 出生日期”格式" in errors.iloc[0]["问题说明"]


def test_online_exports_are_memory_only_and_omit_sensitive_values(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    students, errors = process_import(pd.DataFrame({"姓名": ["虚构学生"], "出生日期": ["2012-11-08"]}), "姓名", "出生日期", date(2024, 1, 1))
    stats = build_class_statistics(students, date(2024, 1, 1))
    export_analysis_excel(students, stats, errors)
    export_html_report(students, stats)
    assert list(tmp_path.iterdir()) == []
    assert "id_col" not in inspect.signature(process_import).parameters


def test_streamlit_sessions_keep_student_lists_isolated():
    app_path = str(ROOT / "app.py")
    first = AppTest.from_file(app_path).run(timeout=15)
    second = AppTest.from_file(app_path).run(timeout=15)

    first_rows = first.session_state["students"].copy()
    first_rows.loc[0] = {
        "student_key": "S0001", "name": "会话甲", "birthday": date(2012, 3, 21), "age": 11,
        "zodiac": "白羊座", "element": "火象", "zodiac_keywords": [], "zodiac_description": "",
        "interaction_tip": "", "age_group": "12～14 岁", "teacher_age_tip": "", "source": "测试", "row_number": 0,
    }
    first.session_state["students"] = first_rows

    assert second.session_state["students"].empty
    assert first.session_state["students"].iloc[0]["name"] == "会话甲"


def test_clear_current_data_clears_the_session_and_confirms_to_user():
    app = AppTest.from_file(str(ROOT / "app.py")).run(timeout=15)
    app.session_state["students"] = pd.DataFrame([{
        "student_key": "S0001", "name": "待清除学生", "birthday": date(2012, 3, 21), "age": 11,
        "zodiac": "白羊座", "element": "火象", "zodiac_keywords": [], "zodiac_description": "",
        "interaction_tip": "", "age_group": "12～14 岁", "teacher_age_tip": "", "source": "测试", "row_number": 0,
    }])
    app.session_state["pending_import"] = pd.DataFrame({"姓名": ["待清除学生"]})
    app.session_state["activity_groups"] = [["待清除学生"]]

    clear_button = next(button for button in app.button if button.label == "清空当前数据")
    clear_button.click().run(timeout=15)

    assert app.session_state["students"].empty
    assert app.session_state["pending_import"] is None
    assert "activity_groups" not in app.session_state
    assert any("当前会话数据已清空" in message.value for message in app.success)


def test_online_cloud_config_is_not_bound_to_a_local_address():
    config = (ROOT / ".streamlit" / "config.toml").read_text(encoding="utf-8")
    assert "gatherUsageStats = false" in config
    assert "address" not in config.lower()
    assert "port" not in config.lower()
