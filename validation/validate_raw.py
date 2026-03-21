"""
HomeschoolIQ — Raw Data Validator
File: validation/validate_raw.py
 
Reads the most recent scrape output from data/raw/, validates every
record against quality rules, and writes:
  - data/logs/<timestamp>_validation.json  — full validation report
  - data/quarantine/<timestamp>_<id>.json  — one file per failed record
 
Only records that pass all checks proceed to the cleaning pipeline.
 
Usage:
    python validation/validate_raw.py
    — or —
    make validate
"""