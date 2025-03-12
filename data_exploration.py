import os
import re
from bs4 import BeautifulSoup
import json
from pathlib import Path

# Directory containing the HTML files
DATA_DIR = "./data"
# Directory to save the extracted content
OUTPUT_DIR = "./extracted_content"

# Create output directory if it doesn't exist
os.makedirs(OUTPUT_DIR, exist_ok=True)

def extract_article_content(html_content):
    """
    Extract the main article content from the HTML.
    Returns a dictionary with title and content.
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Extract the title
    title_tag = soup.find('title')
    title = title_tag.text.split('|')[0].strip() if title_tag else "Unknown Title"
    
    # Find the main content div
    content_div = soup.find('div', class_='mw-parser-output')
    
    if not content_div:
        return {"title": title, "content": "No content found"}
    
    # Extract the article content
    # We'll focus on paragraphs, headings, and lists which contain the actual article text
    content_elements = []
    
    # Get all direct children of the content div
    for element in content_div.children:
        # Skip non-tag elements like NavigableString
        if not hasattr(element, 'name'):
            continue
            
        # Skip the infobox and navigation templates
        if element.name == 'aside' or element.name == 'table':
            continue
            
        # Check if element has class attribute before checking if 'infobox' is in it
        if hasattr(element, 'get') and element.get('class') and any('infobox' in cls for cls in element.get('class')):
            continue
            
        # Include paragraphs, headings, and lists
        if element.name in ['p', 'h1', 'h2', 'h3', 'h4', 'ul', 'ol', 'dl']:
            # Remove edit section links
            for edit_section in element.find_all(class_='mw-editsection'):
                edit_section.decompose()
                
            # Clean up the text by removing extra whitespace
            text = element.get_text().strip()
            if text:
                content_elements.append({
                    "type": element.name,
                    "text": text
                })
    
    return {
        "title": title,
        "content": content_elements
    }

def process_html_files():
    """Process all HTML files in the data directory."""
    # Get all HTML files
    html_files = [f for f in os.listdir(DATA_DIR) if f.endswith('.html')]
    
    print(f"Found {len(html_files)} HTML files to process")
    
    # Process each file
    for i, filename in enumerate(html_files):
        if i % 10 == 0:
            print(f"Processing file {i+1}/{len(html_files)}: {filename}")
            
        file_path = os.path.join(DATA_DIR, filename)
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
                
            # Extract the content
            article_data = extract_article_content(html_content)
            
            # Save the extracted content as JSON
            output_filename = os.path.splitext(filename)[0] + '.json'
            output_path = os.path.join(OUTPUT_DIR, output_filename)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(article_data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            print(f"Error processing {filename}: {e}")
    
    print(f"Processed {len(html_files)} files. Extracted content saved to {OUTPUT_DIR}")

def analyze_content_size():
    """Analyze the size of the extracted content vs. original HTML."""
    html_files = [f for f in os.listdir(DATA_DIR) if f.endswith('.html')]
    json_files = [f for f in os.listdir(OUTPUT_DIR) if f.endswith('.json')]
    
    if not json_files:
        print("No extracted content files found. Run process_html_files() first.")
        return
    
    total_html_size = 0
    total_json_size = 0
    
    for html_file in html_files:
        html_path = os.path.join(DATA_DIR, html_file)
        json_file = os.path.splitext(html_file)[0] + '.json'
        json_path = os.path.join(OUTPUT_DIR, json_file)
        
        if os.path.exists(json_path):
            html_size = os.path.getsize(html_path)
            json_size = os.path.getsize(json_path)
            
            total_html_size += html_size
            total_json_size += json_size
    
    if total_html_size > 0:
        reduction_percentage = ((total_html_size - total_json_size) / total_html_size) * 100
        print(f"Original HTML total size: {total_html_size / 1024:.2f} KB")
        print(f"Extracted content total size: {total_json_size / 1024:.2f} KB")
        print(f"Size reduction: {reduction_percentage:.2f}%")

def sample_extracted_content(num_samples=3):
    """Display samples of the extracted content."""
    json_files = [f for f in os.listdir(OUTPUT_DIR) if f.endswith('.json')]
    
    if not json_files:
        print("No extracted content files found. Run process_html_files() first.")
        return
    
    # Take a few samples
    samples = json_files[:num_samples]
    
    for sample in samples:
        json_path = os.path.join(OUTPUT_DIR, sample)
        
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"\n--- Sample: {sample} ---")
        print(f"Title: {data['title']}")
        print("Content preview:")
        
        # Print first few content elements
        for i, element in enumerate(data['content'][:5]):
            if isinstance(element, dict):
                print(f"  {element['type']}: {element['text'][:100]}...")
            else:
                print(f"  {element}")
            
        print(f"  ... ({len(data['content'])} elements total)")

def create_minimal_html_version():
    """Create minimal HTML versions of the extracted content."""
    minimal_html_dir = "./minimal_html"
    os.makedirs(minimal_html_dir, exist_ok=True)
    
    json_files = [f for f in os.listdir(OUTPUT_DIR) if f.endswith('.json')]
    
    if not json_files:
        print("No extracted content files found. Run process_html_files() first.")
        return
    
    for json_file in json_files:
        json_path = os.path.join(OUTPUT_DIR, json_file)
        
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Create a minimal HTML version with basic styling
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>{data['title']}</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            color: #333;
        }}
        h1, h2, h3, h4 {{
            color: #444;
        }}
        h1 {{
            border-bottom: 1px solid #ddd;
            padding-bottom: 10px;
        }}
        p {{
            margin-bottom: 16px;
        }}
        .quote {{
            font-style: italic;
            margin: 20px 0;
            padding-left: 20px;
            border-left: 4px solid #ddd;
        }}
        .footer {{
            margin-top: 30px;
            padding-top: 10px;
            border-top: 1px solid #ddd;
            font-size: 0.9em;
            color: #666;
        }}
    </style>
</head>
<body>
    <h1>{data['title']}</h1>
"""
        
        # Skip the first paragraph if it contains infobox content
        # (usually very long with lots of newlines and technical details)
        content_elements = data['content']
        skip_first = False
        
        if isinstance(content_elements, list) and len(content_elements) > 0:
            if content_elements[0]['type'] == 'p' and len(content_elements[0]['text']) > 500 and content_elements[0]['text'].count('\n') > 10:
                skip_first = True
        
        # Process each content element
        for i, element in enumerate(content_elements):
            if not isinstance(element, dict):
                continue
                
            # Skip the first element if it's the infobox content
            if i == 0 and skip_first:
                continue
                
            element_type = element['type']
            text = element['text']
            
            # Handle different element types
            if element_type in ['h1', 'h2', 'h3', 'h4']:
                html_content += f"    <{element_type}>{text}</{element_type}>\n"
            
            elif element_type == 'p':
                html_content += f"    <p>{text}</p>\n"
            
            elif element_type == 'dl':
                # Format as a quote
                html_content += f'    <div class="quote">{text}</div>\n'
            
            elif element_type == 'ul':
                # Process list items
                items = text.split('\n')
                html_content += "    <ul>\n"
                for item in items:
                    if item.strip():
                        html_content += f"        <li>{item.strip()}</li>\n"
                html_content += "    </ul>\n"
            
            elif element_type == 'ol':
                # Process ordered list items
                items = text.split('\n')
                html_content += "    <ol>\n"
                for item in items:
                    if item.strip():
                        html_content += f"        <li>{item.strip()}</li>\n"
                html_content += "    </ol>\n"
        
        # Add footer with link to original
        original_filename = os.path.splitext(json_file)[0] + '.html'
        html_content += f"""
    <div class="footer">
        <p>This is a minimal version of the article content extracted from the Civilization 5 Wiki.</p>
        <p>Original article: <a href="https://civilization.fandom.com/wiki/{original_filename.replace('.html', '')}">{data['title']}</a></p>
    </div>
</body>
</html>"""
        
        # Save the minimal HTML
        html_filename = os.path.splitext(json_file)[0] + '.html'
        html_path = os.path.join(minimal_html_dir, html_filename)
        
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
    
    print(f"Created improved minimal HTML versions in {minimal_html_dir}")

if __name__ == "__main__":
    print("Starting data exploration...")
    
    # Process the HTML files
    process_html_files()
    
    # Analyze the content size
    analyze_content_size()
    
    # Show some samples
    sample_extracted_content()
    
    # Create minimal HTML versions
    create_minimal_html_version()
    
    print("Data exploration complete!")
