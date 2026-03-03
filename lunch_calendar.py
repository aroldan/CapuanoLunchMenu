#!/usr/bin/env python3
# /// script
# dependencies = ["requests", "reportlab"]
# ///
"""
School Lunch Menu Calendar Generator
Fetches menu data from LinqConnect API and produces a printable 8.5x11 landscape PDF.

Usage:
    uv run lunch_calendar.py                   # Current month
    uv run lunch_calendar.py 2026 3            # March 2026
    uv run lunch_calendar.py 2026 4            # April 2026
"""

import sys
import json
import calendar
from datetime import date, datetime
from collections import defaultdict

import requests
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor, white, black
from reportlab.pdfgen import canvas
from reportlab.lib.utils import simpleSplit

# ── Configuration ──────────────────────────────────────────────────────────────
BUILDING_ID = "2392b58e-48e6-eb11-a2c9-d2abdd85801a"
DISTRICT_ID = "7810c14e-a7e4-eb11-a2c5-8cc0b3a2728d"
API_URL = "https://api.linqconnect.com/api/FamilyMenu"

# Category names from the API, lowercased, that map to each bucket
HOT_CATEGORIES = {"hot entree", "hot sandwich"}
SIDE_CATEGORIES = {"side", "vegetable"}
ALT_CATEGORIES  = {"deli", "grab and go salad"}
# Everything else (milk, fruit, fruit juice, condiments, breakfast entree…) is skipped

# ── Colors ─────────────────────────────────────────────────────────────────────
C_DARK = HexColor("#2d2926")
C_WARM = HexColor("#6b5e53")
C_RED = HexColor("#c2553a")
C_BG_LIGHT = HexColor("#f9f7f3")
C_BORDER = HexColor("#d6d1ca")
C_WEEKEND = HexColor("#edeae5")
C_ALT_BG = HexColor("#f4f1ec")
C_TEXT = HexColor("#3a3632")
C_MUTED = HexColor("#999999")
C_GREEN = HexColor("#4a7a5a")


