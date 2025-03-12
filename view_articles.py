import os
import http.server
import socketserver
import webbrowser
import argparse
from pathlib import Path

def start_server(directory, port=8000):
    """Start a simple HTTP server to view the HTML files."""
    # Change to the specified directory
    os.chdir(directory)
    
    # Create a simple HTTP server
    handler = http.server.SimpleHTTPRequestHandler
    
    # Allow the server to be reused
    socketserver.TCPServer.allow_reuse_address = True
    
    # Create the server
    with socketserver.TCPServer(("", port), handler) as httpd:
        print(f"Server started at http://localhost:{port}")
        print(f"Serving files from: {os.path.abspath(directory)}")
        print("Press Ctrl+C to stop the server")
        
        # Open the browser
        webbrowser.open(f"http://localhost:{port}")
        
        # Serve until interrupted
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")

def list_articles(directory):
    """List all HTML files in the directory."""
    html_files = sorted([f for f in os.listdir(directory) if f.endswith('.html')])
    
    if not html_files:
        print(f"No HTML files found in {directory}")
        return
    
    print(f"Found {len(html_files)} HTML files in {directory}:")
    for i, file in enumerate(html_files[:20], 1):
        print(f"{i}. {file}")
    
    if len(html_files) > 20:
        print(f"... and {len(html_files) - 20} more files")

def create_index_page(directory):
    """Create an index.html file with links to all articles."""
    html_files = sorted([f for f in os.listdir(directory) if f.endswith('.html')])
    
    if not html_files:
        print(f"No HTML files found in {directory}")
        return
    
    # Create the index.html file
    index_path = os.path.join(directory, "index.html")
    
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write("""<!DOCTYPE html>
<html>
<head>
    <title>Civilization 5 Wiki Articles</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            line-height: 1.6;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            color: #333;
        }
        h1 {
            color: #444;
            border-bottom: 1px solid #ddd;
            padding-bottom: 10px;
        }
        ul {
            list-style-type: none;
            padding: 0;
        }
        li {
            margin-bottom: 8px;
            padding: 8px;
            border-bottom: 1px solid #eee;
        }
        li:hover {
            background-color: #f9f9f9;
        }
        a {
            text-decoration: none;
            color: #0066cc;
        }
        a:hover {
            text-decoration: underline;
        }
        .search-container {
            margin: 20px 0;
        }
        #search {
            padding: 8px;
            width: 100%;
            font-size: 16px;
            border: 1px solid #ddd;
            border-radius: 4px;
        }
    </style>
</head>
<body>
    <h1>Civilization 5 Wiki Articles</h1>
    
    <div class="search-container">
        <input type="text" id="search" placeholder="Search articles..." onkeyup="filterArticles()">
    </div>
    
    <ul id="article-list">
""")
        
        # Add links to all HTML files
        for file in html_files:
            if file != "index.html":
                title = file.replace('.html', '').replace('_', ' ')
                f.write(f'        <li><a href="{file}">{title}</a></li>\n')
        
        f.write("""    </ul>

    <script>
        function filterArticles() {
            // Get the search term
            var input = document.getElementById('search');
            var filter = input.value.toUpperCase();
            
            // Get the list of articles
            var ul = document.getElementById('article-list');
            var li = ul.getElementsByTagName('li');
            
            // Loop through all list items, and hide those that don't match the search query
            for (var i = 0; i < li.length; i++) {
                var a = li[i].getElementsByTagName('a')[0];
                var txtValue = a.textContent || a.innerText;
                
                if (txtValue.toUpperCase().indexOf(filter) > -1) {
                    li[i].style.display = '';
                } else {
                    li[i].style.display = 'none';
                }
            }
        }
    </script>
</body>
</html>""")
    
    print(f"Created index.html with links to {len(html_files)} articles")
    return index_path

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="View minimal HTML files in a browser")
    parser.add_argument("--dir", default="./minimal_html", help="Directory containing the HTML files")
    parser.add_argument("--port", type=int, default=8000, help="Port to run the server on")
    parser.add_argument("--list", action="store_true", help="List available HTML files")
    
    args = parser.parse_args()
    
    # Check if the directory exists
    if not os.path.exists(args.dir):
        print(f"Directory {args.dir} does not exist")
        exit(1)
    
    # List articles if requested
    if args.list:
        list_articles(args.dir)
        exit(0)
    
    # Create an index.html file
    create_index_page(args.dir)
    
    # Start the server
    start_server(args.dir, args.port) 