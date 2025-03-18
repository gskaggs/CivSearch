import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import time
from collections import deque
import datetime
import pickle

# Configuration
START_URL = "https://civilization.fandom.com/wiki/Civilization_V"
OUTPUT_DIR = "./data"
MAX_ARTICLES = 10000
DELAY = 1  # Delay between requests in seconds to be respectful
USER_AGENT = "CivVWikiCrawler/1.0 (Educational Project)"
# How often to save state (in seconds)
SAVE_STATE_INTERVAL = 60
# State file path
STATE_FILE = os.path.join(OUTPUT_DIR, "crawler_state.pkl")

# Create output directory if it doesn't exist
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Track visited URLs to avoid duplicates
visited_urls = set()
# Track saved articles count
saved_count = 0
# Track total URLs processed
processed_count = 0
# Queue for URLs to process
queue = deque()

def is_valid_civ5_article(url):
    """Check if the URL is a valid Civilization V article."""
    if url == START_URL:
        return True
    
    # Must be from the same domain
    if "civilization.fandom.com" not in url:
        if kasbah_url in url:
            print("  - FAILED: Not from civilization.fandom.com domain")
        return False
    
    # Parse the URL to get the path
    parsed_url = urlparse(url)
    path = parsed_url.path

    if "/fi/" in path or "/de/" in path or "/fr/" in path or "/es/" in path or "/it/" in path or "/ja/" in path or "/ko/" in path or "/pl/" in path or "/pt/" in path or "/ru/" in path or "/zh/" in path:
        if kasbah_url in url:
            print("  - FAILED: Contains language prefix")
        return False
    
    # Skip category, talk and category talk pages
    if any(x in path for x in ["Category:", "Talk:", "Category_talk:"]):
        if kasbah_url in url:
            print("  - FAILED: Is a category, talk, or category talk page")
        return False
    
    # Must end with (Civ5)
    if not path.endswith("(Civ5)"):
        if kasbah_url in url:
            print(f"  - FAILED: Path does not end with (Civ5). Path: {path}")
        return False
    
    # Must not be a Civilopedia page
    if "/Civilopedia" in path or path.endswith("(Civ5)/Civilopedia"):
        if kasbah_url in url:
            print("  - FAILED: Is a Civilopedia page")
        return False
    
    if kasbah_url in url:
        print("  + PASSED ALL CHECKS: This URL is valid!")
    
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

def save_state():
    """Save the current state of the crawler to a file."""
    global visited_urls, saved_count, processed_count, queue
    
    state = {
        'visited_urls': list(visited_urls),
        'saved_count': saved_count,
        'processed_count': processed_count,
        'queue': list(queue)
    }
    
    # Use a temporary file to avoid corruption if the process is killed during saving
    temp_file = STATE_FILE + '.tmp'
    
    try:
        with open(temp_file, 'wb') as f:
            pickle.dump(state, f)
        
        # Rename the temporary file to the actual state file
        if os.path.exists(STATE_FILE):
            os.remove(STATE_FILE)
        os.rename(temp_file, STATE_FILE)
        
        print(f"State saved: {processed_count} URLs processed, {saved_count} articles saved, {len(queue)} URLs in queue")
    except Exception as e:
        print(f"Error saving state: {e}")

def load_state():
    """Load the crawler state from a file if it exists."""
    global visited_urls, saved_count, processed_count, queue
    
    if not os.path.exists(STATE_FILE):
        print("No previous state found. Starting fresh crawl.")
        return False
    
    try:
        with open(STATE_FILE, 'rb') as f:
            state = pickle.load(f)
        
        visited_urls = set(state['visited_urls'])
        saved_count = state['saved_count']
        processed_count = state['processed_count']
        queue = deque(state['queue'])
        
        print(f"Loaded previous state: {processed_count} URLs processed, {saved_count} articles saved, {len(queue)} URLs in queue")
        return True
    except Exception as e:
        print(f"Error loading state: {e}")
        print("Starting fresh crawl.")
        return False

