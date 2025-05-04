import os
import json
import chromadb
from chromadb.utils import embedding_functions
from google import genai
import re
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Body, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Dict, Any, Union
import uuid
import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Load environment variables (for API keys)
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="PDF Chatbot API",
    description="API for chatting with PDF documents using Gemini and ChromaDB",
    version="1.0.0"
)

# Add CORS middleware to allow cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this in production to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define request/response models for API endpoints
class ChatRequest(BaseModel):
    query: str
    session_id: Optional[str] = None
    top_k: Optional[int] = 3

    model_config = ConfigDict(protected_namespaces=())  # Fix the Pydantic warning

class NewSessionRequest(BaseModel):
    content_dir: Optional[str] = None
    model_name: Optional[str] = "gemini-2.0-flash"

    model_config = ConfigDict(protected_namespaces=())  # Fix the Pydantic warning

class ConfigUpdateRequest(BaseModel):
    query_expansion: Optional[bool] = None
    model_name: Optional[str] = None
    top_k: Optional[int] = None

    model_config = ConfigDict(protected_namespaces=())  # Fix the Pydantic warning


    def __init__(self, content_dir=None, model_name="gemini-1.5-flash", use_chroma=True):
        """
        Initialize the chatbot with a given content directory
        
        Args:
            content_dir: Directory containing extracted PDF content
            model_name: Name of the Gemini model to use
            use_chroma: Whether to use ChromaDB for vector storage
        """
        try:
            self.content_dir = self._find_content_dir(content_dir)
            logger.info(f"Using content directory: {self.content_dir}")

            self.chunks = []
            self.use_chroma = use_chroma
            self.chat_history = []
            self.model_name = model_name
            self.use_query_expansion = True  # Control whether to use query expansion

            # Setup Gemini API
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("GEMINI_API_KEY not found in environment variables. "
                                "Please add it to a .env file or set it in your environment.")

            # Initialize Gemini client
            self.client = genai.Client(api_key=api_key)
            logger.info(f"Initialized Gemini client for model: {model_name}")

            # Initialize chat session
            self.current_context = None
            self.chat_session = None
            self.initialize_chat_session()

            # Setup ChromaDB
            self._setup_chromadb()

            # Load chunks
            self.load_chunks()

            logger.info(f"PdfChatbot initialized with {len(self.chunks)} chunks ready for context")
        except Exception as e:
            logger.error(f"Error initializing PdfChatbot: {e}")
            raise

    def initialize_chat_session(self):
        """Create a new chat session with the model and initialize it with system prompt"""
        try:
            logger.info("Initializing chat session")
            system_prompt = (
                "You are a helpful assistant specialized in answering questions about the CUPRA Tavascan vehicle. "
                "Base your answers primarily on the provided document context. "
                "If the context doesn't have specific information but you know the general answer, "
                "provide helpful information but note that it's not from the manual. "
                "Always cite the page numbers from the context when available. "
                "Try to be concise and avoid unnecessary details. "
                "Format your answers as JSON with these fields: "
                "{'answer': 'your detailed response', 'page_numbers': [page numbers you referenced], 'figure_numbers': [relevant figure numbers]}"
            )

            # Inicializar usando la API directamente
            import google.generativeai as genai
            genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
            self.chat_session = genai.GenerativeModel(self.model_name).start_chat(history=[])

            # Initialize with system prompt
            self.chat_session.send_message(system_prompt)
            self.current_context = None
            return self.chat_session
        except Exception as e:
            logger.error(f"Error initializing chat session: {e}")
            raise

    def create_new_chat_session(self):
        """Reset the chat session and start fresh"""
        return self.initialize_chat_session()

    def _find_content_dir(self, content_dir=None):
        """Find content directory if not specified"""
        if content_dir and os.path.exists(content_dir):
            return content_dir

        # Try looking in the current directory first
        current_dir = os.path.dirname(os.path.abspath(__file__))
        logger.info(f"Looking for content in: {current_dir}")

        # Create mock content if needed for testing
        mock_dir = os.path.join(current_dir, "mock_content")
        if not os.path.exists(mock_dir):
            os.makedirs(mock_dir, exist_ok=True)
            with open(os.path.join(mock_dir, "rag_chunks.json"), "w") as f:
                json.dump([{"id": "1", "text": "This is a mock chunk about Cupra Tavascan.",
                          "section_title": "Mock Section", "start_page": 1}], f)

            # Create mock chroma_db
            mock_chroma_dir = os.path.join(mock_dir, "chroma_db")
            os.makedirs(mock_chroma_dir, exist_ok=True)
            logger.info(f"Created mock content directory: {mock_dir}")
            return mock_dir

        # Look for directories that match the pattern "extracted_content_*"
        potential_dirs = []
        for item in os.listdir(current_dir):
            if os.path.isdir(os.path.join(current_dir, item)) and item.startswith("extracted_content_"):
                potential_dirs.append(os.path.join(current_dir, item))

        if potential_dirs:
            logger.info(f"Found content directory: {potential_dirs[0]}")
            return potential_dirs[0]
        else:
            logger.warning("No content directories found, using mock directory")
            return mock_dir

    def _setup_chromadb(self):
        """Set up the ChromaDB connection"""
        try:
            if self.use_chroma:
                # Use persistent client with path to the chroma_db directory
                chroma_dir = os.path.join(self.content_dir, "chroma_db")

                # If chroma_db doesn't exist, create a mock one for testing
                if not os.path.exists(chroma_dir):
                    logger.warning(f"ChromaDB directory not found at {chroma_dir}, creating mock database")
                    os.makedirs(chroma_dir, exist_ok=True)

                # Initialize persistent client
                self.chroma_client = chromadb.PersistentClient(path=chroma_dir)
                sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
                    model_name="all-MiniLM-L6-v2"
                )

                # Create or get collection
                collection_name = f"pdf_chunks_{os.path.basename(self.content_dir)}"
                try:
                    self.collection = self.chroma_client.get_collection(
                        name=collection_name,
                        embedding_function=sentence_transformer_ef
                    )
                    logger.info(f"Connected to existing ChromaDB collection: {collection_name}")
                except Exception:
                    logger.info(f"Creating new ChromaDB collection: {collection_name}")
                    self.collection = self.chroma_client.create_collection(
                        name=collection_name,
                        embedding_function=sentence_transformer_ef
                    )

                    # Add mock data if this is a new collection
                    if len(self.chunks) > 0:
                        self.collection.add(
                            ids=[str(chunk["id"]) for chunk in self.chunks],
                            documents=[chunk["text"] for chunk in self.chunks],
                            metadatas=[{"section": chunk["section_title"], "page": chunk["start_page"]}
                                      for chunk in self.chunks]
                        )
                        logger.info(f"Added {len(self.chunks)} chunks to new collection")
        except Exception as e:
            logger.error(f"Error setting up ChromaDB: {e}")
            raise

    def load_chunks(self):
        """Load the chunks from the JSON file"""
        try:
            chunks_path = os.path.join(self.content_dir, "rag_chunks.json")

            if not os.path.exists(chunks_path):
                logger.warning(f"Chunks file not found at {chunks_path}, creating mock chunks")
                # Crear chunks de ejemplo
                mock_chunks = [
                    {
                        "id": "1",
                        "text": "The CUPRA Tavascan is an all-electric SUV coupé from CUPRA, combining sporty design with electric performance. It features advanced technology and a distinctive look.",
                        "section_title": "Introduction",
                        "start_page": 1
                    },
                    {
                        "id": "2",
                        "text": "The Cupra Tavascan's dashboard features a 15-inch central display with infotainment controls and a digital instrument cluster showing essential driving information.",
                        "section_title": "Interior",
                        "start_page": 5
                    },
                    {
                        "id": "3",
                        "text": "The charging port for the CUPRA Tavascan is located on the rear fender. It supports both AC and fast DC charging options.",
                        "section_title": "Charging",
                        "start_page": 12
                    }
                ]

                # Guardar los chunks mock para uso futuro
                os.makedirs(os.path.dirname(chunks_path), exist_ok=True)
                with open(chunks_path, "w", encoding="utf-8") as f:
                    json.dump(mock_chunks, f)

                self.chunks = mock_chunks
            else:
                with open(chunks_path, "r", encoding="utf-8") as f:
                    self.chunks = json.load(f)

            logger.info(f"Loaded {len(self.chunks)} chunks from {chunks_path}")

            # Crear la colección con estos chunks si aún no tiene documentos
            if hasattr(self, 'collection') and self.collection.count() == 0 and self.chunks:
                logger.info(f"Adding {len(self.chunks)} chunks to empty ChromaDB collection")
                try:
                    self.collection.add(
                        ids=[str(chunk["id"]) for chunk in self.chunks],
                        documents=[chunk["text"] for chunk in self.chunks],
                        metadatas=[{
                            "section": chunk["section_title"],
                            "page": chunk["start_page"]
                        } for chunk in self.chunks]
                    )
                    logger.info("Successfully added chunks to ChromaDB")
                except Exception as e:
                    logger.error(f"Error adding chunks to ChromaDB: {e}")
        except Exception as e:
            logger.error(f"Error loading chunks: {e}")
            self.chunks = []

    def _rerank_chunks(self, chunks, query, top_k=3):
        """Re-rank chunks based on relevance to the query"""
        try:
            # Calculate relevance scores using simple term matching
            query_terms = set(query.lower().split())

            for chunk in chunks:
                # Count term overlap between query and chunk text
                chunk_text = chunk.get('text', '').lower()
                matched_terms = sum(1 for term in query_terms if term in chunk_text)

                # Simple scoring: term frequency + section title match bonus
                score = matched_terms

                # Add bonus for section title matches
                section_title = chunk.get('section_title', '').lower()
                section_match = sum(1 for term in query_terms if term in section_title)
                score += section_match * 2  # Title matches get double weight

                # Store score in chunk
                chunk['score'] = score

            # Sort by score (descending) and return top_k
            ranked_chunks = sorted(chunks, key=lambda x: x.get('score', 0), reverse=True)
            return ranked_chunks[:top_k]
        except Exception as e:
            logger.error(f"Error reranking chunks: {e}")
            return chunks[:top_k]  # Return first chunks as fallback

    def expand_query(self, query):
        """Expand the query with synonyms and related terms"""
        # If query expansion is disabled, return the original query
        if not self.use_query_expansion:
            return query

        try:
            # Use a separate generation model for query expansion
            expansion_prompt = f"""
            I need to expand this search query to improve retrieval results: "{query}"
            
            Please generate:
            1. 2-3 synonymous ways to phrase the same query
            2. 3-4 related keywords that could help in document retrieval
            3. Any potentially disambiguating terms if the query is unclear
            
            Format the output as a single line with all terms separated by spaces.
            Only include relevant terms, no explanations or other text.
            """

            # Método correcto para usar la API de Gemini
            import google.generativeai as genai
            genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
            model = genai.GenerativeModel(self.model_name)
            response = model.generate_content(expansion_prompt)

            expanded_terms = response.text.strip()

            # Combine original query with expanded terms
            expanded_query = f"{query} {expanded_terms}"
            logger.info(f"Expanded query: '{query}' -> '{expanded_query}'")

            return expanded_query

        except Exception as e:
            logger.warning(f"Query expansion error: {str(e)}")
            # Fall back to original query if expansion fails
            return query

    def retrieve_context(self, query, top_k=3):
        """Retrieve relevant context based on the query"""
        try:
            if self.use_chroma and hasattr(self, 'collection'):
                # 1. Verificar si la colección tiene documentos
                if self.collection.count() == 0:
                    logger.warning("ChromaDB collection is empty!")
                    return self.chunks[:top_k] if self.chunks else []

                # 2. Desactivar temporalmente la expansión de consulta para evitar errores
                # expanded_query = self.expand_query(query)
                expanded_query = query  # Usar la consulta original sin expansión

                logger.info(f"Retrieving context for: '{query}'")

                # 3. Aumentar el número de resultados para tener más opciones
                search_top_k = min(top_k * 3, len(self.chunks))
                if search_top_k == 0:
                    logger.warning("No chunks available!")
                    return []

                # 4. Realizar búsqueda con parámetros más permisivos
                results = self.collection.query(
                    query_texts=[expanded_query],
                    n_results=search_top_k,  # Buscamos más resultados de los que necesitamos
                    include=["documents", "metadatas", "distances", "embeddings"]
                )

                # 5. Verificar que se encontraron resultados
                contexts = []
                if results and "ids" in results and results["ids"] and len(results["ids"][0]) > 0:
                    for i, doc_id in enumerate(results["ids"][0]):
                        # Buscar el chunk original
                        found = False
                        for chunk in self.chunks:
                            if str(chunk["id"]) == doc_id:
                                contexts.append({
                                    "text": chunk["text"],
                                    "section_title": chunk["section_title"],
                                    "start_page": chunk["start_page"],
                                    "score": float(results["distances"][0][i]) if "distances" in results else 0.0
                                })
                                found = True
                                break

                        if not found and i < len(results["documents"][0]):
                            # Si no encontramos el chunk original, usar el documento del resultado
                            contexts.append({
                                "text": results["documents"][0][i],
                                "section_title": "Unknown section",
                                "start_page": results["metadatas"][0][i].get("page", 0) if results["metadatas"] else 0,
                                "score": float(results["distances"][0][i]) if "distances" in results else 0.0
                            })

                # 6. Si no hay suficientes contextos, añadir contextos aleatorios
                if len(contexts) < top_k:
                    logger.warning(f"Not enough contexts retrieved, using first {top_k} chunks")
                    # Añadir contextos de chunks que no estén ya en los contextos
                    added = 0
                    for chunk in self.chunks:
                        if added >= (top_k - len(contexts)):
                            break

                        # Verificar si este chunk ya está en los contextos
                        already_added = False
                        for ctx in contexts:
                            if ctx["text"] == chunk["text"]:
                                already_added = True
                                break

                        if not already_added:
                            contexts.append({
                                "text": chunk["text"],
                                "section_title": chunk["section_title"],
                                "start_page": chunk["start_page"],
                                "score": 0.5  # Default score
                            })
                            added += 1

                # 7. Siempre incluye los primeros chunks aunque no sean relevantes
                if len(contexts) < top_k and self.chunks:
                    remaining = top_k - len(contexts)
                    contexts.extend([{
                        "text": chunk["text"],
                        "section_title": chunk["section_title"],
                        "start_page": chunk["start_page"],
                        "score": 0.3  # Menor puntaje para indicar que son menos relevantes
                    } for chunk in self.chunks[:remaining]])

                logger.info(f"Retrieved {len(contexts)} contexts")

                return contexts[:top_k]  # Devolver solo los top_k más relevantes
            else:
                # Si ChromaDB no está disponible, usar búsqueda básica
                logger.warning("ChromaDB not available, using basic context retrieval")
                return self.chunks[:top_k] if self.chunks else []
        except Exception as e:
            logger.error(f"Error retrieving context: {e}")
            # Devolver los primeros chunks como fallback
            return self.chunks[:top_k] if self.chunks else []

    def format_context_for_prompt(self, contexts):
        """Format retrieved contexts for the prompt"""
        context_text = ""

        for i, ctx in enumerate(contexts):
            context_text += f"[Context {i+1} - Page {ctx.get('start_page', 'unknown')} - {ctx.get('section_title', 'Section')}]\n"
            context_text += f"{ctx['text']}\n\n"

        return context_text.strip()

    def get_response(self, query, top_k=3):
        """Get response from Gemini with relevant context"""
        try:
            # Retrieve relevant context based on the query
            contexts = self.retrieve_context(query, top_k=top_k)

            if not contexts:
                context_text = "No relevant context found in the document."
            else:
                context_text = self.format_context_for_prompt(contexts)
                # Save the current context for potential follow-up questions
                self.current_context = context_text

            # If the query seems like a follow-up question and we have previous context
            if (self.is_followup_question(query) and self.current_context):
                # Use current context from the previous query
                full_prompt = f"Based on this document context:\n{self.current_context}\n\nUser Question: {query}"
            else:
                # Use newly retrieved context
                full_prompt = f"Document Context:\n{context_text}\n\nUser Question: {query}"

            # Get response from Gemini using chat session
            response = self.chat_session.send_message(full_prompt)
            logger.info(f"Generated response for query: '{query}'")

            return {
                "text": response.text,
                "contexts": [
                    {
                        "text": ctx["text"],
                        "section_title": ctx["section_title"],
                        "page": ctx["start_page"],
                        "score": ctx.get("score", 0)
                    } for ctx in contexts
                ],
                "query_expanded": query != self.expand_query(query) if self.use_query_expansion else False
            }
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return {
                "text": f"Error generating response: {str(e)}",
                "contexts": [],
                "query_expanded": False,
                "error": str(e)
            }

    def is_followup_question(self, query):
        """Check if the query is likely a follow-up question"""
        followup_indicators = [
            "it", "this", "that", "these", "those", "the", "they", "them",
            "their", "he", "she", "his", "her", "what about", "how about",
            "can you", "tell me more", "explain", "elaborate", "summarize",
            "resume", "continue", "go on", "and", "also", "additionally"
        ]

        query_lower = query.lower()
        # Check if query is short or contains followup indicators
        return (len(query.split()) <= 5 or
                any(indicator in query_lower for indicator in followup_indicators))

    def update_config(self, config):
        """Update chatbot configuration"""
        if "query_expansion" in config and config["query_expansion"] is not None:
            self.use_query_expansion = config["query_expansion"]

        if "model_name" in config and config["model_name"]:
            self.model_name = config["model_name"]
            # Recreate the chat session with the new model
            self.initialize_chat_session()

        return {
            "query_expansion": self.use_query_expansion,
            "model_name": self.model_name
        }

    def get_history(self):
        """Get chat history in a structured format"""
        history = []
        for message in self.chat_session.get_history():
            history.append({
                "role": message.role,
                "content": message.parts[0].text
            })
        return history
