---
name: astro-sage
description: Calculate and explain a natal chart using Jyotisha and Western astrology, grounded in stated traditions and sources, and create a polished PDF reading. Use when asked for birth-chart calculations, Vedic or Western natal interpretation, or a chart-reading PDF.
---

# Astro Sage

Create careful, transparent natal chart readings that combine classical Jyotisha and modern Western astrology without blending their assumptions. Use the calculation script for positions; never estimate planetary degrees mentally or invent placements.

## Workflow

1. Collect birth date, exact local birth time, named time zone or UTC offset, birthplace, and latitude/longitude. Ask whether the time is exact or approximate. If time/place is unknown, do not claim accurate ascendant, houses, divisional charts, or timing periods.
2. Confirm the convention before calculation: default Jyotisha uses sidereal zodiac with Lahiri/Chitrapaksha ayanamsha, whole-sign rāśi houses, mean lunar node, and D1 plus D9; Western uses tropical zodiac, Placidus houses, and major aspects. These are defaults, not universal rules. Say that other lineages/settings may differ.
3. Run `scripts/chart.py` with the supplied ISO-8601 datetime including a UTC offset and coordinates. Example:

   ```sh
   python scripts/chart.py --datetime "1990-05-17T14:30:00+05:30" --latitude 19.076 --longitude 72.8777 --name "Example"
   ```

   Add `--pdf reading.pdf` to create a PDF, and `--reading interpretation.md` to include the agent's completed UTF-8 text/Markdown reading. The script writes a JSON chart to stdout. Keep the JSON with the reading so calculations can be checked. Dependencies: `pip install -r requirements.txt`.
4. Interpret the Jyotisha and Western charts in separate sections, then offer a short synthesis that distinguishes shared themes from differences. Cover chart context first, then luminaries/lagna, personal planets, houses, major patterns, strengths, tensions, and practical reflection. In Jyotisha, explain lordship and house context before making a claim; distinguish sign dignity, house placement, aspects, and conjunctions. Do not assert a yoga just because a keyword pattern appears: show the rule and check relevant conditions.
5. Cite tradition-specific claims with a named text, chapter/verse or reputable scholarly/translation reference when available. Do not fabricate verses, quotations, lineage authority, or certainty. Use `references/methodology.md` for calculation conventions; add verified source notes to the reading when making shastra-specific claims. If the source cannot be verified, label the interpretation as a contemporary interpretive convention.
6. Treat astrology as a cultural and reflective practice, not an empirically validated prediction method. Use non-deterministic language. Do not give medical, legal, financial, safety, fertility, death, or relationship-ending predictions; do not recommend gemstones, rituals, or costly remedies as guaranteed fixes. For consequential decisions, encourage evidence-based advice from an appropriate professional.
7. Protect birth details: process only what the user provides, do not send them to third parties, and avoid repeating exact birth details in the reading unless useful and requested.

## Reading quality

- Be specific to the computed chart and explain the reasoning chain from placement to interpretation.
- State data quality, timezone/coordinates, house systems, ayanamsha, node convention, and any uncertainty that affects angles or houses.
- Keep symbolic meanings distinct from factual claims. Avoid generic lists, fatalism, and false precision in event timing.
- When a birth time is approximate, explain how a small time change can alter the ascendant, houses, and D9; offer a planet-only reading instead.
- PDF output should have a clear title, contents-like headings, readable tables, page numbers, and a concise methods/limits note. Never present the PDF as a substitute for an astrologer or professional advice.

## Script limits

The script calculates chart positions and exports a plain, reviewable PDF. It does not generate interpretations, determine birth time, run daśā timing, or validate textual yoga rules. The agent supplies interpretation from verified sources and should not infer absent calculations.
