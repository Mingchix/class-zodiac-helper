from datetime import date, datetime
import calendar
import re
import pandas as pd

def parse_birthday(value) -> date:
    if value is None or pd.isna(value):
        raise ValueError("生日为空")
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    raw = str(value).strip()
    if not raw:
        raise ValueError("生日为空")
    if re.fullmatch(r"\d{8}(?:\.0)?", raw):
        raw = raw[:8]
        return datetime.strptime(raw, "%Y%m%d").date()
    normalized = re.sub(r"[./]", "-", raw)
    try:
        return date.fromisoformat(normalized[:10])
    except ValueError:
        parsed = pd.to_datetime(raw, errors="coerce")
        if pd.isna(parsed):
            raise ValueError("日期无法解析")
        return parsed.date()

def calculate_age(birthday: date, reference_date: date | None = None) -> int:
    reference_date = reference_date or date.today()
    years = reference_date.year - birthday.year
    if birthday.month == 2 and birthday.day == 29 and not calendar.isleap(reference_date.year):
        birthday_this_year = date(reference_date.year, 2, 28)
    else:
        birthday_this_year = birthday.replace(year=reference_date.year)
    return years - (reference_date < birthday_this_year)
