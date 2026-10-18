# Transit Lab

Transit Lab is a Jyotisha-only installable agent skill. The user can share a birthplace, date, and ordinary local time phrase; the LLM handles clarification and the calculator resolves coordinates, time zone, UTC conversion, chart placements, birth Panchanga, Vimshottari dasha periods, and current gochara. The LLM then writes the interpretation and can include it in a PDF.

## Install the skill

```sh
npx skills add DNRaina/transitlab --skill transit-lab
```

`skills add` is the Skills CLI install command (there is no `skills install <repo>` command). The CLI detects a supported agent, or you can target one explicitly, for example `--agent codex`, `--agent claude-code`, or `--agent antigravity`.

The public repository is installable directly from GitHub. I verified it with `npx skills add DNRaina/transitlab --list`; the CLI found the `transit-lab` skill and parsed its description. The `skills.sh` directory is an install leaderboard populated from anonymous CLI install telemetry, rather than a manual submission registry, so a valid skill can install before it appears in the directory. See the [skills.sh FAQ](https://www.skills.sh/docs/faq).

## Example

Install Python dependencies, then:

```sh
python -m pip install -r transit-lab/requirements.txt
python transit-lab/scripts/chart.py --date 1990-03-12 --time "subah ke 4" --place "Jaipur, India"
```

The script returns JSON. It sends only the city/town place query to OpenStreetMap's public Nominatim geocoder; name, birth date, and birth time are not sent to that service. The agent should disclose the lookup and follow the [Nominatim usage policy](https://operations.osmfoundation.org/policies/nominatim/). This is not end-to-end offline when used through a hosted LLM: the conversation is processed by the selected agent provider. To avoid geocoding, supply coordinates and a time zone.

Saving is opt-in. Add `--save-json charts/dhruv.json` to save the full chart locally as plain JSON. The file contains exact birth details and location; choose a private path. Add `--redact-birth-details` with `--pdf` to omit the auto-generated birth date/time/location from the PDF; keep them out of `interpretation.md` too, because the flag cannot redact arbitrary text. If a place, time zone, or clock time is ambiguous, the script returns choices for the agent to clarify with the user. To create a PDF, add `--pdf report.pdf --reading interpretation.md` after the agent has written the interpretation.

For an explicitly offline calculator run, pass `--offline`, coordinates, and an IANA `--timezone`. This disables birthplace geocoding; it does not make a hosted LLM conversation offline.

```sh
python transit-lab/scripts/chart.py --offline --date 1990-03-12 --time "subah ke 4" --latitude 26.91 --longitude 75.79 --timezone Asia/Kolkata --save-json charts/jaipur.json
```

For a local-calendar date range, add both dasha range bounds. The JSON and PDF will include the overlapping Mahadasha, Antardasha, and Pratyantardasha intervals, clipped to the selected dates:

```sh
python transit-lab/scripts/chart.py --date 1990-03-12 --time "subah ke 4" --place "Jaipur, India" --dasha-range-start 2026-01-01 --dasha-range-end 2026-03-31
```

The date range is inclusive and uses the birth location's time zone. Range reporting is descriptive timing data, not an event prediction.

See [the skill instructions](transit-lab/SKILL.md) and [methodology notes](transit-lab/references/methodology.md) for privacy boundaries, supported calculations, and limitations.

For a Nominatim-compatible geocoder you operate or have permission to use, override the host with `--nominatim-domain` or `TRANSIT_LAB_NOMINATIM_DOMAIN`.

## Licensing note

Swiss Ephemeris is dual licensed under AGPL and a commercial/professional license. Review its current terms before distributing an application or providing a service based on its calculations. See [methodology notes](transit-lab/references/methodology.md).
