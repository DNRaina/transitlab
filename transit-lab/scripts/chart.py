#!/usr/bin/env python3
"""Build a Jyotisha birth chart from a birthplace and local birth time."""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

SIGNS = [
    "Mesha", "Vrishabha", "Mithuna", "Karka",
    "Simha", "Kanya", "Tula", "Vrischika",
    "Dhanu", "Makara", "Kumbha", "Meena",
]

SIGN_LORDS = {
    "Mesha": "Mars",
    "Vrishabha": "Venus",
    "Mithuna": "Mercury",
    "Karka": "Moon",
    "Simha": "Sun",
    "Kanya": "Mercury",
    "Tula": "Venus",
    "Vrischika": "Mars",
    "Dhanu": "Jupiter",
    "Makara": "Saturn",
    "Kumbha": "Saturn",
    "Meena": "Jupiter",
}

NAKSHATRAS = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni",
    "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha",
    "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta", "Shatabhisha",
    "Purva Bhadrapada", "Uttara Bhadrapada", "Revati",
]

DASHA_LORDS = [
    ("Ketu", 7), ("Venus", 20), ("Sun", 6), ("Moon", 10),
    ("Mars", 7), ("Rahu", 18), ("Jupiter", 16), ("Saturn", 19), ("Mercury", 17),
]

BODIES = [
    ("Sun", "Sun"), ("Moon", "Moon"), ("Mercury", "Mercury"),
    ("Venus", "Venus"), ("Mars", "Mars"), ("Jupiter", "Jupiter"),
    ("Saturn", "Saturn"), ("MeanNode", "Rahu"),
]

NAKSHATRA_SPAN = 360.0 / 27
YEAR_DAYS = 365.2425
OSM_ATTRIBUTION = "Geocoding: © OpenStreetMap contributors (Nominatim)"


class ClarificationNeeded(Exception):
    def __init__(self, payload: dict):
        self.payload = payload


def norm(degrees: float) -> float:
    return degrees % 360.0