def crawl():
    """Crawl the website starting from the START_URL using a queue-based approach."""
    global saved_count, processed_count, queue, visited_urls
    
    # Kasbah URL for debugging
    kasbah_url = "https://civilization.fandom.com/wiki/Kasbah_(Civ5)"
    
    # Check if we have a saved state to resume from
    state_loaded = load_state()
    
    # If no state was loaded, initialize the queue with the starting URL
    if not state_loaded:
        queue = deque([START_URL])
        # Add Kasbah URL directly to the queue for testing
        if kasbah_url not in queue:
            queue.append(kasbah_url)
            print(f"\n!!! MANUALLY ADDED KASBAH URL TO QUEUE !!!")
    
    # Set up headers for requests
    headers = {
        "User-Agent": USER_AGENT
    }
    
    # Record start time
    start_time = time.time()
    last_progress_time = start_time
    last_save_time = start_time
    
    # Create or append to log file
    log_file = os.path.join(OUTPUT_DIR, "crawl_log.txt")
    log_mode = "a" if state_loaded else "w"
    
    with open(log_file, log_mode, encoding="utf-8") as f:
        f.write(f"\nCrawl {'resumed' if state_loaded else 'started'} at: {datetime.datetime.now()}\n")
        if not state_loaded:
            f.write(f"Starting URL: {START_URL}\n")
        f.write(f"Max articles: {MAX_ARTICLES}\n")
        f.write(f"Current progress: {saved_count}/{MAX_ARTICLES} articles saved\n\n")
    
    # Check if Kasbah URL is in visited_urls
    if kasbah_url in visited_urls:
        print(f"\n!!! KASBAH URL ALREADY VISITED: {kasbah_url} !!!")
    
    # Check if Kasbah URL is in queue
    if any(kasbah_url in url for url in queue):
        print(f"\n!!! KASBAH URL ALREADY IN QUEUE !!!")
    
    while queue and saved_count < MAX_ARTICLES:
        # Get the next URL from the queue
        url = queue.popleft()

        # Remove any URL fragments (#) and query parameters (?)
        url = url.split('#')[0]  # Remove fragment
        url = url.split('?')[0]  # Remove query parameters
        
        # Skip if we've already visited this URL
        if url in visited_urls:
            if kasbah_url in url:
                print(f"\n!!! SKIPPING KASBAH URL (ALREADY VISITED): {url} !!!")
            continue
        
        # Mark as visited
        visited_urls.add(url)
        processed_count += 1
        
        # Print progress every 10 seconds
        current_time = time.time()
        if current_time - last_progress_time > 10:
            print_progress()
            last_progress_time = current_time
        
        # Save state periodically
        if current_time - last_save_time > SAVE_STATE_INTERVAL:
            save_state()
            last_save_time = current_time

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
                
                # Check for Kasbah URL
                if kasbah_url in absolute_url:
                    print(f"\n!!! FOUND KASBAH LINK: {absolute_url} !!!")
                    print(f"!!! ORIGINAL HREF: {href} !!!")
                    print(f"!!! FOUND ON PAGE: {url} !!!")
                    print(f"!!! IS IN VISITED_URLS: {absolute_url in visited_urls} !!!")
                
                # Only follow links to the same domain
                if "civilization.fandom.com" in absolute_url and absolute_url not in visited_urls:
                    # Add to the queue
                    queue.append(absolute_url)
                    if kasbah_url in absolute_url:
                        print(f"\n!!! ADDED KASBAH URL TO QUEUE: {absolute_url} !!!")
            
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
    
    # Save final state
    save_state()
    
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
    
    # Test Kasbah URL validation
    kasbah_url = "https://civilization.fandom.com/wiki/Kasbah_(Civ5)"
    print("\n=== TESTING KASBAH URL VALIDATION ===")
    print(f"URL: {kasbah_url}")
    parsed_url = urlparse(kasbah_url)
    print(f"Parsed URL: {parsed_url}")
    print(f"Path: {parsed_url.path}")
    print(f"Path ends with (Civ5): {parsed_url.path.endswith('(Civ5)')}")
    print(f"Is valid: {is_valid_civ5_article(kasbah_url)}")
    print("=====================================\n")
    
    try:
        # Start the crawl
        crawl()
    except KeyboardInterrupt:
        print("\nCrawling interrupted by user.")
        # Save state on keyboard interrupt
        save_state()
    except Exception as e:
        print(f"Unexpected error: {e}")
        # Save state on unexpected error
        save_state()
    
    print(f"Crawling complete. Saved {saved_count} articles.")
    print(f"Processed {processed_count} URLs in total.")
