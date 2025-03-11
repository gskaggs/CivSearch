import os
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import time
import hashlib
from collections import deque
import sys
import datetime

# Configuration
START_URL = "https://civilization.fandom.com/wiki/Civilization_V"
OUTPUT_DIR = "./data"
MAX_ARTICLES = 5000
DELAY = 1  # Delay between requests in seconds to be respectful
USER_AGENT = "CivVWikiCrawler/1.0 (Educational Project)"

# Create output directory if it doesn't exist
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Track visited URLs to avoid duplicates
visited_urls = set()
# Track saved articles count
saved_count = 0
# Track total URLs processed
processed_count = 0

def is_valid_civ5_article(url):
    """Check if the URL is a valid Civilization V article."""
    if url == START_URL:
        return True
    
    # Must be from the same domain
    if "civilization.fandom.com" not in url:
        return False
    
    # Parse the URL to get the path
    parsed_url = urlparse(url)
    path = parsed_url.path
    
    # Must end with (Civ5)
    if not path.endswith("(Civ5)"):
        return False
    
    # Must not be a Civilopedia page
    if "/Civilopedia" in path or path.endswith("(Civ5)/Civilopedia"):
        return False
    
    return True

def save_article(url, html_content):
    """Save the HTML content to a file."""
    global saved_count
    
    # Create a filename from the URL
    parsed_url = urlparse(url)
    path = parsed_url.path
    
    # Use a hash of the URL as the filename to avoid any issues with special characters
    # Extract the article name from the URL and clean it up
    article_name = url.split('/')[-1]  # Get text after last '/'
    article_name = article_name.replace('_(Civ5)', '')  # Remove the Civ5 suffix
    filename = article_name + '.html'
    filepath = os.path.join(OUTPUT_DIR, filename)
    
    # Save the HTML content
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    # Create a mapping file to keep track of which hash corresponds to which URL
    with open(os.path.join(OUTPUT_DIR, "url_mapping.txt"), "a", encoding="utf-8") as f:
        f.write(f"{filename}\t{url}\n")
    
    saved_count += 1
    print(f"Saved article {saved_count}/{MAX_ARTICLES}: {url}")

def print_progress():
    """Print progress information."""
    global processed_count, saved_count
    print(f"Processed: {processed_count} URLs | Saved: {saved_count}/{MAX_ARTICLES} articles | Queue: {len(queue)} URLs")

def crawl():
    """Crawl the website starting from the START_URL using a queue-based approach."""
    global saved_count, processed_count, queue
    
    # Initialize the queue with the starting URL
    queue = deque([START_URL])
    
    # Set up headers for requests
    headers = {
        "User-Agent": USER_AGENT
    }
    
    # Record start time
    start_time = time.time()
    last_progress_time = start_time
    
    # Create a log file
    log_file = os.path.join(OUTPUT_DIR, "crawl_log.txt")
    with open(log_file, "w", encoding="utf-8") as f:
        f.write(f"Crawl started at: {datetime.datetime.now()}\n")
        f.write(f"Starting URL: {START_URL}\n")
        f.write(f"Max articles: {MAX_ARTICLES}\n\n")
    
    while queue and saved_count < MAX_ARTICLES:
        # Get the next URL from the queue
        url = queue.popleft()
        
        # Skip if we've already visited this URL
        if url in visited_urls:
            continue
        
        # Mark as visited
        visited_urls.add(url)
        processed_count += 1
        
        # Print progress every 10 seconds
        current_time = time.time()
        if current_time - last_progress_time > 10:
            print_progress()
            last_progress_time = current_time
        
        try:
            # Make the request
            print(f"Crawling: {url}")
            
            # Save the article if it's a valid Civ5 article
            if not is_valid_civ5_article(url):
                continue

            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            # Parse the HTML
            soup = BeautifulSoup(response.text, "html.parser")

            save_article(url, response.text)
            
            # Log the saved article
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(f"Saved: {url}\n")
            
            if saved_count >= MAX_ARTICLES:
                print(f"Reached maximum number of articles ({MAX_ARTICLES})")
                break
            
            # Find all links on the page
            links = soup.find_all("a", href=True)
            
            # Process each link
            for link in links:
                href = link["href"]
                
                # Skip empty links, anchors, and non-HTTP links
                if not href or href.startswith("#") or href.startswith("javascript:"):
                    continue
                
                # Convert relative URLs to absolute URLs
                absolute_url = urljoin(url, href)
                
                # Only follow links to the same domain
                if "civilization.fandom.com" in absolute_url and absolute_url not in visited_urls:
                    # Add to the queue
                    queue.append(absolute_url)
            
            # Be respectful and don't hammer the server
            time.sleep(DELAY)
        
        except requests.exceptions.RequestException as e:
            print(f"Request error crawling {url}: {e}")
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(f"Error: {url} - {str(e)}\n")
        except Exception as e:
            print(f"Error crawling {url}: {e}")
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(f"Error: {url} - {str(e)}\n")
    
    # Record end time and calculate duration
    end_time = time.time()
    duration = end_time - start_time
    
    # Log completion
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"\nCrawl completed at: {datetime.datetime.now()}\n")
        f.write(f"Duration: {duration:.2f} seconds\n")
        f.write(f"Processed URLs: {processed_count}\n")
        f.write(f"Saved articles: {saved_count}\n")

if __name__ == "__main__":
    print(f"Starting crawler at {START_URL}")
    print(f"Saving articles to {OUTPUT_DIR}")
    print(f"Maximum articles: {MAX_ARTICLES}")
    
    try:
        # Start the crawl
        crawl()
    except KeyboardInterrupt:
        print("\nCrawling interrupted by user.")
    except Exception as e:
        print(f"Unexpected error: {e}")
    
    print(f"Crawling complete. Saved {saved_count} articles.")
    print(f"Processed {processed_count} URLs in total.")
