from datetime import date

import pandas as pd

from .date_utils import calculate_age, parse_birthday
from .zodiac import get_element, get_zodiac, get_zodiac_profile, SIGNS
from data.age_profiles import get_age_profile


NAME_ALIASES = {"姓名", "学生姓名", "名字", "name"}
BIRTH_ALIASES = {"生日", "出生日期", "出生年月", "出生年月日", "出生时间", "dob", "birthday"}
ELEMENTS = ["火象", "土象", "风象", "水象"]
SENSITIVE_HEADER_MARKERS = (
    "身份证", "证件", "idcard", "id_card", "identity", "passport", "socialsecurity",
    "identification", "nationalid", "idnumber", "id_no", "idno", "ssn",
    "地址", "住址", "电话", "手机", "phone", "mobile", "医疗", "病历", "健康", "诊断", "medical",
)


def _normalized(value):
    return str(value).strip().casefold().replace(" ", "") if value is not None else ""


def is_sensitive_column(column) -> bool:
    """Recognize headers that the Online version must never load or display."""
    normalized = _normalized(column)
    return normalized.startswith("id") or any(marker.casefold() in normalized for marker in SENSITIVE_HEADER_MARKERS)


def read_online_excel(uploaded):
    """Read an uploaded workbook while excluding sensitive columns at the parser."""
    uploaded.seek(0)
    headers = list(pd.read_excel(uploaded, nrows=0).columns)
    sensitive_headers = [header for header in headers if is_sensitive_column(header)]
    safe_headers = [header for header in headers if not is_sensitive_column(header)]
    if not safe_headers:
        return pd.DataFrame(), sensitive_headers

    uploaded.seek(0)
    frame = pd.read_excel(uploaded, dtype=str, usecols=safe_headers)
    return frame, sensitive_headers


def detect_excel_columns(df: pd.DataFrame) -> dict:
    found = {}
    for col in df.columns:
        name = _normalized(col)
        if "name" not in found and name in NAME_ALIASES:
            found["name"] = col
        if "birthday" not in found and name in BIRTH_ALIASES:
            found["birthday"] = col
    return found


def process_import(df: pd.DataFrame, name_col, birthday_col=None, reference_date=None):
    reference_date = reference_date or date.today()
    students, errors, seen = [], [], set()
    for idx, row in df.iterrows():
        try:
            excel_row = int(idx) + 2
        except (TypeError, ValueError):
            excel_row = len(students) + len(errors) + 2

        name_value = row.get(name_col) if name_col is not None else None
        name = "" if pd.isna(name_value) else str(name_value).strip()
        raw_birthday = row.get(birthday_col) if birthday_col is not None else None
        if not name and (birthday_col is None or pd.isna(raw_birthday) or not str(raw_birthday).strip()):
            continue

        issue = None
        birthday = None
        if not name:
            issue = ("姓名为空", "请填写学生姓名")
        elif birthday_col is None or pd.isna(raw_birthday) or not str(raw_birthday).strip():
            issue = ("生日为空", "Online 版仅支持“姓名 + 出生日期”格式")
        else:
            try:
                birthday = parse_birthday(raw_birthday)
            except (ValueError, TypeError):
                issue = ("日期无法解析", "出生日期格式无法识别")

        if issue is None and birthday > reference_date:
            issue = ("未来日期", "出生日期晚于统计日期")
        if issue:
            errors.append({"Excel行号": excel_row, "姓名": name, "问题类型": issue[0], "问题说明": issue[1]})
            continue

        age = calculate_age(birthday, reference_date)
        if age > 120:
            errors.append({"Excel行号": excel_row, "姓名": name, "问题类型": "年龄明显不合理", "问题说明": "计算年龄超过 120 岁"})
            continue

        key = (name.casefold(), birthday)
        duplicate = key in seen
        if duplicate:
            errors.append({"Excel行号": excel_row, "姓名": name, "问题类型": "可能重复", "问题说明": "姓名和出生日期与前一条记录相同，请确认是否保留。"})
        seen.add(key)
        zodiac = get_zodiac(birthday)
        profile = get_zodiac_profile(zodiac)
        age_group, teacher_tip = get_age_profile(age)
        students.append({
            "student_key": f"S{len(students)+1:04d}", "name": name, "birthday": birthday, "age": age,
            "zodiac": zodiac, "element": get_element(zodiac), "zodiac_keywords": profile["keywords"],
            "zodiac_description": profile["description"], "interaction_tip": profile["tip"],
            "age_group": age_group, "teacher_age_tip": teacher_tip, "source": "Excel",
            "row_number": excel_row, "duplicate_warning": duplicate,
        })

    student_columns = [
        "student_key", "name", "birthday", "age", "zodiac", "element", "zodiac_keywords",
        "zodiac_description", "interaction_tip", "age_group", "teacher_age_tip", "source",
        "row_number", "duplicate_warning",
    ]
    error_columns = ["Excel行号", "姓名", "问题类型", "问题说明"]
    return pd.DataFrame(students, columns=student_columns), pd.DataFrame(errors, columns=error_columns)


def build_class_statistics(df: pd.DataFrame, reference_date=None):
    reference_date = reference_date or date.today()
    zodiac = df["zodiac"].value_counts().reindex(SIGNS, fill_value=0).rename_axis("星座").reset_index(name="人数") if len(df) else pd.DataFrame({"星座": SIGNS, "人数": 0})
    zodiac["占比"] = zodiac["人数"].apply(lambda n: n / len(df) if len(df) else 0)
    element = df["element"].value_counts().reindex(ELEMENTS, fill_value=0).rename_axis("四象").reset_index(name="人数") if len(df) else pd.DataFrame({"四象": ELEMENTS, "人数": 0})
    element["占比"] = element["人数"].apply(lambda n: n / len(df) if len(df) else 0)
    months = df["birthday"].map(lambda d: d.month).value_counts().reindex(range(1, 13), fill_value=0).rename_axis("月份").reset_index(name="人数") if len(df) else pd.DataFrame({"月份": range(1, 13), "人数": 0})
    ages = df["age"] if len(df) else pd.Series(dtype=int)
    this_month = sum(1 for d in df["birthday"] if d.month == reference_date.month) if len(df) else 0
    return {
        "zodiac": zodiac, "element": element, "months": months,
        "summary": {
            "total": len(df), "valid_birthdays": len(df),
            "average_age": round(float(ages.mean()), 1) if len(ages) else 0,
            "min_age": int(ages.min()) if len(ages) else 0,
            "max_age": int(ages.max()) if len(ages) else 0,
            "this_month": this_month,
        },
    }
