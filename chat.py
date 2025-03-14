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
        self.conversation_history = []
        
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
        
        # Use conversation history and LLM to create an improved query
        improved_query = self._generate_improved_query(query)
        print(f"Improved query: '{improved_query}'")
        
        # Transform query to TF-IDF vector
        query_vector = self.vectorizer.transform([improved_query])
        
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
    
    def _generate_improved_query(self, current_query):
        """Generate an improved search query using conversation history and LLM."""
        # If there's no conversation history, return the original query
        if len(self.conversation_history) < 2:  # Need at least one previous exchange
            return current_query
        
        try:
            # Prepare conversation history for context
            history_context = ""
            # Get the last few exchanges (up to 5 for reasonable context)
            recent_history = self.conversation_history[-10:-1]  # Exclude the current query which is the last one
            
            # If there's no previous history after excluding current query, return original
            if not recent_history:
                return current_query
                
            for message in recent_history:
                role = message["role"]
                content = message["content"]
                history_context += f"{role.capitalize()}: {content}\n"
            
            # Get the current query (which should be the last item in conversation_history)
            current_query_from_history = self.conversation_history[-1]["content"]
            
            # Prepare system message
            system_message = """You are a query improvement system for a Civilization V wiki search engine.
Your task is to create an improved search query based on the conversation history and the current query.
If the current query refers to previous context or uses pronouns, make it more specific and self-contained.
Focus on extracting key Civilization V terms and concepts that would make a good search query.
Return ONLY the improved query text without any explanation or additional text."""
            
            # Call OpenAI API
            response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": f"Conversation history:\n{history_context}\n\nCurrent query: {current_query_from_history}\n\nImproved query:"}
                ],
                max_tokens=100,
                temperature=0.3
            )
            
            improved_query = response.choices[0].message.content.strip()
            
            # If the improved query is empty or the API call failed somehow, fall back to the original
            if not improved_query:
                return current_query
                
            return improved_query
            
        except Exception as e:
            print(f"Error generating improved query: {e}")
            # Fall back to the original query if there's an error
            return current_query
    
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
            response = "I couldn't find any relevant information about that topic in the Civilization V wiki."
            # No need to add user query to history as it's already added before search
            self.conversation_history.append({"role": "assistant", "content": response})
            return response, []
        
        # Prepare context from search results
        context = ""
        for i, result in enumerate(search_results):
            context += f"\n--- Article {i}: {result['title']} ---\n"
            # Get a more substantial chunk of content, but still limit it
            content_chunk = result['content'][:2000]  
            context += content_chunk
            context += "\n"
        
        # Prepare system message with context
        system_message = f"""You are a helpful assistant that answers questions about Civilization V based on wiki articles. 
Always cite your sources using [0], [1], etc. when you use information from the provided articles.

Here are the relevant articles for the current question:
{context}"""
        
        # The current query is already added to conversation history before search
        # So we don't need to add it again here
        
        try:
            # Prepare messages for OpenAI API
            messages = [{"role": "system", "content": system_message}]
            
            # Add conversation history (limited to last 10 exchanges to manage token usage)
            history_to_include = self.conversation_history[-10:] if len(self.conversation_history) > 10 else self.conversation_history
            messages.extend(history_to_include)  # Include all history since we no longer add the query twice
            
            # Call OpenAI API
            response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                max_tokens=500,
                temperature=0.7
            )
            
            answer = response.choices[0].message.content
            
            # Add the response to conversation history
            self.conversation_history.append({"role": "assistant", "content": answer})
            
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
            error_message = "Sorry, I encountered an error while generating a response."
            self.conversation_history.append({"role": "assistant", "content": error_message})
            return error_message, []

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
            
            # Add the current query to conversation history before searching
            # This ensures the query improvement has access to the current query in history
            rag.conversation_history.append({"role": "user", "content": query})
            
            # Search for relevant articles
            print("Searching for relevant information...")
            start_time = time.time()
            results = rag.search(query)
            search_time = time.time() - start_time
            
            if not results:
                print("No relevant articles found. Please try a different question.")
                # Add assistant response to conversation history
                rag.conversation_history.append({"role": "assistant", "content": "I couldn't find any relevant information about that topic in the Civilization V wiki."})
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
