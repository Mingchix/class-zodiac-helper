from datetime import date
from data.zodiac_profiles import PROFILES

SIGNS = ["摩羯座", "水瓶座", "双鱼座", "白羊座", "金牛座", "双子座", "巨蟹座", "狮子座", "处女座", "天秤座", "天蝎座", "射手座"]
STARTS = [(12, 22), (1, 20), (2, 19), (3, 21), (4, 20), (5, 21), (6, 22), (7, 23), (8, 23), (9, 23), (10, 24), (11, 23)]

def get_zodiac(birthday: date) -> str:
    key = (birthday.month, birthday.day)
    for i, start in enumerate(STARTS):
        end = STARTS[(i + 1) % len(STARTS)]
        if start <= end and start <= key < end:
            return SIGNS[i]
        if start > end and (key >= start or key < end):
            return SIGNS[i]
    raise ValueError(f"无法判断星座日期: {birthday}")

def get_element(zodiac: str) -> str:
    return PROFILES[zodiac]["element"]

def get_zodiac_profile(zodiac: str) -> dict:
    return PROFILES[zodiac].copy()
