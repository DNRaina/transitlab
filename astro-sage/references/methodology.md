# Calculation and tradition notes

## Default settings

- Ephemeris: Swiss Ephemeris via the `pyswisseph` Python binding. The script requests Swiss Ephemeris calculations and allows the binding's built-in fallback when files are unavailable; the result records returned flags so an agent can disclose the actual source.
- Jyotisha: Lahiri/Chitrapaksha sidereal zodiac; whole-sign houses based on sidereal ascendant; mean lunar node; D1 rāśi and D9 navāṃśa positions. Whole-sign houses and Lahiri are common modern defaults, not the only valid Jyotisha practice.
- Western: tropical zodiac; Placidus houses; major aspects among Sun through Pluto, with conservative configurable orb defaults in the script.
- Coordinates: decimal degrees, north/east positive. Birth datetime must include an explicit UTC offset. The script converts it to UTC before calculating.

## Interpretation boundaries

Do not present these modern defaults as a single timeless or universally agreed “Hindu astrology” system. Jyotisha is diverse across texts, periods, regions, and lineages. The chart engine does not calculate Vimshottari daśā, divisional charts beyond D9, special lagnas, upagrahas, or classical bala metrics. Never imply that it has.

Textual claims require checked references. Useful primary-text families to consult include Bṛhat Parāśara Horā Śāstra, Bṛhat Jātaka, Phaladīpikā, and Jaimini materials, but editions/translations and attributions vary. Cite a specific edition/translator and chapter/verse only after verifying it. Do not pass off a contemporary blog or a model-generated paraphrase as a shastra quotation.

## Licensing

Swiss Ephemeris is dual licensed under AGPL and a commercial/professional license. Anyone distributing an application that incorporates it or activating a public service must choose and comply with a license. Review the current Swiss Ephemeris license and the `pyswisseph` package terms before public distribution. This repository's skill instructions and Python wrapper do not grant a Swiss Ephemeris license.
