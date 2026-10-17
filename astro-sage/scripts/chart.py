#!/usr/bin/env python3
"""Calculate a compact dual Jyotisha/Western natal chart and optional PDF."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
VEDIC_SIGNS = ["Mesha", "Vrishabha", "Mithuna", "Karka", "Simha", "Kanya", "Tula", "Vrischika", "Dhanu", "Makara", "Kumbha", "Meena"]
BODIES = [("Sun", "Sun"), ("Moon", "Moon"), ("Mercury", "Mercury"), ("Venus", "Venus"), ("Mars", "Mars"), ("Jupiter", "Jupiter"), ("Saturn", "Saturn"), ("Uranus", "Uranus"), ("Neptune", "Neptune"), ("Pluto", "Pluto"), ("MeanNode", "Mean Node")]


def norm(x: float) -> float:
    return x % 360.0


def zodiac(longitude: float, signs: list[str]) -> dict:
    value = norm(longitude)
    idx = int(value // 30)
    degree = value - idx * 30
    return {"sign": signs[idx], "degree": round(degree, 5), "longitude": round(value, 5)}


def navamsa(longitude: float) -> dict:
    # Each navamsa is 3°20'. Start sign depends on movable/fixed/dual modality.
    value = norm(longitude)
    rasi = int(value // 30)
    pada = int((value % 30) // (30 / 9))
    modality = rasi % 3  # 0 movable, 1 fixed, 2 dual
    start = {0: rasi, 1: (rasi + 8) % 12, 2: (rasi + 4) % 12}[modality]
    return {"sign": VEDIC_SIGNS[(start + pada) % 12], "pada": pada + 1}


def house_for(lon: float, asc: float) -> int:
    # Whole-sign houses start at 0° of the rising sign, not at the ascendant degree.
    return ((int(norm(lon) // 30) - int(norm(asc) // 30)) % 12) + 1


def aspect_name(angle: float) -> tuple[str, float] | None:
    targets = [(0, "conjunction", 8), (60, "sextile", 5), (90, "square", 7), (120, "trine", 7), (180, "opposition", 8)]
    for target, name, orb in targets:
        delta = abs(angle - target)
        if delta <= orb:
            return name, round(delta, 3)
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--datetime", required=True, help="Local ISO-8601 birth time with explicit UTC offset, e.g. 1990-05-17T14:30:00+05:30")
    parser.add_argument("--latitude", required=True, type=float, help="Decimal degrees; north positive")
    parser.add_argument("--longitude", required=True, type=float, help="Decimal degrees; east positive")
    parser.add_argument("--name", default="", help="Optional chart label")
    parser.add_argument("--pdf", help="Optional output PDF path")
    parser.add_argument("--reading", help="Optional UTF-8 text/Markdown interpretation to include in the PDF")
    args = parser.parse_args()

    try:
        local = datetime.fromisoformat(args.datetime)
    except ValueError as exc:
        parser.error(f"invalid --datetime: {exc}")
    if local.tzinfo is None or local.utcoffset() is None:
        parser.error("--datetime must include a UTC offset; the script does not guess time zones")
    if not -90 <= args.latitude <= 90 or not -180 <= args.longitude <= 180:
        parser.error("latitude must be -90..90 and longitude -180..180")

    try:
        import swisseph as swe
    except ImportError:
        print("Missing dependency. Run: pip install -r requirements.txt", file=sys.stderr)
        return 2

    utc = local.astimezone(timezone.utc)
    hour = utc.hour + utc.minute / 60 + (utc.second + utc.microsecond / 1e6) / 3600
    jd = swe.julday(utc.year, utc.month, utc.day, hour, swe.GREG_CAL)
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    flags = swe.FLG_SWIEPH | swe.FLG_SPEED
    tropical: dict[str, float] = {}
    actual_flags: dict[str, int] = {}
    for key, label in BODIES:
        body = getattr(swe, "MEAN_NODE") if key == "MeanNode" else getattr(swe, key.upper())
        xx, retflags = swe.calc_ut(jd, body, flags)
        tropical[label] = norm(xx[0])
        actual_flags[label] = retflags

    ayanamsha = swe.get_ayanamsa_ut(jd)
    sidereal = {name: norm(lon - ayanamsha) for name, lon in tropical.items()}
    # Placidus tropical houses; whole-sign Jyotisha houses from sidereal lagna.
    western_cusps, western_ascmc = swe.houses_ex(jd, args.latitude, args.longitude, b"P")
    sid_cusps, sid_ascmc = swe.houses_ex(jd, args.latitude, args.longitude, b"W", swe.FLG_SIDEREAL)
    tropical_asc = western_ascmc[0]
    sidereal_asc = sid_ascmc[0]

    jyotisha_planets = {}
    western_planets = {}
    for name in tropical:
        jyotisha_planets[name] = {
            **zodiac(sidereal[name], VEDIC_SIGNS),
            "whole_sign_house": house_for(sidereal[name], sidereal_asc),
            "navamsa": navamsa(sidereal[name]),
        }
        western_planets[name] = {**zodiac(tropical[name], SIGNS), "placidus_house": None}
    # Convert house cusp arcs into integer placements, preserving wrap-around.
    for name, lon in tropical.items():
        western_planets[name]["placidus_house"] = next(
            (i + 1 for i in range(12) if norm(lon - western_cusps[i]) < norm(western_cusps[(i + 1) % 12] - western_cusps[i])),
            None,
        )

    # Aspect set: traditional major planets, plus outer planets, excluding node.
    aspects = []
    names = [n for n in tropical if n != "Mean Node"]
    for i, left in enumerate(names):
        for right in names[i + 1:]:
            separation = abs(norm(tropical[left] - tropical[right]))
            separation = min(separation, 360 - separation)
            found = aspect_name(separation)
            if found:
                aspects.append({"body1": left, "body2": right, "aspect": found[0], "orb_degrees": found[1]})

    result = {
        "label": args.name,
        "birth_datetime_local": local.isoformat(),
        "birth_datetime_utc": utc.isoformat(),
        "coordinates": {"latitude": args.latitude, "longitude": args.longitude},
        "calculation": {
            "julian_day_ut": round(jd, 8), "ayanamsha": "Lahiri/Chitrapaksha", "ayanamsha_degrees": round(ayanamsha, 6),
            "node": "mean", "jyotisha_houses": "whole sign", "western_houses": "Placidus", "western_zodiac": "tropical",
            "ephemeris_flags_returned": actual_flags,
        },
        "jyotisha": {"lagna": zodiac(sidereal_asc, VEDIC_SIGNS), "planets": jyotisha_planets},
        "western": {"ascendant": zodiac(tropical_asc, SIGNS), "mc": zodiac(western_ascmc[1], SIGNS), "planets": western_planets, "major_aspects": aspects},
        "limitations": ["Symbolic astrology reading; not an empirically validated prediction method.", "D9 is computed; no daśā periods, bala metrics, or other vargas are calculated."],
    }
    payload = json.dumps(result, indent=2, ensure_ascii=False)
    print(payload)
    if args.pdf:
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import letter
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
        except ImportError:
            print("Missing PDF dependency. Run: pip install -r requirements.txt", file=sys.stderr)
            return 2
        path = Path(args.pdf)
        path.parent.mkdir(parents=True, exist_ok=True)
        styles = getSampleStyleSheet()
        story = [Paragraph(args.name or "Natal Chart Calculation", styles["Title"]), Spacer(1, 12),
                 Paragraph(f"Local birth time: {local.isoformat()} | UTC: {utc.isoformat()}", styles["BodyText"]),
                 Paragraph(f"Coordinates: {args.latitude:.5f}, {args.longitude:.5f} | Jyotisha: Lahiri, whole sign, mean node | Western: tropical, Placidus", styles["BodyText"]), Spacer(1, 14)]
        rows = [["Body", "Jyotisha D1", "House", "D9", "Western", "House"]]
        for name in tropical:
            v, w = jyotisha_planets[name], western_planets[name]
            rows.append([name, f"{v['sign']} {v['degree']:.2f}°", str(v['whole_sign_house']), v['navamsa']['sign'], f"{w['sign']} {w['degree']:.2f}°", str(w['placidus_house'] or "—")])
        rows.extend([["Lagna / Asc", f"{zodiac(sidereal_asc, VEDIC_SIGNS)['sign']} {zodiac(sidereal_asc, VEDIC_SIGNS)['degree']:.2f}°", "1", "—", f"{zodiac(tropical_asc, SIGNS)['sign']} {zodiac(tropical_asc, SIGNS)['degree']:.2f}°", "1"]])
        table = Table(rows, repeatRows=1, hAlign="LEFT")
        table.setStyle(TableStyle([("BACKGROUND", (0,0),(-1,0), colors.HexColor("#23314d")), ("TEXTCOLOR",(0,0),(-1,0),colors.white), ("GRID",(0,0),(-1,-1),.35,colors.HexColor("#cbd2dc")), ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#f3f5f8")]), ("FONTSIZE",(0,0),(-1,-1),8), ("BOTTOMPADDING",(0,0),(-1,-1),6), ("TOPPADDING",(0,0),(-1,-1),6)]))
        story += [table]
        if args.reading:
            story += [Spacer(1, 18), Paragraph("Interpretation", styles["Heading1"])]
            reading_text = Path(args.reading).read_text(encoding="utf-8")
            for raw in reading_text.splitlines():
                line = raw.strip()
                if not line:
                    story.append(Spacer(1, 6))
                elif line.startswith("### "):
                    story.append(Paragraph(line[4:], styles["Heading3"]))
                elif line.startswith("## "):
                    story.append(Paragraph(line[3:], styles["Heading2"]))
                elif line.startswith("# "):
                    story.append(Paragraph(line[2:], styles["Heading1"]))
                else:
                    safe = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                    story.append(Paragraph(safe, styles["BodyText"]))
        story += [Spacer(1, 16), Paragraph("Calculation notes and limits", styles["Heading2"]), Paragraph("Positions are calculated with Swiss Ephemeris. Birth time and coordinate accuracy affect angles and houses. Astrological interpretation is symbolic and should not replace qualified professional advice.", styles["BodyText"])]
        def footer(canvas, doc):
            canvas.saveState(); canvas.setFont("Helvetica", 8); canvas.setFillColor(colors.grey); canvas.drawString(36, 22, "Astro Sage • Chart data, not a prediction") ; canvas.drawRightString(letter[0]-36, 22, f"Page {doc.page}"); canvas.restoreState()
        SimpleDocTemplate(str(path), pagesize=letter, rightMargin=36, leftMargin=36, topMargin=40, bottomMargin=40, title="Natal Chart").build(story, onFirstPage=footer, onLaterPages=footer)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
