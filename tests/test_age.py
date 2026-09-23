from datetime import date
from utils.date_utils import calculate_age, parse_birthday
from data.age_profiles import get_age_profile

def test_age_before_after_and_on_birthday():
    born = date(2012, 6, 15)
    assert calculate_age(born, date(2024, 6, 14)) == 11
    assert calculate_age(born, date(2024, 6, 15)) == 12
    assert calculate_age(born, date(2024, 6, 16)) == 12

def test_february_29_age_uses_february_28_in_non_leap_year():
    assert calculate_age(date(2008, 2, 29), date(2023, 2, 27)) == 14
    assert calculate_age(date(2008, 2, 29), date(2023, 2, 28)) == 15
    assert calculate_age(date(2008, 2, 29), date(2024, 2, 28)) == 15

def test_parse_supported_date_formats():
    expected = date(2012, 3, 21)
    for value in ["2012-03-21", "2012/03/21", "2012.03.21", "20120321"]:
        assert parse_birthday(value) == expected
    assert parse_birthday(expected) == expected

def test_age_group():
    assert get_age_profile(13)[0] == "12～14 岁"
    assert get_age_profile(18)[0] == "15～18 岁"
    assert get_age_profile(19)[0] == "19 岁以上"
