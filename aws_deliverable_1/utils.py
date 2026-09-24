from datetime import datetime
from typing import Any


def get_date_parts(date_str: str) -> tuple[str, int, str, int]:
    """Returns (month_name, day_num, suffix, year) for superscript formatting."""
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    day = dt.day

    if 11 <= day <= 13:
        suffix = 'th'
    else:
        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(day % 10, 'th')

    return dt.strftime('%B'), day, suffix, dt.year


def add_header_with_superscript_date(
    paragraph: Any,
    prefix: str,
    start_date_str: str,
    end_date_str: str
) -> None:
    """Appends header text with ordinal day suffixes formatted as superscripts."""
    p1_month, p1_day, p1_suf, p1_year = get_date_parts(start_date_str)
    p2_month, p2_day, p2_suf, p2_year = get_date_parts(end_date_str)

    paragraph.add_run(f"{prefix} (")
    paragraph.add_run(f"{p1_month} {p1_day}")
    r_s1 = paragraph.add_run(p1_suf)
    r_s1.font.superscript = True
    paragraph.add_run(f", {p1_year} to ")

    paragraph.add_run(f"{p2_month} {p2_day}")
    r_s2 = paragraph.add_run(p2_suf)
    r_s2.font.superscript = True
    paragraph.add_run(f", {p2_year})")

    for run in paragraph.runs:
        run.bold = True