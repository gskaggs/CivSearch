# Civilization V Wiki Crawler

A web crawler designed to scrape Civilization V wiki articles from the Civilization Fandom wiki.

## Features

- Crawls the Civilization V wiki starting from the main page
- Saves only valid Civilization V articles (URLs ending with "(Civ5)")
- Excludes Civilopedia pages (URLs ending with "/Civilopedia")
- Respects the server by adding delays between requests
- Logs crawling progress and errors
- Limits the number of articles saved to prevent excessive downloads

## Requirements

- Python 3.6+
- Required packages: requests, beautifulsoup4

## Installation

1. Clone this repository
2. Install the required packages:

```bash
pip install -r requirements.txt
```

## Usage

Run the crawler with:

```bash
python scrape.py
```

The crawler will:
1. Start at the Civilization V main page
2. Follow links to find Civilization V articles
3. Save HTML content to the `./data` directory
4. Create a mapping file (`url_mapping.txt`) to track which files correspond to which URLs
5. Create a log file (`crawl_log.txt`) with details about the crawling process

## Configuration

You can modify the following variables in `scrape.py` to customize the crawler:

- `START_URL`: The starting URL for the crawler
- `OUTPUT_DIR`: The directory where HTML files will be saved
- `MAX_ARTICLES`: The maximum number of articles to save
- `DELAY`: The delay between requests in seconds

## Notes

- The crawler uses a breadth-first search approach to find articles
- It avoids visiting the same URL twice
- It handles errors gracefully and logs them
- You can interrupt the crawler at any time with Ctrl+C 