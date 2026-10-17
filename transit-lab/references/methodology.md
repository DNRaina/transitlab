# Calculation, source, and data notes

## Jyotisha defaults

- Ephemeris: Swiss Ephemeris through `pyswisseph`; returned flags are recorded in the JSON so the agent can disclose which ephemeris was used.
- Zodiac: sidereal Lahiri/Chitrapaksha; whole-sign houses from the sidereal ascendant; mean Rahu and Ketu derived exactly opposite Rahu.
- Included calculations: D1 rāśi, D9 navāṃśa, Moon's nakshatra and pada, retrograde status, and Vimshottari mahadasha sequence with the birth-period balance.
- Vimshottari period boundaries use a 365.2425-day year. This is an implementation convention for converting dasha years to calendar dates; interpret timing with care and do not present it as certainty.
- Time conversion uses the IANA time-zone database. Ambiguous or nonexistent local times at daylight-saving transitions are returned as a clarification request rather than guessed.

These settings are not the only valid Jyotisha conventions. Traditions differ in ayanamsha, node, house, dasha-year, and interpretive rules. Disclose the selected settings in every substantial reading.

## Birthplace resolution and privacy

When given a place name, the script uses GeoPy with a Nominatim-compatible geocoder for a one-time lookup, then uses `timezonefinder` locally to identify an IANA time zone. Only the city/town query is sent to the geocoder; date and time remain local. The default endpoint is OpenStreetMap's public Nominatim service. It uses a specific User-Agent, limits results to five, rate-limits requests, and can be redirected with `--nominatim-domain` or `TRANSIT_LAB_NOMINATIM_DOMAIN`. Attribute results from OSM to OpenStreetMap contributors. The public endpoint is intended for light, user-triggered use, not autocomplete, bulk, or commercial traffic; switch to a suitable provider for higher-volume or commercial use.

Place names can be ambiguous, coordinates can fall near time-zone borders, and historical local-time records can be uncertain. The LLM must surface multiple matches and ask the user to choose. Never silently use the machine's current time zone or today's UTC offset for a historical birth.

## Interpreting shastra

Useful primary-text families include Bṛhat Parāśara Horā Śāstra, Bṛhat Jātaka, Phaladīpikā, and Jaimini materials, but editions, translations, attributions, and rules vary. Do not claim that a specific interpretive rule comes from a text unless the exact passage has been checked in a named edition or reliable translation. Do not invent chapter/verse numbers or quotations. If no verifiable textual support is available, call the reading a contemporary interpretive convention.

The calculator supplies placements and timing boundaries; it does not validate yoga rules or determine strength. For every interpretive claim, explain the relevant lordship, house, sign, dignity, aspects, conjunctions, and modifiers only when those facts are actually calculated or reliably derived.

## Swiss Ephemeris licensing

Swiss Ephemeris is dual licensed under AGPL and a commercial/professional license. Review the current license and `pyswisseph` package terms before redistributing this package or offering a service. This skill and its wrapper do not grant an ephemeris license.
