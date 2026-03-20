"""
HomeschoolIQ — Web Scraper
File: scraper/scrape_sources.py
 
Reads active sources from scraper/sources.json, fetches each page,
extracts the visible text, and writes timestamped output to data/raw/.
A run manifest is written to data/logs/ on every run.
 
Usage:
    python scraper/scrape_sources.py
    — or —
    make scrape
"""