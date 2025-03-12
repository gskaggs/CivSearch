import os
import re
import glob
import json
import time
import dotenv
import openai
from bs4 import BeautifulSoup
from pathlib import Path
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Load environment variables
dotenv.load_dotenv()

# Set up OpenAI API
openai.api_key = os.getenv("OPEN_AI_API_KEY")
if not openai.api_key:
    raise ValueError("OpenAI API key not found. Please set the OPEN_AI_API_KEY environment variable.")

# Directory containing the HTML files
HTML_DIR = "./minimal_html"

class CivSearchRAG:
    def __init__(self):
        self.articles = []
        self.vectorizer = TfidfVectorizer(stop_words='english')
        self.tfidf_matrix = None
        
    def load_articles(self):
        """Load all HTML articles from the minimal_html directory."""
        print("Loading articles...")
        html_files = glob.glob(os.path.join(HTML_DIR, "*.html"))
        
        for file_path in html_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                
                # Parse HTML
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # Extract title and content
                title = soup.title.text if soup.title else Path(file_path).stem.replace('_', ' ')
                
                # Clean up the title (remove "Civ5" and other formatting)
                title = title.replace(" (Civ5)", "").replace("_", " ")
                
                # Extract text content from paragraphs, headings, and lists
                content = ""
                for element in soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'li']):
                    content += element.get_text() + " "
                
                # Store article data
                self.articles.append({
                    'title': title,
                    'content': content,
                    'file_path': file_path
                })
                
            except Exception as e:
                print(f"Error loading {file_path}: {e}")
        
        print(f"Loaded {len(self.articles)} articles.")
        
        # Create TF-IDF matrix
        if self.articles:
            documents = [f"{article['title']} {article['content']}" for article in self.articles]
            self.tfidf_matrix = self.vectorizer.fit_transform(documents)
    
    def search(self, query, top_k=3):
        """Search for articles relevant to the query."""
        if not self.articles or self.tfidf_matrix is None:
            print("No articles loaded. Please load articles first.")
            return []
        
        # Transform query to TF-IDF vector
        query_vector = self.vectorizer.transform([query])
        
        # Calculate cosine similarity
        similarities = cosine_similarity(query_vector, self.tfidf_matrix).flatten()
        
        # Get top-k indices
        top_indices = similarities.argsort()[-top_k:][::-1]
        
        # Return top-k articles with similarity scores
        results = []
        for idx in top_indices:
            article = self.articles[idx]
            # Only include articles with a minimum similarity score
            if similarities[idx] > 0.001:  # Adjust threshold as needed
                results.append({
                    'title': article['title'],
                    'similarity': similarities[idx],
                    'content': article['content'],
                    'file_path': article['file_path']
                })
        
        return results
    
    def get_article_content(self, file_path):
        """Get the full content of an article."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # Parse HTML
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Extract text content
            content = ""
            for element in soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'li']):
                content += element.get_text() + "\n"
            
            return content
        
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            return ""
    
    def generate_response(self, query, search_results):
        """Generate a response using OpenAI API based on search results."""
        if not search_results:
            return "I couldn't find any relevant information about that topic in the Civilization V wiki.", []
        
        # Prepare context from search results
        context = ""
        for i, result in enumerate(search_results):
            context += f"\n--- Article {i}: {result['title']} ---\n"
            # Get a more substantial chunk of content, but still limit it
            content_chunk = result['content'][:2000]  
            context += content_chunk
            context += "\n"
        
        # Prepare prompt for OpenAI
        prompt = f"""You are an assistant that helps answer questions about the Civilization V video game.
Use the following articles from the Civilization V wiki to answer the user's question.
If you don't know the answer based on these articles, say so.

{context}

When you use information from an article, cite it using square brackets with the article number, like [0], [1], etc.
The article numbers correspond to the article headings above.

User question: {query}

Answer:"""
        
        try:
            # Call OpenAI API
            response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that answers questions about Civilization V based on wiki articles. Always cite your sources using [0], [1], etc. when you use information from the provided articles."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.7
            )
            
            answer = response.choices[0].message.content
            
            # Determine which articles were actually cited in the response
            cited_articles = []
            for i, result in enumerate(search_results):
                citation_marker = f"[{i}]"
                if citation_marker in answer:
                    # Get the filename from the path
                    filename = os.path.basename(result['file_path'])
                    cited_articles.append({
                        'index': i,
                        'title': result['title'],
                        'filename': filename
                    })
            
            return answer, cited_articles
        
        except Exception as e:
            print(f"Error calling OpenAI API: {e}")
            return "Sorry, I encountered an error while generating a response.", []

def display_welcome():
    """Display a welcome message."""
    print("\n" + "=" * 50)
    print("  CIVILIZATION V WIKI SEARCH - RAG SYSTEM")
    print("=" * 50)
    print("Ask questions about Civilization V and get answers based on wiki content.")
    print("Examples:")
    print("  - What are the Shoshone Pathfinders?")
    print("  - Tell me about the Russian unique ability")
    print("  - How does tourism work in Civ 5?")
    print("\nType 'quit' to exit.")
    print("=" * 50)

def format_citations(cited_articles):
    """Format the citations for display."""
    if not cited_articles:
        return "No sources cited."
    
    citations = "\nSources:\n"
    for article in cited_articles:
        citations += f"[{article['index']}] {article['title']} - {article['filename']}\n"
    
    return citations

def main():
    # Initialize the RAG system
    rag = CivSearchRAG()
    
    try:
        # Load articles
        rag.load_articles()
        
        # Display welcome message
        display_welcome()
        
        while True:
            # Get user query
            query = input("\nYour question: ")
            
            if not query.strip():
                continue
                
            if query.lower() in ['quit', 'exit', 'q']:
                print("\nThank you for using the Civilization V Wiki Search. Goodbye!")
                break
            
            # Search for relevant articles
            print("Searching for relevant information...")
            start_time = time.time()
            results = rag.search(query)
            search_time = time.time() - start_time
            
            if not results:
                print("No relevant articles found. Please try a different question.")
                continue
            
            # Print search results
            print(f"\nFound {len(results)} relevant articles in {search_time:.2f} seconds:")
            for i, result in enumerate(results):
                print(f"{i}. {result['title']} (Relevance: {result['similarity']:.4f})")
            
            # Generate response
            print("\nGenerating answer...")
            start_time = time.time()
            response, cited_articles = rag.generate_response(query, results)
            generation_time = time.time() - start_time
            
            # Print response
            print("\n" + "-" * 50)
            print(response)
            
            # Print citations
            if cited_articles:
                print("\n" + "-" * 50)
                print(format_citations(cited_articles))
            
            print("-" * 50)
            print(f"Response generated in {generation_time:.2f} seconds")
            
    except KeyboardInterrupt:
        print("\n\nSearch interrupted. Goodbye!")
    except Exception as e:
        print(f"\nAn error occurred: {e}")

if __name__ == "__main__":
    main()
