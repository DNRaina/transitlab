---
name: transit-lab
description: Create source-aware Jyotisha birth-chart readings from natural-language birth details, including place lookup, local-time conversion, nakshatra, D9, Vimshottari mahadasha, and optional PDF. Use for Vedic astrology readings and reports.
---

# Transit Lab

Turn ordinary birth details into a careful Jyotisha chart and a readable, personalized interpretation. The user should be able to say something like “I was born in Jaipur on 12 March 1990, subah ke 4” without learning astrology software or date-time formats. The LLM handles clarification and orchestration; the script handles reproducible calculations.

## Workflow

1. Extract the birth date, local clock time, and birthplace from the conversation. Normalize the date to `YYYY-MM-DD` (the parser also accepts clean `/` and `-` date variants); retain the time as a local phrase such as `subah ke 4`, `dopahar 12:30`, or `4.30 pm`; pass the place as the user named it. Never treat local birth time as UTC.
   The command line is an internal tool: do not ask the user to install Python, run commands, look up coordinates, or convert time zones. Handle those steps yourself when the runtime permits.
   Reuse the chart JSON and resolved coordinates already produced for follow-up questions; do not repeat a geocoding request for the same birthplace.
2. Ask only for information that is missing or genuinely ambiguous. “Subah ke 4” is 04:00; “shaam ke 4” is 16:00; “dopahar 12” is noon; “raat ke 12” is midnight. If the user says only “4” or “4:30” without AM/PM or a period phrase, ask whether they mean morning (04:00/04:30) or afternoon/evening (16:00/16:30). Do not silently choose an AM/PM interpretation. For Hindi text, Devanagari numerals (`०-९`) and common Hindi time words (`सुबह`, `दोपहर`, `शाम`, `रात`, `बजे`) are supported by the calculator.
3. For automatic birthplace lookup, briefly disclose that a city/town-level place name (only) will be sent to OpenStreetMap's public Nominatim service, link its [usage policy](https://operations.osmfoundation.org/policies/nominatim/), and use it only for this user-triggered one-time lookup. Do not send a street address, hospital, full birth date, or birth time; if the user gives an exact address, reduce it to the city/town before lookup or ask for coordinates. If they prefer not to send the place, use coordinates instead. The script geocodes the birthplace, detects its IANA time zone from the coordinates, applies the historical UTC offset for that date, and calculates in UTC. Example:

   ```sh
   python <path-to-skill>/scripts/chart.py --date 1990-03-12 --time "subah ke 4" --place "Jaipur, India"
   ```

   (When installed into a project via `npx skills`, use `python .agents/skills/transit-lab/scripts/chart.py ...`; from this source repo root, use `python transit-lab/scripts/chart.py ...`.)

   If the returned JSON has `status: needs_clarification`, present its choices in plain language, get the user's choice, then rerun: pass a selected clock time to `--time`, a selected zone to `--timezone-choice`, or a repeated-hour choice to `--dst-fold`. For an ambiguous place, use the selected result's `--latitude`, `--longitude`, and `--place-label` directly on rerun instead of repeating the external lookup. If the place cannot be resolved, ask for a city/region/country or coordinates. The calculator detects the time zone from coordinates; `--timezone` can override it with an IANA name.
4. Use the returned JSON as the sole source for degrees, signs, sign lords, whole-sign house lords, retrograde status, lagna, nakshatra/pada, D9 navāṁśa, and Vimshottari mahadasha boundaries. Do not estimate these values or infer calculations that are absent. The chart defaults to sidereal zodiac, Lahiri/Chitrapaksha ayanamsha, whole-sign rāśi houses, and mean Rahu with Ketu opposite. These conventions are common but not universal; disclose them.
5. Write the interpretation yourself. Keep the calculated chart and the interpretation distinct: placements are data; meanings are tradition-specific judgments. Explain the chain from placement → rule → contextual factors → balanced reading. Consult `references/methodology.md` for calculation limits, geocoding privacy, and sourcing expectations.
6. Structure the reading around lagna and lagna lord, Moon and nakshatra, graha placements and house lords, relevant aspects/conjunctions, D9 context, and the Vimshottari mahadasha sequence (noting the active mahadasha). Use the precomputed `houses` map and `sign_lord` fields in the JSON to verify house rulerships. Explain why a factor matters and how other placements qualify it. Avoid generic sign descriptions, keyword piles, and unsupported yoga claims.
7. For shastra claims, name the text and edition/translator and give a chapter/verse only when verified. Never invent a Sanskrit quotation, verse number, lineage authority, or universal consensus. When a traditional rule cannot be verified, label it as a contemporary interpretive convention.
8. If the user asks for a PDF, write the completed reading to a UTF-8 Markdown file and run the script with `--pdf report.pdf --reading reading.md`. The PDF renders Markdown headings, bold, italics, bullet lists, and blockquotes alongside the chart tables, Vimshottari periods, and calculation notes. Open or share the created file when useful.

## Interpretation boundaries

- Treat astrology as a cultural and reflective practice, not an empirically validated prediction method. Use non-deterministic language; avoid fatalism and false precision.
- Do not give medical, legal, financial, safety, fertility, death, or relationship-ending predictions. Do not present gemstones, rituals, or costly remedies as guaranteed fixes. Encourage qualified professional advice for consequential decisions.
- The script sends only the city/town query to OpenStreetMap's public Nominatim geocoder; birth date and time stay local. Clearly disclose this before the first lookup and link its policy. Respect its one-request-per-second limit, moderate-use restriction, and attribution requirement. Use a different provider for higher-volume or commercial services.
- Exact birth details are sensitive. Include them in the reading only when useful; do not send the date or time to the geocoder.
- If the birth time is approximate or unknown, say that ascendant, houses, D9 lagna, and timing can shift. Offer a planet/nakshatra-led reading and avoid presenting time-dependent results as certain.

## Calculator limits

The script calculates D1, D9, Nakshatras/padas for all grahas and lagna, retrograde motion, and Vimshottari mahadasha periods. It does not calculate antardasha, shadbala, other vargas, yogas, or event predictions. Do not claim results for features it does not compute.