from ..chatbot_api import PdfChatbot
# Dictionary to store active chatbot sessions by ID
chatbot_sessions = {}

@app.get("/")
async def root():
    """Root endpoint to check if API is running"""
    return {"message": "PDF Chatbot API is running", "status": "ok"}

@app.post("/sessions/create", status_code=201)
async def create_session(request: NewSessionRequest = Body(...)):
    """Create a new chatbot session"""
    try:
        session_id = str(uuid.uuid4())
        logger.info(f"Creating new session with ID: {session_id}")

        # Default model if not specified or if we encounter problems with the specified one
        model_name = request.model_name or "gemini-1.5-flash"

        chatbot_sessions[session_id] = PdfChatbot(
            content_dir=request.content_dir,
            model_name=model_name
        )
        return {
            "session_id": session_id,
            "model_name": chatbot_sessions[session_id].model_name,
            "content_dir": chatbot_sessions[session_id].content_dir,
            "chunks_loaded": len(chatbot_sessions[session_id].chunks)
        }
    except Exception as e:
        logger.error(f"Error creating session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat")
async def chat(request: ChatRequest = Body(...)):
    """Send a message to the chatbot and get a response"""
    session_id = request.session_id

    # If no session_id provided or session not found, create a new one
    if not session_id or session_id not in chatbot_sessions:
        logger.info(f"No valid session ID provided: {session_id}, creating new session")
        new_session = await create_session(NewSessionRequest())
        session_id = new_session["session_id"]

    try:
        chatbot = chatbot_sessions[session_id]
        logger.info(f"Processing chat request for session {session_id}")
        response = chatbot.get_response(request.query, top_k=request.top_k)

        # Process response to extract JSON
        try:
            response_text = response["text"]
            response_clean = re.sub(r'```json', '', response_text)
            response_clean = re.sub(r'```', '', response_clean)
            parsed_json = json.loads(response_clean)

            return {
                "session_id": session_id,
                "response": parsed_json,
                "contexts": response["contexts"],
                "query_expanded": response["query_expanded"],
                "raw_text": response_text
            }
        except json.JSONDecodeError:
            # If JSON parsing fails, return the raw text
            logger.warning("Failed to parse response as JSON")
            return {
                "session_id": session_id,
                "response": {
                    "answer": response["text"],
                    "page_numbers": [],
                    "figure_numbers": []
                },
                "contexts": response["contexts"],
                "query_expanded": response["query_expanded"],
                "raw_text": response["text"],
                "parsing_error": "Response could not be parsed as JSON"
            }
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/sessions/{session_id}/reset")
async def reset_session(session_id: str):
    """Reset a chatbot session"""
    if session_id not in chatbot_sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        chatbot = chatbot_sessions[session_id]
        chatbot.create_new_chat_session()
        return {"session_id": session_id, "status": "reset"}
    except Exception as e:
        logger.error(f"Error resetting session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/sessions/{session_id}/history")
