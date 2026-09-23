from datetime import date, timedelta
import pytest
from utils.zodiac import get_zodiac, SIGNS, STARTS, get_element

@pytest.mark.parametrize("sign,start", list(zip(SIGNS, STARTS)))
def test_zodiac_start_and_day_before(sign, start):
    y = 2024
    first = date(y, *start)
    assert get_zodiac(first) == sign
    assert get_zodiac(first - timedelta(days=1)) != sign

@pytest.mark.parametrize("sign,start", list(zip(SIGNS, STARTS)))
def test_zodiac_end_and_day_after(sign, start):
    i = SIGNS.index(sign)
    next_month, next_day = STARTS[(i + 1) % 12]
    end_year = 2025 if next_month <= start[0] else 2024
    end = date(end_year, next_month, next_day) - timedelta(days=1)
    assert get_zodiac(end) == sign
    assert get_zodiac(end + timedelta(days=1)) != sign

@pytest.mark.parametrize("birthday,expected", [(date(2024,3,20),"双鱼座"),(date(2024,3,21),"白羊座"),(date(2024,4,19),"白羊座"),(date(2024,4,20),"金牛座"),(date(2024,12,21),"射手座"),(date(2024,12,22),"摩羯座"),(date(2024,1,19),"摩羯座"),(date(2024,1,20),"水瓶座")])
def test_known_boundaries(birthday, expected):
    assert get_zodiac(birthday) == expected

def test_elements():
    assert get_element("白羊座") == "火象"
    assert get_element("摩羯座") == "土象"
    assert get_element("水瓶座") == "风象"
    assert get_element("双鱼座") == "水象"