def fetch_menu(year: int, month: int) -> dict:
    """Fetch menu from LinqConnect API and return {day_num: {hot: [...], alt: [...]}}."""
    last_day = calendar.monthrange(year, month)[1]
    params = {
        "buildingId": BUILDING_ID,
        "districtId": DISTRICT_ID,
        "startDate": f"{month}-1-{year}",
        "endDate": f"{month}-{last_day}-{year}",
    }
    print(f"Fetching menu for {calendar.month_name[month]} {year}...")
    resp = requests.get(API_URL, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    return parse_menu(data, year, month)


def parse_menu(data: dict, year: int, month: int) -> dict:
    result = {}
    sessions = data.get("FamilyMenuSessions", [])
    for session in sessions:
        if (session.get("ServingSession") or "").lower() != "lunch":
            continue
        for plan in session.get("MenuPlans", []):
            for day in plan.get("Days", []):
                date_str = day.get("Date", "")
                if not date_str:
                    continue
                try:
                    d = datetime.strptime(date_str, "%m/%d/%Y")
                except ValueError:
                    try:
                        d = datetime.strptime(date_str[:10], "%Y-%m-%d")
                    except ValueError:
                        continue
                if d.month != month or d.year != year:
                    continue
                day_num = d.day
                hot = []
                side = []
                alt = []
                for meal in day.get("MenuMeals", []):
                    for cat in meal.get("RecipeCategories", []):
                        cat_name = cat.get("CategoryName", "").lower()
                        if cat_name in HOT_CATEGORIES:
                            bucket = hot
                        elif cat_name in SIDE_CATEGORIES:
                            bucket = side
                        elif cat_name in ALT_CATEGORIES:
                            bucket = alt
                        else:
                            continue
                        for recipe in cat.get("Recipes", []):
                            name = (recipe.get("RecipeName") or "").strip()
                            if name and name not in bucket:
                                bucket.append(name)
                result[day_num] = {"hot": hot, "side": side, "alt": alt}
    return result


def get_calendar_weeks(year: int, month: int):
    """Return list of weeks, each a list of 7 day-numbers (None for empty slots)."""
    cal = calendar.Calendar(firstweekday=6)  # Sunday first
    weeks = []
    current_week = []
    for d in cal.itermonthdates(year, month):
        day_num = d.day if d.month == month else None
        current_week.append(day_num)
        if len(current_week) == 7:
            weeks.append(current_week)
            current_week = []
    if current_week:
        while len(current_week) < 7:
            current_week.append(None)
        weeks.append(current_week)
    return weeks


def get_week_alternates(week, menu_data):
    """Collect unique alternates across all days in a given week row."""
    alts = []
    for i, day in enumerate(week):
        if day is None or i == 0 or i == 6:
            continue
        day_data = menu_data.get(day)
        if day_data:
            for a in day_data["alt"]:
                if a not in alts:
                    alts.append(a)
    return alts


def draw_text_wrapped(c_obj, text, x, y, max_width, font_name, font_size,
                      color=C_TEXT, leading=None, bullet=None, bullet_color=None):
    """Draw wrapped text, return the y position after drawing."""
    if leading is None:
        leading = font_size + 2

    c_obj.setFont(font_name, font_size)
    c_obj.setFillColor(color)

    if bullet:
        bullet_w = c_obj.stringWidth(bullet + " ", font_name, font_size)
        # Draw bullet
        if bullet_color:
            c_obj.setFillColor(bullet_color)
        c_obj.drawString(x, y, bullet)
        c_obj.setFillColor(color)
        text_x = x + bullet_w
        text_max = max_width - bullet_w
    else:
        text_x = x
        text_max = max_width

    lines = simpleSplit(text, font_name, font_size, text_max)
    for i, line in enumerate(lines):
        if i == 0:
            c_obj.drawString(text_x, y, line)
        else:
            c_obj.drawString(text_x, y, line)
        y -= leading
    return y


def generate_pdf(year: int, month: int, menu_data: dict, filename: str):
    """Generate the landscape 8.5x11 PDF calendar."""
    page_w, page_h = landscape(letter)  # 11 x 8.5 inches
    c_obj = canvas.Canvas(filename, pagesize=landscape(letter))

    margin_left = 0.35 * inch
    margin_right = 0.35 * inch
    margin_top = 0.35 * inch
    margin_bottom = 0.25 * inch

    usable_w = page_w - margin_left - margin_right
    usable_h = page_h - margin_top - margin_bottom

    weeks = get_calendar_weeks(year, month)
    num_weeks = len(weeks)

    has_alternates = any(
        menu_data.get(day, {}).get("alt", [])
        for week in weeks
        for i, day in enumerate(week)
        if day and 0 < i < 6
    )

    # Column widths
    weekend_w = 0.32 * inch
    alt_w = 1.55 * inch if has_alternates else 0
    remaining = usable_w - 2 * weekend_w - alt_w
    day_w = remaining / 5.0

    # Header area
    header_h = 0.45 * inch
    day_header_h = 0.22 * inch
    table_top = page_h - margin_top - header_h
    table_body_top = table_top - day_header_h
    table_body_h = table_body_top - margin_bottom
    row_h = table_body_h / num_weeks

    # ── Draw title bar ─────────────────────────────────────────────────────
    title = f"{calendar.month_name[month]} {year} — Lunch Menu"
    c_obj.setFont("Helvetica-Bold", 22)
    c_obj.setFillColor(C_DARK)
    c_obj.drawString(margin_left, page_h - margin_top - 0.25 * inch, title)

    c_obj.setFont("Helvetica", 8)
    c_obj.setFillColor(C_MUTED)
    sub = "Source: LinqConnect"
    sub_w = c_obj.stringWidth(sub, "Helvetica", 8)
    c_obj.drawString(page_w - margin_right - sub_w, page_h - margin_top - 0.25 * inch, sub)

    # Title underline
    c_obj.setStrokeColor(C_DARK)
    c_obj.setLineWidth(2)
    line_y = table_top + 0.04 * inch
    c_obj.line(margin_left, line_y, page_w - margin_right, line_y)

    # ── Day-of-week header row ─────────────────────────────────────────────
    day_names = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    col_widths = [weekend_w, day_w, day_w, day_w, day_w, day_w, weekend_w]
    if has_alternates:
        col_widths.append(alt_w)

    # Header background
    c_obj.setFillColor(C_DARK)
    c_obj.rect(margin_left, table_top - day_header_h, usable_w, day_header_h, fill=1, stroke=0)

    x = margin_left
    for i, name in enumerate(day_names):
        w = col_widths[i]
        c_obj.setFillColor(white)
        if i == 0 or i == 6:
            c_obj.setFont("Helvetica-Bold", 7)
            label = name[0]
        else:
            c_obj.setFont("Helvetica-Bold", 9)
            label = name
        tw = c_obj.stringWidth(label, c_obj._fontname, c_obj._fontsize)
        c_obj.drawString(x + (w - tw) / 2, table_top - day_header_h + 0.06 * inch, label)
        x += w

    if has_alternates:
        c_obj.setFillColor(C_WARM)
        c_obj.rect(x, table_top - day_header_h, alt_w, day_header_h, fill=1, stroke=0)
        c_obj.setFillColor(white)
        c_obj.setFont("Helvetica-Bold", 7)
        label = "WEEKLY ALTERNATES"
        tw = c_obj.stringWidth(label, "Helvetica-Bold", 7)
        c_obj.drawString(x + (alt_w - tw) / 2, table_top - day_header_h + 0.06 * inch, label)

    # ── Draw calendar rows ─────────────────────────────────────────────────
    for wi, week in enumerate(weeks):
        row_top = table_body_top - wi * row_h
        row_bot = row_top - row_h

        x = margin_left
        for di, day in enumerate(week):
            w = col_widths[di]
            is_weekend = (di == 0 or di == 6)

            # Cell background
            if day is None:
                c_obj.setFillColor(C_BG_LIGHT if not is_weekend else C_WEEKEND)
            elif is_weekend:
                c_obj.setFillColor(C_WEEKEND)
            else:
                c_obj.setFillColor(white)
            c_obj.rect(x, row_bot, w, row_h, fill=1, stroke=0)

            # Cell border
            c_obj.setStrokeColor(C_BORDER)
            c_obj.setLineWidth(0.5)
            c_obj.rect(x, row_bot, w, row_h, fill=0, stroke=1)

            if day is not None:
                # Day number
                y_cursor = row_top - 0.14 * inch
                if is_weekend:
                    c_obj.setFont("Helvetica", 9)
                    c_obj.setFillColor(C_MUTED)
                    tw = c_obj.stringWidth(str(day), "Helvetica", 9)
                    c_obj.drawString(x + (w - tw) / 2, y_cursor, str(day))
                else:
                    c_obj.setFont("Helvetica-Bold", 11)
                    c_obj.setFillColor(C_DARK)
                    c_obj.drawString(x + 0.05 * inch, y_cursor, str(day))

                    # Entrees and sides
                    day_data = menu_data.get(day)
                    y_cursor -= 0.16 * inch
                    if day_data and day_data["hot"]:
                        for item in day_data["hot"]:
                            if y_cursor < row_bot + 0.04 * inch:
                                break
                            y_cursor = draw_text_wrapped(
                                c_obj, item,
                                x + 0.08 * inch, y_cursor,
                                w - 0.14 * inch,
                                "Helvetica", 7.5,
                                color=C_TEXT,
                                leading=9,
                                bullet="•",
                                bullet_color=C_RED
                            )
                            y_cursor -= 1
                    elif not is_weekend:
                        c_obj.setFont("Helvetica-Oblique", 7)
                        c_obj.setFillColor(C_MUTED)
                        c_obj.drawString(x + 0.08 * inch, y_cursor, "—")

                    if day_data and day_data["side"]:
                        y_cursor -= 2  # small gap before sides
                        for item in day_data["side"]:
                            if y_cursor < row_bot + 0.04 * inch:
                                break
                            y_cursor = draw_text_wrapped(
                                c_obj, item,
                                x + 0.08 * inch, y_cursor,
                                w - 0.14 * inch,
                                "Helvetica", 7,
                                color=C_MUTED,
                                leading=8.5,
                                bullet="·",
                                bullet_color=C_GREEN
                            )
                            y_cursor -= 1

            x += w

        # Alternates column
        if has_alternates:
            alt_x = x
            # Background
            c_obj.setFillColor(C_ALT_BG)
            c_obj.rect(alt_x, row_bot, alt_w, row_h, fill=1, stroke=0)
            # Left accent border
            c_obj.setStrokeColor(C_WARM)
            c_obj.setLineWidth(1.5)
            c_obj.line(alt_x, row_bot, alt_x, row_top)
            # Outer border
            c_obj.setStrokeColor(C_BORDER)
            c_obj.setLineWidth(0.5)
            c_obj.rect(alt_x, row_bot, alt_w, row_h, fill=0, stroke=1)

            week_alts = get_week_alternates(week, menu_data)
            y_cursor = row_top - 0.12 * inch
            if week_alts:
                c_obj.setFont("Helvetica-Bold", 6)
                c_obj.setFillColor(C_MUTED)
                c_obj.drawString(alt_x + 0.06 * inch, y_cursor, "THIS WEEK")
                y_cursor -= 0.12 * inch
                for alt_item in week_alts:
                    if y_cursor < row_bot + 0.04 * inch:
                        break
                    y_cursor = draw_text_wrapped(
                        c_obj, alt_item,
                        alt_x + 0.06 * inch, y_cursor,
                        alt_w - 0.12 * inch,
                        "Helvetica", 7,
                        color=C_WARM,
                        leading=8.5,
                        bullet="◦",
                        bullet_color=C_WARM
                    )
                    y_cursor -= 1

    # ── Legend ──────────────────────────────────────────────────────────────
    legend_y = margin_bottom - 0.02 * inch
    c_obj.setFont("Helvetica", 6.5)
    c_obj.setFillColor(C_MUTED)
    legend_text = "• Hot Entrees     · Sides & Vegetables     ◦ Alternates (weekly: deli, grab & go, etc.)     Milk and fruit not shown."
    c_obj.drawString(margin_left, legend_y, legend_text)

    c_obj.save()
    print(f"✓ Saved: {filename}")


def main():
    today = date.today()
    if len(sys.argv) >= 3:
        year = int(sys.argv[1])
        month = int(sys.argv[2])
    elif len(sys.argv) == 2:
        month = int(sys.argv[1])
        year = today.year
    else:
        year = today.year
        month = today.month

    menu_data = fetch_menu(year, month)

    if not menu_data:
        print("⚠  No lunch menu data found for this month. The school may not have published it yet.")
        print("   Generating empty calendar anyway...")

    filename = f"lunch_menu_{year}_{month:02d}.pdf"
    generate_pdf(year, month, menu_data, filename)

    # Print summary
    total_days = sum(1 for d in menu_data.values() if d["hot"])
    total_sides = sum(1 for d in menu_data.values() if d["side"])
    total_alt = sum(1 for d in menu_data.values() if d["alt"])
    print(f"   {total_days} days with hot entrees, {total_sides} with sides, {total_alt} with alternates")


if __name__ == "__main__":
    main()