async def get_session_history(session_id: str):
    """Get chat history for a session"""
    if session_id not in chatbot_sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        chatbot = chatbot_sessions[session_id]
        return {"session_id": session_id, "history": chatbot.get_history()}
    except Exception as e:
        logger.error(f"Error getting history for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.patch("/sessions/{session_id}/config")
async def update_session_config(session_id: str, config: ConfigUpdateRequest = Body(...)):
    """Update configuration for a chatbot session"""
    if session_id not in chatbot_sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        chatbot = chatbot_sessions[session_id]
        updated_config = chatbot.update_config({
            "query_expansion": config.query_expansion,
            "model_name": config.model_name
        })
        return {"session_id": session_id, "config": updated_config}
    except Exception as e:
        logger.error(f"Error updating config for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/sessions")
async def list_sessions():
    """List all active chatbot sessions"""
    sessions = []
    for session_id, chatbot in chatbot_sessions.items():
        sessions.append({
            "session_id": session_id,
            "model_name": chatbot.model_name,
            "content_dir": chatbot.content_dir
        })
    return {"sessions": sessions}

@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a chatbot session"""
    if session_id not in chatbot_sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        del chatbot_sessions[session_id]
        return {"session_id": session_id, "status": "deleted"}
    except Exception as e:
        logger.error(f"Error deleting session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.middleware("http")
async def exception_middleware(request: Request, call_next):
    """Middleware to catch and log exceptions"""
    try:
        return await call_next(request)
    except Exception as e:
        logger.error(f"Unhandled exception: {e}")
        return HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn

    # Check for GEMINI_API_KEY
    if not os.getenv("GEMINI_API_KEY"):
        logger.error("GEMINI_API_KEY environment variable is not set!")
        print("\n*** ERROR: GEMINI_API_KEY not found! ***")
        print("Please set the GEMINI_API_KEY environment variable or add it to a .env file.")
        print("You can get an API key from https://ai.google.dev/")
        sys.exit(1)

    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True, log_level="info")