def zodiac(longitude: float) -> dict:
    value = norm(longitude)
    index = int(value // 30)
    sign = SIGNS[index]
    return {
        "sign": sign,
        "sign_lord": SIGN_LORDS[sign],
        "degree": round(value - index * 30, 5),
        "longitude": round(value, 5),
    }


def navamsa(longitude: float) -> dict:
    value = norm(longitude)
    sign_index = int(value // (360.0 / 108)) % 12
    sign = SIGNS[sign_index]
    pada = min(9, int((value % 30) // (30.0 / 9)) + 1)
    return {
        "sign": sign,
        "sign_lord": SIGN_LORDS[sign],
        "pada": pada,
    }


def get_nakshatra(longitude: float) -> dict:
    val = norm(longitude)
    nak_index = min(26, int(val / NAKSHATRA_SPAN))
    pada = min(4, int((val - nak_index * NAKSHATRA_SPAN) / (NAKSHATRA_SPAN / 4.0)) + 1)
    lord = DASHA_LORDS[nak_index % len(DASHA_LORDS)][0]
    return {
        "name": NAKSHATRAS[nak_index],
        "pada": pada,
        "lord": lord,
    }


def parse_date(value: str) -> date:
    raw = value.strip().replace("/", "-")
    match_iso = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})$", raw)
    if match_iso:
        y, m, d = int(match_iso.group(1)), int(match_iso.group(2)), int(match_iso.group(3))
        return date(y, m, d)
    match_dmy = re.match(r"^(\d{1,2})-(\d{1,2})-(\d{4})$", raw)
    if match_dmy:
        d, m, y = int(match_dmy.group(1)), int(match_dmy.group(2)), int(match_dmy.group(3))
        return date(y, m, d)
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise ValueError(f"Birth date must be YYYY-MM-DD (received {value!r}).") from exc


def parse_local_time(value: str) -> time:
    raw = value.strip().lower()
    for devanagari, digit in zip("०१२३४५६७८९", "0123456789"):
        raw = raw.replace(devanagari, digit)

    # Standalone single-word times
    if raw in ("noon", "midday", "मध्याह्न"):
        return time(12, 0, 0)
    if raw in ("midnight", "मध्यरात्रि"):
        return time(0, 0, 0)

    # Match hour with optional minute and second separated by : or .
    match = re.search(r"(?<!\d)(\d{1,2})(?:[:.]([0-5]\d))?(?:[:.]([0-5]\d))?(?:\s*([ap])\.?m\.?)?", raw)
    if not match:
        raise ValueError("I couldn't read that time. Use a clock time (e.g. '04:00' or '16:30') or a phrase such as 'subah ke 4'.")

    hour = int(match.group(1))
    minute = int(match.group(2) or 0)
    second = int(match.group(3) or 0)
    meridiem = match.group(4)

    morning = any(word in raw for word in ("subah", "सुबह", "morning", "dawn", "pratah", "प्रातः", "bhor", "भोर", "purvahna", "पूर्वाह्न"))
    afternoon = any(word in raw for word in ("dopahar", "दोपहर", "afternoon", "shaam", "शाम", "saanjh", "साँझ", "सांझ", "evening", "noon", "sandhya", "संध्या", "madhyahna", "मध्याह्न", "aparahna", "अपराह्न"))
    night = any(word in raw for word in ("raat", "रात", "night", "midnight", "madhyaratri", "मध्यरात्रि", "ratri", "रात्रि"))

    if meridiem:
        if not 1 <= hour <= 12:
            raise ValueError("For AM/PM time, the hour must be 1 through 12.")
        hour = (hour % 12) + (12 if meridiem == "p" else 0)
    elif morning:
        if not 1 <= hour <= 12:
            raise ValueError("That morning time is outside the 1–12 hour range.")
        hour = 0 if hour == 12 else hour
    elif afternoon:
        if not 1 <= hour <= 12:
            raise ValueError("That afternoon/evening time is outside the 1–12 hour range.")
        hour = 12 if hour == 12 else hour + 12
    elif night:
        if not 1 <= hour <= 12:
            raise ValueError("That night time is outside the 1–12 hour range.")
        hour = 0 if hour == 12 else (hour if hour <= 5 else hour + 12)
    elif match.group(2) and len(match.group(1)) == 2:
        if not 0 <= hour <= 23:
            raise ValueError("24-hour time must be between 00:00 and 23:59.")
    elif 1 <= hour <= 12:
        if hour == 12:
            choices = [f"00:{minute:02d}:{second:02d}", f"12:{minute:02d}:{second:02d}"]
            raise ClarificationNeeded({
                "status": "needs_clarification",
                "kind": "time",
                "question": f"Does {value!r} mean midnight or noon?",
                "choices": choices,
            })
        first_choice = f"{hour % 12:02d}:{minute:02d}:{second:02d}"
        second_choice = f"{(hour % 12) + 12:02d}:{minute:02d}:{second:02d}"
        raise ClarificationNeeded({
            "status": "needs_clarification",
            "kind": "time",
            "question": f"Does {value!r} mean morning ({first_choice}) or afternoon/evening ({second_choice})?",
            "choices": [first_choice, second_choice],
        })
    elif not 0 <= hour <= 23:
        raise ValueError("Hour must be between 0 and 23.")

    return time(hour, minute, second)


def geocode_place(query: str, domain: str) -> tuple[float, float, str]:
    try:
        from geopy.geocoders import Nominatim
        from geopy.extra.rate_limiter import RateLimiter
    except ImportError as exc:
        raise RuntimeError("Place lookup needs the geocoding dependencies. Install transit-lab/requirements.txt.") from exc
    try:
        geocoder = Nominatim(domain=domain, scheme="https", user_agent="transit-lab/0.2 (https://github.com/DNRaina/transitlab)", timeout=15)
        lookup = RateLimiter(geocoder.geocode, min_delay_seconds=1.1, max_retries=1, error_wait_seconds=2, swallow_exceptions=False)
        matches = lookup(query, exactly_one=False, limit=5, addressdetails=True) or []
    except Exception as exc:
        raise RuntimeError(f"Birthplace lookup failed ({exc.__class__.__name__}). Check the place spelling or provide coordinates and a time zone.") from exc

    # Filter out duplicate addresses and near-duplicate points in the same metropolitan area (< ~20 km)
    candidates = []
    seen_addresses = set()
    for item in matches:
        addr = item.address.strip().lower()
        if addr in seen_addresses:
            continue
        if any(abs(c.latitude - item.latitude) < 0.2 and abs(c.longitude - item.longitude) < 0.2 for c in candidates):
            continue
        seen_addresses.add(addr)
        candidates.append(item)

    if not candidates:
        raise RuntimeError(f"No place match for {query!r}. Add a region/country or provide coordinates.")
    if len(candidates) > 1:
        raise ClarificationNeeded({
            "status": "needs_clarification",
            "kind": "place",
            "question": "Which of these birthplaces did you mean?",
            "choices": [{"index": i + 1, "name": item.address, "latitude": item.latitude, "longitude": item.longitude} for i, item in enumerate(candidates)],
        })
    item = candidates[0]
    return float(item.latitude), float(item.longitude), item.address


def local_to_utc(local_naive: datetime, zone: ZoneInfo, fold_choice: str | None) -> datetime:
    valid = []
    for fold in (0, 1):
        aware = local_naive.replace(tzinfo=zone, fold=fold)
        utc = aware.astimezone(timezone.utc)
        if utc.astimezone(zone).replace(tzinfo=None) == local_naive and all(utc != previous for previous in valid):
            valid.append(utc)
    valid.sort()
    if not valid:
        raise ClarificationNeeded({
            "status": "needs_clarification",
            "kind": "dst_gap",
            "question": f"{local_naive.isoformat()} did not occur in {zone.key} because clocks changed. Ask for the corrected local birth time.",
        })
    if len(valid) == 1:
        return valid[0]
    if fold_choice is None:
        raise ClarificationNeeded({
            "status": "needs_clarification",
            "kind": "dst_fold",
            "question": f"{local_naive.isoformat()} happened twice in {zone.key}. Which occurrence was it?",
            "choices": [
                {"index": "earlier", "local": valid[0].astimezone(zone).isoformat(), "utc": valid[0].isoformat()},
                {"index": "later", "local": valid[1].astimezone(zone).isoformat(), "utc": valid[1].isoformat()},
            ],
        })
    return valid[0] if fold_choice == "earlier" else valid[1]


def vimshottari(moon_longitude: float, birth_utc: datetime, zone: ZoneInfo) -> dict:
    nak_index = min(26, int(norm(moon_longitude) / NAKSHATRA_SPAN))
    progress = (norm(moon_longitude) - nak_index * NAKSHATRA_SPAN) / NAKSHATRA_SPAN
    lord_index = nak_index % len(DASHA_LORDS)
    lord, years = DASHA_LORDS[lord_index]
    balance = years * (1 - progress)
    cursor = birth_utc
    periods = []
    now_utc = datetime.now(timezone.utc)
    current_mahadasha = None

    for offset in range(len(DASHA_LORDS)):
        current_lord, full_years = DASHA_LORDS[(lord_index + offset) % len(DASHA_LORDS)]
        duration = balance if offset == 0 else full_years
        end = cursor + timedelta(days=duration * YEAR_DAYS)
        start_local = cursor.astimezone(zone).replace(microsecond=0)
        end_local = end.astimezone(zone).replace(microsecond=0)
        is_cur = (cursor <= now_utc < end)
        if is_cur:
            current_mahadasha = current_lord

        periods.append({
            "lord": current_lord,
            "portion": "balance at birth" if offset == 0 else "full period",
            "duration_years": round(duration, 4),
            "start_local": start_local.isoformat(),
            "end_local": end_local.isoformat(),
            "is_current": is_cur,
        })
        cursor = end

    res = {
        "system": "Vimshottari",
        "birth_nakshatra_lord": lord,
        "balance_years_at_birth": round(balance, 4),
        "mahadashas": periods,
    }
    if current_mahadasha:
        res["current_mahadasha"] = current_mahadasha
    return res


def markdown_to_reportlab_elements(md_text: str, styles) -> list:
    """Safely converts Markdown text into formatted ReportLab flowables."""
    from reportlab.platypus import Paragraph, Spacer
    from reportlab.lib.styles import ParagraphStyle

    # Custom styles for clean reading layout
    bullet_style = ParagraphStyle(
        "ReadingBullet",
        parent=styles["BodyText"],
        leftIndent=14,
        firstLineIndent=-10,
        spaceAfter=3,
        fontSize=9,
        leading=12,
    )
    quote_style = ParagraphStyle(
        "ReadingQuote",
        parent=styles["BodyText"],
        leftIndent=16,
        rightIndent=16,
        fontName="Helvetica-Oblique",
        spaceAfter=4,
        fontSize=9,
        leading=12,
    )
    body_style = ParagraphStyle(
        "ReadingBody",
        parent=styles["BodyText"],
        spaceAfter=5,
        fontSize=9.5,
        leading=13,
    )

    def format_inline(text: str) -> str:
        # Escape XML entities first
        escaped = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        # Bold: **text** or __text__
        escaped = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", escaped)
        escaped = re.sub(r"__(.+?)__", r"<b>\1</b>", escaped)
        # Italic: *text* or _text_
        escaped = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<i>\1</i>", escaped)
        escaped = re.sub(r"(?<!_)_(?!_)(.+?)(?<!_)_(?!_)", r"<i>\1</i>", escaped)
        # Inline code: `text`
        escaped = re.sub(r"`(.+?)`", r'<font name="Courier">\1</font>', escaped)
        return escaped

    elements = []
    lines = md_text.splitlines()
    for raw in lines:
        line = raw.strip()
        if not line:
            elements.append(Spacer(1, 4))
        elif line.startswith("#### "):
            elements.append(Paragraph(format_inline(line[5:]), styles["Heading4"]))
        elif line.startswith("### "):
            elements.append(Paragraph(format_inline(line[4:]), styles["Heading3"]))
        elif line.startswith("## "):
            elements.append(Spacer(1, 6))
            elements.append(Paragraph(format_inline(line[3:]), styles["Heading2"]))
        elif line.startswith("# "):
            elements.append(Spacer(1, 8))
            elements.append(Paragraph(format_inline(line[2:]), styles["Heading1"]))
        elif re.match(r"^[-*•]\s+", line):
            content = re.sub(r"^[-*•]\s+", "", line)
            elements.append(Paragraph(f"&bull; {format_inline(content)}", bullet_style))
        elif re.match(r"^\d+\.\s+", line):
            num_match = re.match(r"^(\d+\.)\s+(.+)$", line)
            if num_match:
                prefix = num_match.group(1)
                content = num_match.group(2)
                elements.append(Paragraph(f"<b>{prefix}</b> {format_inline(content)}", bullet_style))
            else:
                elements.append(Paragraph(format_inline(line), bullet_style))
        elif line.startswith("> "):
            elements.append(Paragraph(format_inline(line[2:]), quote_style))
        else:
            elements.append(Paragraph(format_inline(line), body_style))

    return elements


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", required=True, help="Local birth date, YYYY-MM-DD (e.g. 1990-03-12)")
    parser.add_argument("--time", required=True, help="Birth time as given locally; accepts clock time or simple phrases such as 'subah ke 4'")
    location = parser.add_mutually_exclusive_group(required=True)
    location.add_argument("--place", help="Birthplace name/address to geocode")
    location.add_argument("--latitude", type=float, help="Coordinates instead of a birthplace; requires --longitude")
    parser.add_argument("--longitude", type=float, help="Decimal degrees; east positive")
    parser.add_argument("--place-label", help="Optional readable name to retain when using selected coordinates")
    parser.add_argument("--timezone", help="IANA time zone override (e.g. Asia/Kolkata); auto-detected for --place")
    parser.add_argument("--timezone-choice", help="Select a time zone when coordinates overlap multiple zones")
    parser.add_argument("--nominatim-domain", default=os.environ.get("TRANSIT_LAB_NOMINATIM_DOMAIN", "nominatim.openstreetmap.org"), help="Nominatim-compatible geocoder host")
    parser.add_argument("--dst-fold", choices=["earlier", "later"], help="Select an occurrence when a clock time happened twice during a DST change")
    parser.add_argument("--pdf", help="Optional output PDF path")
    parser.add_argument("--reading", help="Optional UTF-8 text/Markdown interpretation to include in the PDF")
    args = parser.parse_args()

    if args.reading and not args.pdf:
        parser.error("--reading requires --pdf")
    if args.latitude is not None and args.longitude is None:
        parser.error("--latitude requires --longitude")
    if args.longitude is not None and args.latitude is None:
        parser.error("--longitude requires --latitude")

    try:
        birth_date = parse_date(args.date)
        birth_time = parse_local_time(args.time)
        local_naive = datetime.combine(birth_date, birth_time)

        if args.place:
            latitude, longitude, resolved_place = geocode_place(args.place, args.nominatim_domain)
        else:
            latitude, longitude, resolved_place = args.latitude, args.longitude, args.place_label or "Coordinates supplied by user"

        if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
            raise RuntimeError("Latitude must be -90..90 and longitude -180..180.")

        if args.timezone:
            timezone_name = args.timezone
        else:
            try:
                from timezonefinder import TimezoneFinder
            except ImportError as exc:
                raise RuntimeError("Automatic time-zone lookup needs timezonefinder. Install transit-lab/requirements.txt.") from exc
            tf = TimezoneFinder()
            zone_name = tf.timezone_at(lng=longitude, lat=latitude)
            if not zone_name:
                zone_name = tf.certain_timezone_at(lng=longitude, lat=latitude)

            if args.timezone_choice:
                timezone_name = args.timezone_choice
            elif not zone_name:
                raise RuntimeError("Couldn't identify a time zone at those coordinates. Supply --timezone with an IANA zone name.")
            else:
                timezone_name = zone_name

        try:
            zone = ZoneInfo(timezone_name)
        except ZoneInfoNotFoundError as exc:
            raise RuntimeError(f"Time-zone database has no entry for {timezone_name!r}. Check the place or install tzdata.") from exc

        birth_utc = local_to_utc(local_naive, zone, args.dst_fold)
    except ClarificationNeeded as exc:
        print(json.dumps(exc.payload, indent=2, ensure_ascii=False))
        return 3
    except (ValueError, RuntimeError) as exc:
        parser.error(str(exc))

    try:
        import swisseph as swe  # type: ignore
    except ImportError:
        print("Missing chart dependency. Install transit-lab/requirements.txt.", file=sys.stderr)
        return 2

    utc_hour = birth_utc.hour + birth_utc.minute / 60.0 + birth_utc.second / 3600.0 + birth_utc.microsecond / 3_600_000_000.0
    julian_day = swe.julday(birth_utc.year, birth_utc.month, birth_utc.day, utc_hour, swe.GREG_CAL)
    swe.set_sid_mode(swe.SIDM_LAHIRI)

    # Use FLG_SIDEREAL so all calculations are projected onto the exact Lahiri sidereal frame
    calc_flags = swe.FLG_SWIEPH | swe.FLG_SPEED | swe.FLG_SIDEREAL
    positions = {}
    returned_flags = {}

    for key, label in BODIES:
        body = swe.MEAN_NODE if key == "MeanNode" else getattr(swe, key.upper())
        coordinates, flags = swe.calc_ut(julian_day, body, calc_flags)
        positions[label] = coordinates
        returned_flags[label] = flags

    # Ketu is placed 180° opposite Rahu with identical speed
    rahu = positions["Rahu"]
    positions["Ketu"] = (norm(rahu[0] + 180.0), -rahu[1], rahu[2], rahu[3], 0.0, 0.0)
    returned_flags["Ketu"] = returned_flags["Rahu"]

    ayanamsha = swe.get_ayanamsa_ut(julian_day)
    sidereal = {name: norm(position[0]) for name, position in positions.items()}

    try:
        _, asc_mc = swe.houses_ex(julian_day, latitude, longitude, b"W", swe.FLG_SIDEREAL)
    except swe.Error as exc:
        parser.error(f"Jyotisha whole-sign ascendant calculation failed for this location: {exc}")

    sidereal_asc = norm(asc_mc[0])
    lagna_sign_index = int(sidereal_asc // 30)
    lagna_sign = SIGNS[lagna_sign_index]

    # Precompute whole-sign house assignments and house lords
    houses = {}
    for h in range(1, 13):
        sign_idx = (lagna_sign_index + h - 1) % 12
        h_sign = SIGNS[sign_idx]
        houses[str(h)] = {
            "sign": h_sign,
            "lord": SIGN_LORDS[h_sign],
        }

    planets = {}
    for name, longitude_sidereal in sidereal.items():
        house_num = ((int(longitude_sidereal // 30) - lagna_sign_index) % 12) + 1
        speed = positions[name][3]
        planets[name] = {
            **zodiac(longitude_sidereal),
            "whole_sign_house": house_num,
            "nakshatra": get_nakshatra(longitude_sidereal),
            "navamsa": navamsa(longitude_sidereal),
            "retrograde": speed < 0 if name not in ("Rahu", "Ketu") else None,
            "daily_motion_degrees": round(speed, 5),
        }

    moon_nak = get_nakshatra(sidereal["Moon"])
    local_aware = birth_utc.astimezone(zone)

    # Human-readable ephemeris identification
    sun_flags = returned_flags.get("Sun", 0)
    ephemeris_type = "Swiss Ephemeris (high-precision files)" if (sun_flags & swe.FLG_SWIEPH) else "Moshier analytical ephemeris"

    result = {
        "label": resolved_place,
        "birth": {
            "local_datetime": local_aware.isoformat(),
            "utc_datetime": birth_utc.isoformat(),
            "timezone": timezone_name,
            "utc_offset": local_aware.strftime("%z"),
        },
        "place": {
            "resolved_name": resolved_place,
            "latitude": round(latitude, 6),
            "longitude": round(longitude, 6),
            "geocoding_attribution": OSM_ATTRIBUTION if args.place else None,
        },
        "calculation": {
            "ayanamsha": "Lahiri/Chitrapaksha",
            "ayanamsha_degrees": round(ayanamsha, 6),
            "zodiac": "sidereal",
            "houses": "whole sign",
            "node": "mean Rahu; Ketu derived 180 degrees opposite",
            "dasha_year_days": YEAR_DAYS,
            "julian_day_ut": round(julian_day, 8),
            "ephemeris_engine": ephemeris_type,
            "ephemeris_flags_returned": returned_flags,
        },
        "jyotisha": {
            "lagna": {
                **zodiac(sidereal_asc),
                "nakshatra": get_nakshatra(sidereal_asc),
            },
            "navamsa_lagna": navamsa(sidereal_asc),
            "houses": houses,
            "planets": planets,
            "moon_nakshatra": moon_nak,
        },
        "vimshottari_dasha": vimshottari(sidereal["Moon"], birth_utc, zone),
        "limitations": [
            "Astrological interpretation is symbolic and not an empirically validated prediction method.",
            "This calculation includes D1, D9, Nakshatras, whole-sign houses, and Vimshottari mahadasha only; no antardasha, shadbala, or other vargas are calculated.",
        ],
    }

    print(json.dumps(result, indent=2, ensure_ascii=False))

    if args.pdf:
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import letter
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle, HRFlowable
        except ImportError:
            print("Missing PDF dependency. Install transit-lab/requirements.txt.", file=sys.stderr)
            return 2

        path = Path(args.pdf)
        path.parent.mkdir(parents=True, exist_ok=True)
        styles = getSampleStyleSheet()

        # Custom header styling
        title_style = ParagraphStyle("ChartTitle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=18, leading=22, textColor=colors.HexColor("#1b2a47"), alignment=0)
        subtitle_style = ParagraphStyle("ChartSubtitle", parent=styles["Normal"], fontSize=9, leading=13, textColor=colors.HexColor("#4a5568"))
        section_style = ParagraphStyle("SectionHead", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=12, leading=16, textColor=colors.HexColor("#1b2a47"), spaceBefore=10, spaceAfter=4)
        info_banner_style = ParagraphStyle("InfoBanner", parent=styles["Normal"], fontName="Helvetica", fontSize=9, leading=13, textColor=colors.HexColor("#1b2a47"))

        story = [
            Paragraph(f"Transit Lab — {resolved_place}", title_style),
            Spacer(1, 4),
            Paragraph(
                f"<b>Birth:</b> {local_aware.strftime('%Y-%m-%d %H:%M:%S')} {timezone_name} ({birth_utc.strftime('%Y-%m-%d %H:%M:%S')} UTC) &nbsp;|&nbsp; "
                f"<b>Coordinates:</b> {latitude:.4f}°, {longitude:.4f}° &nbsp;|&nbsp; "
                f"<b>System:</b> Lahiri Sidereal, Whole-Sign Houses",
                subtitle_style
            ),
            Spacer(1, 8),
            HRFlowable(width="100%", thickness=1, color=colors.HexColor("#cbd2dc"), spaceBefore=2, spaceAfter=8),
        ]

        # Key Ascendant & Moon banner
        lagna_data = result["jyotisha"]["lagna"]
        d9_lagna = result["jyotisha"]["navamsa_lagna"]
        banner_text = (
            f"<b>Lagna (Ascendant):</b> {lagna_data['sign']} {lagna_data['degree']:.2f}° "
            f"({lagna_data['nakshatra']['name']}, Pada {lagna_data['nakshatra']['pada']}) • Lord: {lagna_data['sign_lord']} &nbsp;|&nbsp; "
            f"<b>D9 Lagna:</b> {d9_lagna['sign']} • Lord: {d9_lagna['sign_lord']}<br/>"
            f"<b>Janma Nakshatra (Moon):</b> {moon_nak['name']}, Pada {moon_nak['pada']} • Lord: {moon_nak['lord']}"
        )
        banner_table = Table([[Paragraph(banner_text, info_banner_style)]], colWidths=[540])
        banner_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#eef2f7")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd2dc")),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ]))
        story.extend([banner_table, Spacer(1, 10)])

        # Planetary positions table
        story.append(Paragraph("Graha Placements (D1 & D9)", section_style))
        graha_rows = [["Graha", "Rāśi & Degree", "Lord", "Nakshatra (Pada)", "House", "D9 Navāṁśa", "Motion"]]
        for name in ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]:
            p = planets[name]
            motion = "Retrograde" if p["retrograde"] else ("Direct" if p["retrograde"] is False else "Mean Node")
            nak_str = f"{p['nakshatra']['name']} ({p['nakshatra']['pada']})"
            graha_rows.append([
                name,
                f"{p['sign']} {p['degree']:.2f}°",
                p["sign_lord"],
                nak_str,
                str(p["whole_sign_house"]),
                f"{p['navamsa']['sign']}",
                motion,
            ])

        graha_table = Table(graha_rows, colWidths=[60, 95, 60, 120, 45, 90, 70], repeatRows=1, hAlign="LEFT")
        graha_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1b2a47")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#cbd2dc")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("ALIGN", (4, 0), (4, -1), "CENTER"),
        ]))
        story.extend([graha_table, Spacer(1, 10)])

        # Vimshottari Mahadasha Table
        story.append(Paragraph("Vimshottari Mahadasha Periods", section_style))
        dasha_rows = [["Lord", "Portion", "Start Date (Local)", "End Date (Local)", "Status"]]
        for period in result["vimshottari_dasha"]["mahadashas"]:
            status = "Current" if period.get("is_current") else ""
            dasha_rows.append([
                period["lord"],
                period["portion"],
                period["start_local"][:10],
                period["end_local"][:10],
                status,
            ])
        dasha_table = Table(dasha_rows, colWidths=[70, 110, 120, 120, 120], repeatRows=1, hAlign="LEFT")
        dasha_style = [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1b2a47")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#cbd2dc")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]
        # Highlight current mahadasha row if present
        for row_idx, period in enumerate(result["vimshottari_dasha"]["mahadashas"], start=1):
            if period.get("is_current"):
                dasha_style.append(("BACKGROUND", (0, row_idx), (-1, row_idx), colors.HexColor("#e2e8f0")))
                dasha_style.append(("FONTNAME", (0, row_idx), (-1, row_idx), "Helvetica-Bold"))
        dasha_table.setStyle(TableStyle(dasha_style))
        story.extend([dasha_table, Spacer(1, 10)])

        # Reading Interpretation Section
        if args.reading:
            story.append(Paragraph("Astrological Interpretation", section_style))
            md_content = Path(args.reading).read_text(encoding="utf-8")
            story.extend(markdown_to_reportlab_elements(md_content, styles))
            story.append(Spacer(1, 8))

        # Method and limits footer note
        method_note = (
            f"<b>Calculation Method &amp; Limits:</b> Calculations computed via Swiss Ephemeris with Lahiri/Chitrapaksha ayanamsha "
            f"({ayanamsha:.4f}°) and whole-sign houses. Local time converted using IANA database ({timezone_name}). "
            f"{OSM_ATTRIBUTION if args.place else ''} Astrology is a cultural and reflective symbolic tradition; it does not substitute "
            f"for medical, legal, or financial professional guidance."
        )
        footer_style = ParagraphStyle("FooterNote", parent=styles["Normal"], fontSize=7.5, leading=10, textColor=colors.HexColor("#718096"))
        story.extend([Spacer(1, 6), Paragraph(method_note, footer_style)])

        def page_footer(canvas, doc):
            canvas.saveState()
            canvas.setFont("Helvetica", 8)
            canvas.setFillColor(colors.HexColor("#718096"))
            canvas.drawString(36, 20, f"Transit Lab • Jyotisha Chart ({resolved_place})")
            canvas.drawRightString(letter[0] - 36, 20, f"Page {doc.page}")
            canvas.restoreState()

        doc = SimpleDocTemplate(
            str(path),
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36,
            title=f"Transit Lab — {resolved_place}",
        )
        doc.build(story, onFirstPage=page_footer, onLaterPages=page_footer)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
