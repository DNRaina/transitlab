# Astro Sage

An installable agent skill for dual Jyotisha and Western natal chart readings. The skill combines a small Python chart calculator with source-aware interpretation instructions and an optional PDF export.

## Install

From the project root, install the skill folder directly with the Skills CLI:

```sh
npx skills add . --skill astro-sage
```

To distribute publicly, push this repository to GitHub and use:

```sh
npx skills add OWNER/REPOSITORY --skill astro-sage
```

The Skills CLI supports Codex, Claude Code, Antigravity and other agents; exact agent selection can be passed with `-a` if needed. Check `npx skills add --help` for current options.

## Calculate a chart

Requires Python 3.10+ and the dependencies in `astro-sage/requirements.txt`:

```sh
python -m pip install -r astro-sage/requirements.txt
python astro-sage/scripts/chart.py --datetime "1990-05-17T14:30:00+05:30" --latitude 19.076 --longitude 72.8777 --name "Example" --reading interpretation.md --pdf example-reading.pdf
```

The datetime must include an explicit UTC offset. Coordinates are decimal degrees, north/east positive. The script writes machine-readable chart JSON to stdout and can create a PDF containing chart data and, optionally, a written interpretation supplied as UTF-8 text/Markdown. It does not generate that interpretation.

## Important distribution note

Swiss Ephemeris is dual licensed under AGPL and a commercial/professional license. Review its current licensing requirements before distributing this package or offering a service based on its calculations. See `astro-sage/references/methodology.md`.
