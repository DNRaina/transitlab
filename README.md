# Transit Lab

Transit Lab is a Jyotisha-only installable agent skill. The user can share a birthplace, date, and ordinary local time phrase; the LLM handles clarification and the calculator resolves coordinates, time zone, UTC conversion, chart placements, and Vimshottari mahadasha. The LLM then writes the interpretation and can include it in a PDF.

## Install the skill

```sh
npx skills add DNRaina/transitlab --skill transit-lab
```

The Skills CLI installs the same skill format into Codex, Claude Code, Antigravity, and other supported agents.

## Example

Install Python dependencies, then:

```sh
python -m pip install -r transit-lab/requirements.txt
python transit-lab/scripts/chart.py --date 1990-03-12 --time "subah ke 4" --place "Jaipur, India"
```

The script returns JSON. It sends only the place string to the OpenStreetMap Nominatim geocoder; time-zone lookup and birth-time conversion run locally. The agent should disclose this lookup and follow the [Nominatim usage policy](https://operations.osmfoundation.org/policies/nominatim/). If a place, time zone, or clock time is ambiguous, it returns choices for the agent to clarify with the user. To create a PDF, add `--pdf report.pdf --reading interpretation.md` after the agent has written the interpretation.

For coordinate input, pass `--latitude` and `--longitude`; the time zone is detected locally. An optional IANA `--timezone` can override it, for example `Asia/Kolkata`. See [the skill instructions](transit-lab/SKILL.md) and [methodology notes](transit-lab/references/methodology.md).

For a Nominatim-compatible geocoder you operate or have permission to use, override the host with `--nominatim-domain` or `TRANSIT_LAB_NOMINATIM_DOMAIN`.

## Licensing note

Swiss Ephemeris is dual licensed under AGPL and a commercial/professional license. Review its current terms before distributing an application or providing a service based on its calculations. See [methodology notes](transit-lab/references/methodology.md).
