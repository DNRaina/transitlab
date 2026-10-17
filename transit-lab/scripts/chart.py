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

SIGNS = ["Mesha", "Vrishabha", "Mithuna", "Karka", "Simha", "Kanya", "Tula", "Vrischika", "Dhanu", "Makara", "Kumbha", "Meena"]
NAKSHATRAS = ["Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra", "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha", "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta", "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada", "Revati"]
DASHA_LORDS = [("Ketu", 7), ("Venus", 20), ("Sun", 6), ("Moon", 10), ("Mars", 7), ("Rahu", 18), ("Jupiter", 16), ("Saturn", 19), ("Mercury", 17)]
BODIES = [("Sun", "Sun"), ("Moon", "Moon"), ("Mercury", "Mercury"), ("Venus", "Venus"), ("Mars", "Mars"), ("Jupiter", "Jupiter"), ("Saturn", "Saturn"), ("MeanNode", "Rahu")]
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
    return {"sign": SIGNS[index], "degree": round(value - index * 30, 5), "longitude": round(value, 5)}


def navamsa(longitude: float) -> dict:
    value = norm(longitude)
    rasi = int(value // 30)
    pada = int((value % 30) // (30 / 9))
    start_sign = {0: rasi, 1: (rasi + 8) % 12, 2: (rasi + 4) % 12}[rasi % 3]
    return {"sign": SIGNS[(start_sign + pada) % 12], "pada": pada + 1}


def parse_local_time(value: str) -> time:
    raw = value.strip().lower()
    for devanagari, digit in zip("०१२३४५६७८९", "0123456789"):
        raw = raw.replace(devanagari, digit)
    match = re.search(r"(?<!\d)(\d{1,2})(?::([0-5]\d))?(?::([0-5]\d))?(?:\s*([ap])\.?m\.?)?", raw)
    if not match:
        raise ValueError("I couldn't read that time. Use a clock time or a phrase such as 'subah ke 4'.")
    hour, minute, second = int(match.group(1)), int(match.group(2) or 0), int(match.group(3) or 0)
    meridiem = match.group(4)
    morning = any(word in raw for word in ("subah", "सुबह", "morning", "dawn"))
    afternoon = any(word in raw for word in ("dopahar", "दोपहर", "afternoon", "shaam", "शाम", "saanjh", "साँझ", "सांझ", "evening"))
    night = any(word in raw for word in ("raat", "रात", "night"))
    if meridiem:
        if not 1 <= hour <= 12:
            raise ValueError("For AM/PM time, the hour must be 1 through 12.")
        hour = hour % 12 + (12 if meridiem == "p" else 0)
    elif morning:
        if not 1 <= hour <= 12:
            raise ValueError("That morning time is outside the 1–12 hour range.")
        hour %= 12
    elif afternoon:
        if not 1 <= hour <= 12:
            raise ValueError("That afternoon/evening time is outside the 1–12 hour range.")
        hour = hour % 12 + (12 if hour != 12 else 0)
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
            raise ClarificationNeeded({"status": "needs_clarification", "kind": "time", "question": f"Does {value!r} mean midnight or noon?", "choices": choices})
        first_choice = f"{hour % 12:02d}:{minute:02d}:{second:02d}"
        second_choice = f"{(hour % 12) + 12:02d}:{minute:02d}:{second:02d}"
        raise ClarificationNeeded({"status": "needs_clarification", "kind": "time", "question": f"Does {value!r} mean morning ({first_choice}) or afternoon/evening ({second_choice})?", "choices": [first_choice, second_choice]})
    elif not 0 <= hour <= 23:
        raise ValueError("Hour must be between 0 and 23.")
    return time(hour, minute, second)


def geocode_place(query: str, domain: str) -> tuple[float, float, str]:
    try:
        from geopy.geocoders import Nominatim
        from geopy.extra.rate_limiter import RateLimiter
    except ImportError as exc:
        raise RuntimeError("Place lookup needs the optional geocoding dependencies. Install transit-lab/requirements.txt.") from exc
    try:
        geocoder = Nominatim(domain=domain, scheme="https", user_agent="transit-lab/0.2 (https://github.com/DNRaina/transitlab)", timeout=15)
        lookup = RateLimiter(geocoder.geocode, min_delay_seconds=1.1, max_retries=1, error_wait_seconds=2, swallow_exceptions=False)
        matches = lookup(query, exactly_one=False, limit=5, addressdetails=True) or []
    except Exception as exc:
        raise RuntimeError(f"Birthplace lookup failed ({exc.__class__.__name__}). Check the place spelling or provide coordinates and a time zone.") from exc
    # Collapse duplicate map features for the same named place and near-identical point.
    candidates = []
    seen = set()
    for item in matches:
        key = (round(item.latitude, 3), round(item.longitude, 3))
        if key not in seen:
            seen.add(key)
            candidates.append(item)
    if not candidates:
        raise RuntimeError(f"No place match for {query!r}. Add a region/country or provide coordinates.")
    if len(candidates) > 1:
        raise ClarificationNeeded({
            "status": "needs_clarification", "kind": "place",
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
        raise ClarificationNeeded({"status": "needs_clarification", "kind": "dst_gap", "question": f"{local_naive.isoformat()} did not occur in {zone.key} because clocks changed. Ask for the corrected local birth time."})
    if len(valid) == 1:
        return valid[0]
    if fold_choice is None:
        raise ClarificationNeeded({"status": "needs_clarification", "kind": "dst_fold", "question": f"{local_naive.isoformat()} happened twice in {zone.key}. Which occurrence was it?", "choices": [
            {"index": "earlier", "local": valid[0].astimezone(zone).isoformat(), "utc": valid[0].isoformat()},
            {"index": "later", "local": valid[1].astimezone(zone).isoformat(), "utc": valid[1].isoformat()},
        ]})
    return valid[0] if fold_choice == "earlier" else valid[1]


def vimshottari(moon_longitude: float, birth_utc: datetime, zone: ZoneInfo) -> dict:
    nak_index = min(26, int(norm(moon_longitude) / NAKSHATRA_SPAN))
    progress = (norm(moon_longitude) - nak_index * NAKSHATRA_SPAN) / NAKSHATRA_SPAN
    lord_index = nak_index % len(DASHA_LORDS)
    lord, years = DASHA_LORDS[lord_index]
    balance = years * (1 - progress)
    cursor = birth_utc
    periods = []
    for offset in range(len(DASHA_LORDS)):
        current_lord, full_years = DASHA_LORDS[(lord_index + offset) % len(DASHA_LORDS)]
        duration = balance if offset == 0 else full_years
        end = cursor + timedelta(days=duration * YEAR_DAYS)
        periods.append({
            "lord": current_lord,
            "portion": "balance at birth" if offset == 0 else "full period",
            "duration_years": round(duration, 4),
            "start_local": cursor.astimezone(zone).isoformat(),
            "end_local": end.astimezone(zone).isoformat(),
        })
        cursor = end
    return {"system": "Vimshottari", "birth_nakshatra_lord": lord, "balance_years_at_birth": round(balance, 4), "mahadashas": periods}


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", required=True, help="Local birth date, YYYY-MM-DD (the agent can normalize natural-language dates)")
    parser.add_argument("--time", required=True, help="Birth time as given locally; accepts clock time or simple phrases such as 'subah ke 4'")
    location = parser.add_mutually_exclusive_group(required=True)
    location.add_argument("--place", help="Birthplace name/address to geocode")
    location.add_argument("--latitude", type=float, help="Coordinates instead of a birthplace; requires --longitude")
    parser.add_argument("--longitude", type=float, help="Decimal degrees; east positive")
    parser.add_argument("--place-label", help="Optional readable name to retain when using selected coordinates")
    parser.add_argument("--timezone", help="IANA time zone override (e.g. Asia/Kolkata); auto-detected for --place")
    parser.add_argument("--timezone-choice", help="Select a time zone when the coordinates overlap multiple zones")
    parser.add_argument("--nominatim-domain", default=os.environ.get("TRANSIT_LAB_NOMINATIM_DOMAIN", "nominatim.openstreetmap.org"), help="Nominatim-compatible geocoder host; may also be set with TRANSIT_LAB_NOMINATIM_DOMAIN")
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
        birth_date = date.fromisoformat(args.date)
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
                from timezonefinder import timezones_at
            except ImportError as exc:
                raise RuntimeError("Automatic time-zone lookup needs timezonefinder. Install transit-lab/requirements.txt.") from exc
            timezone_matches = timezones_at(lng=longitude, lat=latitude)
            if not timezone_matches:
                raise RuntimeError("Couldn't identify a time zone at those coordinates. Supply --timezone with an IANA zone name.")
            if args.timezone_choice:
                if args.timezone_choice not in timezone_matches:
                    raise RuntimeError(f"--timezone-choice must be one of: {', '.join(timezone_matches)}")
                timezone_name = args.timezone_choice
            elif len(timezone_matches) > 1:
                raise ClarificationNeeded({"status": "needs_clarification", "kind": "timezone", "question": "The birthplace coordinates lie in an overlapping time-zone area. Which local civil time zone was used for the birth time?", "choices": timezone_matches})
            else:
                timezone_name = timezone_matches[0]
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
        import swisseph as swe
    except ImportError:
        print("Missing chart dependency. Install transit-lab/requirements.txt.", file=sys.stderr)
        return 2

    utc_hour = birth_utc.hour + birth_utc.minute / 60 + birth_utc.second / 3600 + birth_utc.microsecond / 3_600_000_000
    julian_day = swe.julday(birth_utc.year, birth_utc.month, birth_utc.day, utc_hour, swe.GREG_CAL)
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    calc_flags = swe.FLG_SWIEPH | swe.FLG_SPEED
    positions = {}
    returned_flags = {}
    for key, label in BODIES:
        body = swe.MEAN_NODE if key == "MeanNode" else getattr(swe, key.upper())
        coordinates, flags = swe.calc_ut(julian_day, body, calc_flags)
        positions[label] = coordinates
        returned_flags[label] = flags
    positions["Ketu"] = ((positions["Rahu"][0] + 180) % 360, -positions["Rahu"][1], 0, positions["Rahu"][3], 0, 0)
    returned_flags["Ketu"] = returned_flags["Rahu"]
    ayanamsha = swe.get_ayanamsa_ut(julian_day)
    sidereal = {name: norm(position[0] - ayanamsha) for name, position in positions.items()}

    try:
        _, asc_mc = swe.houses_ex(julian_day, latitude, longitude, b"W", swe.FLG_SIDEREAL)
    except swe.Error as exc:
        parser.error(f"Jyotisha whole-sign ascendant calculation failed for this location: {exc}")
    sidereal_asc = norm(asc_mc[0])

    planets = {}
    for name, longitude_sidereal in sidereal.items():
        house = ((int(longitude_sidereal // 30) - int(sidereal_asc // 30)) % 12) + 1
        planets[name] = {
            **zodiac(longitude_sidereal),
            "whole_sign_house": house,
            "navamsa": navamsa(longitude_sidereal),
            "retrograde": positions[name][3] < 0 if name not in ("Rahu", "Ketu") else None,
        }
    moon_nak_index = min(26, int(sidereal["Moon"] / NAKSHATRA_SPAN))
    moon_pada = int((sidereal["Moon"] - moon_nak_index * NAKSHATRA_SPAN) / (NAKSHATRA_SPAN / 4)) + 1
    local_aware = birth_utc.astimezone(zone)
    result = {
        "label": resolved_place,
        "birth": {"local_datetime": local_aware.isoformat(), "utc_datetime": birth_utc.isoformat(), "timezone": timezone_name, "utc_offset": local_aware.strftime("%z")},
        "place": {"resolved_name": resolved_place, "latitude": round(latitude, 6), "longitude": round(longitude, 6), "geocoding_attribution": OSM_ATTRIBUTION if args.place else None},
        "calculation": {"ayanamsha": "Lahiri/Chitrapaksha", "ayanamsha_degrees": round(ayanamsha, 6), "zodiac": "sidereal", "houses": "whole sign", "node": "mean Rahu; Ketu derived 180 degrees opposite", "dasha_year_days": YEAR_DAYS, "julian_day_ut": round(julian_day, 8), "ephemeris_flags_returned": returned_flags},
        "jyotisha": {"lagna": zodiac(sidereal_asc), "navamsa_lagna": navamsa(sidereal_asc), "planets": planets, "moon_nakshatra": {"name": NAKSHATRAS[moon_nak_index], "pada": moon_pada, "lord": DASHA_LORDS[moon_nak_index % 9][0]}},
        "vimshottari_dasha": vimshottari(sidereal["Moon"], birth_utc, zone),
        "limitations": ["Astrological interpretation is symbolic and not an empirically validated prediction method.", "This calculation includes D1, D9, Moon nakshatra, and Vimshottari mahadasha only; no antardasha, shadbala, or other vargas are calculated."],
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))

    if args.pdf:
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import letter
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
        except ImportError:
            print("Missing PDF dependency. Install transit-lab/requirements.txt.", file=sys.stderr)
            return 2
        path = Path(args.pdf)
        path.parent.mkdir(parents=True, exist_ok=True)
        styles = getSampleStyleSheet()
        story = [Paragraph(f"Transit Lab — {resolved_place}", styles["Title"]), Spacer(1, 10),
                 Paragraph(f"Birth: {local_aware.isoformat()} ({birth_utc.isoformat()} UTC)", styles["BodyText"]),
                 Paragraph(f"Coordinates: {latitude:.5f}, {longitude:.5f} | Jyotisha: Lahiri sidereal, whole-sign houses", styles["BodyText"]), Spacer(1, 12)]
        rows = [["Graha", "Rāśi", "House", "D9", "Motion"]]
        for name in ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]:
            planet = planets[name]
            motion = "Retrograde" if planet["retrograde"] else ("Direct" if planet["retrograde"] is False else "Node")
            rows.append([name, f"{planet['sign']} {planet['degree']:.2f}°", str(planet["whole_sign_house"]), planet["navamsa"]["sign"], motion])
        table = Table(rows, repeatRows=1, hAlign="LEFT")
        table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#23314d")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("GRID", (0, 0), (-1, -1), .35, colors.HexColor("#cbd2dc")), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f3f5f8")]), ("FONTSIZE", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 6), ("TOPPADDING", (0, 0), (-1, -1), 6)]))
        story += [table, Spacer(1, 12), Paragraph("Lagna", styles["Heading2"]), Paragraph(f"{result['jyotisha']['lagna']['sign']} {result['jyotisha']['lagna']['degree']:.2f}° | D9 lagna: {result['jyotisha']['navamsa_lagna']['sign']}", styles["BodyText"]), Paragraph(f"Moon nakshatra: {NAKSHATRAS[moon_nak_index]}, pada {moon_pada}; lord {DASHA_LORDS[moon_nak_index % 9][0]}", styles["BodyText"]), Spacer(1, 10), Paragraph("Vimshottari mahadasha periods", styles["Heading2"])]
        dasha_rows = [["Lord", "Portion", "From (local)", "To (local)"]]
        for period in result["vimshottari_dasha"]["mahadashas"]:
            dasha_rows.append([period["lord"], period["portion"], period["start_local"][:10], period["end_local"][:10]])
        dasha_table = Table(dasha_rows, repeatRows=1, hAlign="LEFT")
        dasha_table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#23314d")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("GRID", (0, 0), (-1, -1), .35, colors.HexColor("#cbd2dc")), ("FONTSIZE", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 5), ("TOPPADDING", (0, 0), (-1, -1), 5)]))
        story.append(dasha_table)
        if args.reading:
            story += [Spacer(1, 16), Paragraph("Reading", styles["Heading1"])]
            for raw in Path(args.reading).read_text(encoding="utf-8").splitlines():
                line = raw.strip()
                if not line:
                    story.append(Spacer(1, 5))
                elif line.startswith("### "):
                    story.append(Paragraph(line[4:], styles["Heading3"]))
                elif line.startswith("## "):
                    story.append(Paragraph(line[3:], styles["Heading2"]))
                elif line.startswith("# "):
                    story.append(Paragraph(line[2:], styles["Heading1"]))
                else:
                    escaped = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                    story.append(Paragraph(escaped, styles["BodyText"]))
        story += [Spacer(1, 12), Paragraph("Method and limits", styles["Heading2"]), Paragraph(f"Positions use Swiss Ephemeris with Lahiri/Chitrapaksha ayanamsha and whole-sign houses. Birth time converted from {timezone_name} to UTC using the time-zone database. {OSM_ATTRIBUTION if args.place else ''} Astrology is symbolic and should not replace professional advice.", styles["BodyText"])]
        def footer(canvas, doc):
            canvas.saveState(); canvas.setFont("Helvetica", 8); canvas.setFillColor(colors.grey); canvas.drawString(36, 22, "Transit Lab • Jyotisha chart") ; canvas.drawRightString(letter[0] - 36, 22, f"Page {doc.page}"); canvas.restoreState()
        SimpleDocTemplate(str(path), pagesize=letter, rightMargin=36, leftMargin=36, topMargin=40, bottomMargin=40, title=f"Transit Lab — {resolved_place}").build(story, onFirstPage=footer, onLaterPages=footer)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
