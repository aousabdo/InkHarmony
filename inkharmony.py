"""
InkHarmony: AI-powered Book Generation System

Main application entry point that initializes the agent system
and provides core functionality.
"""
import os
import sys
import logging
import argparse
import threading
import time
import json
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

# Add the current directory to the path to ensure modules can be imported
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Only import config after environment variables are loaded
from config import LOG_LEVEL, LOG_FILE, STORAGE_DIR
from core.messaging import message_queue
from core.workflow import workflow_manager, WorkflowStatus
from core.storage import BookStorage, create_new_book_id, list_books
from agents.maestro import MaestroAgent, MaestroTask
from agents.outline import OutlineArchitectAgent
from agents.narrative import NarrativeWriterAgent
from agents.linguistic import LinguisticPolisherAgent
from agents.visual import VisualDesignCoordinatorAgent

# Set up logging
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class InkHarmony:
    """
    Main application class for the InkHarmony book generation system.
    Manages agents, workflows, and provides the API for the web interface.
    """
    
    def __init__(self):
        """Initialize the InkHarmony system."""
        self.initialized = False
        self.agents = {}
        self.agent_threads = {}
        
        # Ensure storage directories exist
        os.makedirs(STORAGE_DIR, exist_ok=True)
        
        logger.info("InkHarmony system initializing...")
    
    def initialize(self):
        """
        Initialize all agents and system components.
        """
        if self.initialized:
            logger.warning("InkHarmony system already initialized")
            return
        
        logger.info("Starting InkHarmony agents...")
        
        try:
            # Initialize agents
            self.agents["maestro"] = MaestroAgent("maestro")
            self.agents["outline"] = OutlineArchitectAgent("outline")
            self.agents["narrative"] = NarrativeWriterAgent("narrative")
            self.agents["linguistic"] = LinguisticPolisherAgent("linguistic")
            self.agents["visual"] = VisualDesignCoordinatorAgent("visual")
            
            # Start agent threads
            for agent_id, agent in self.agents.items():
                thread = threading.Thread(
                    target=agent.run,
                    name=f"{agent_id}_thread",
                    daemon=True
                )
                self.agent_threads[agent_id] = thread
                thread.start()
                logger.info(f"Started {agent_id} agent thread")
            
            self.initialized = True
            logger.info("InkHarmony system initialized successfully")
        
        except Exception as e:
            logger.error(f"Error initializing InkHarmony system: {str(e)}")
            self.shutdown()
            raise
    
    def shutdown(self):
        """
        Shutdown the InkHarmony system.
        """
        logger.info("Shutting down InkHarmony system...")
        
        # No need to explicitly stop threads as they are daemon threads
        
        self.agent_threads = {}
        self.agents = {}
        self.initialized = False
        
        logger.info("InkHarmony system shutdown complete")
    
    def create_book(self, metadata: Dict[str, Any]) -> str:
        """
        Create a new book project.
        
        Args:
            metadata: Book metadata including title, genre, description, etc.
            
        Returns:
            Book ID
        """
        if not self.initialized:
            self.initialize()
        
        logger.info(f"Creating new book: {metadata.get('title', 'Untitled')}")
        
        try:
            # Create a timestamp for tracking
            metadata["created_at"] = time.time()
            
            # Start book creation via Maestro
            maestro = self.agents.get("maestro")
            if not maestro:
                raise ValueError("Maestro agent not initialized")
            
            book_id = maestro.start_book_creation(metadata)
            
            logger.info(f"Successfully created book with ID: {book_id}")
            return book_id
            
        except Exception as e:
            logger.error(f"Error creating book: {str(e)}")
            raise
    
    def get_book_status(self, book_id: str) -> Dict[str, Any]:
        """
        Get the status of a book project.
        
        Args:
            book_id: The book ID
            
        Returns:
            Book status information
        """
        if not self.initialized:
            self.initialize()
        
        try:
            status = workflow_manager.get_workflow_status(book_id)
            if not status:
                raise ValueError(f"Book not found: {book_id}")
                
            return status
            
        except Exception as e:
            logger.error(f"Error getting book status: {str(e)}")
            raise
    
    def list_all_books(self) -> List[Dict[str, Any]]:
        """
        List all books in the system.
        
        Returns:
            List of book metadata
        """
        try:
            books = list_books()
            return books
            
        except Exception as e:
            logger.error(f"Error listing books: {str(e)}")
            raise
    
    def assign_task(self, book_id: str, agent_id: str, task_details: Dict[str, Any]) -> str:
        """
        Assign a task to an agent for a specific book.
        
        Args:
            book_id: The book ID
            agent_id: The target agent ID
            task_details: Task details
            
        Returns:
            Task ID
        """
        if not self.initialized:
            self.initialize()
        
        logger.info(f"Assigning task to {agent_id} for book {book_id}")
        
        try:
            # Use Maestro to assign the task
            maestro = self.agents.get("maestro")
            if not maestro:
                raise ValueError("Maestro agent not initialized")
            
            # Create a task for Maestro to assign the task
            from core.messaging import create_task, message_queue
            
            task_message_id = create_task(
                "system",
                "maestro",
                MaestroTask.ASSIGN_TASK.value,
                {
                    "book_id": book_id,
                    "agent": agent_id,
                    "task_details": task_details
                }
            )
            
            # Wait for the result (with timeout)
            start_time = time.time()
            timeout = 30  # seconds
            
            while time.time() - start_time < timeout:
                # Check for result messages
                result_messages = message_queue.get_history({
                    "parent_id": task_message_id,
                    "message_type": "result",
                    "sender": "maestro"
                })
                
                if result_messages:
                    result = result_messages[0]
                    return result.content.get("task_id")
                
                time.sleep(0.5)
            
            raise TimeoutError("Timed out waiting for task assignment")
            
        except Exception as e:
            logger.error(f"Error assigning task: {str(e)}")
            raise
    
    def progress_workflow(self, book_id: str, action: str = "next") -> Dict[str, Any]:
        """
        Progress a book workflow to the next phase or perform other workflow actions.
        
        Args:
            book_id: The book ID
            action: The action to take (next, pause, resume)
            
        Returns:
            Updated workflow status
        """
        if not self.initialized:
            self.initialize()
        
        logger.info(f"Progressing workflow for book {book_id} with action: {action}")
        
        try:
            # Use Maestro to progress the workflow
            maestro = self.agents.get("maestro")
            if not maestro:
                raise ValueError("Maestro agent not initialized")
            
            # Create a task for Maestro to progress the workflow
            from core.messaging import create_task, message_queue
            
            task_message_id = create_task(
                "system",
                "maestro",
                MaestroTask.PROGRESS_WORKFLOW.value,
                {
                    "book_id": book_id,
                    "action": action
                }
            )
            
            # Wait for the result (with timeout)
            start_time = time.time()
            timeout = 30  # seconds
            
            while time.time() - start_time < timeout:
                # Check for result messages
                result_messages = message_queue.get_history({
                    "parent_id": task_message_id,
                    "message_type": "result",
                    "sender": "maestro"
                })
                
                if result_messages:
                    result = result_messages[0]
                    return result.content.get("current_status")
                
                time.sleep(0.5)
            
            raise TimeoutError("Timed out waiting for workflow progression")
            
        except Exception as e:
            logger.error(f"Error progressing workflow: {str(e)}")
            raise
    
    def get_book_content(self, book_id: str, content_type: str = "all") -> Dict[str, Any]:
        """
        Get the content of a book.
        
        Args:
            book_id: The book ID
            content_type: Type of content to retrieve (all, outline, chapters, etc.)
            
        Returns:
            Book content
        """
        if not self.initialized:
            self.initialize()
        
        try:
            storage = BookStorage(book_id)
            
            if content_type == "all":
                # Get all available content
                result = {
                    "book_id": book_id,
                    "metadata": storage.load_metadata()
                }
                
                # Try to get outline
                outline_json = storage.load_component("outline")
                if outline_json:
                    try:
                        result["outline"] = json.loads(outline_json)
                    except Exception:
                        result["outline"] = outline_json
                
                # Try to get chapters
                chapters = []
                chapter_names = [c for c in storage.list_components() if c.startswith("chapter_")]
                for chapter_name in sorted(chapter_names):
                    if chapter_name.count('_') == 1:  # Only include main chapters, not sub-components
                        chapter_content = storage.load_component(chapter_name)
                        if chapter_content:
                            chapters.append({
                                "name": chapter_name,
                                "content": chapter_content
                            })
                
                if chapters:
                    result["chapters"] = chapters
                
                # Check if cover exists
                cover_exists = storage.load_image("cover", "png") is not None
                result["has_cover"] = cover_exists
                
                return result
                
            elif content_type == "outline":
                # Get just the outline
                outline_json = storage.load_component("outline")
                if not outline_json:
                    return {"error": "Outline not found"}
                
                try:
                    return {"outline": json.loads(outline_json)}
                except Exception:
                    return {"outline": outline_json}
                    
            elif content_type == "chapters":
                # Get just the chapters
                chapters = []
                chapter_names = [c for c in storage.list_components() if c.startswith("chapter_")]
                for chapter_name in sorted(chapter_names):
                    if chapter_name.count('_') == 1:  # Only include main chapters, not sub-components
                        chapter_content = storage.load_component(chapter_name)
                        if chapter_content:
                            chapters.append({
                                "name": chapter_name,
                                "content": chapter_content
                            })
                
                if not chapters:
                    return {"error": "No chapters found"}
                
                return {"chapters": chapters}
                
            elif content_type.startswith("chapter_"):
                # Get a specific chapter
                chapter_content = storage.load_component(content_type)
                if not chapter_content:
                    return {"error": f"Chapter {content_type} not found"}
                
                return {
                    "chapter": content_type,
                    "content": chapter_content
                }
                
            elif content_type == "cover":
                # Check if cover exists
                cover_data = storage.load_image("cover", "png")
                if not cover_data:
                    return {"error": "Cover not found"}
                
                # We can't return binary data in JSON, so just confirm it exists
                return {"has_cover": True}
                
            else:
                # Try to get a specific component
                component_content = storage.load_component(content_type)
                if not component_content:
                    return {"error": f"Content type {content_type} not found"}
                
                try:
                    return {content_type: json.loads(component_content)}
                except Exception:
                    return {content_type: component_content}
            
        except Exception as e:
            logger.error(f"Error getting book content: {str(e)}")
            raise
    
    def export_book(self, book_id: str, export_dir: Optional[str] = None) -> Dict[str, str]:
        """
        Export a book to files.
        
        Args:
            book_id: The book ID
            export_dir: Optional directory to export to (default: creates a new directory)
            
        Returns:
            Dictionary of exported file paths
        """
        if not self.initialized:
            self.initialize()
        
        try:
            storage = BookStorage(book_id)
            
            # Create export directory if not provided
            if not export_dir:
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                export_dir = os.path.join(os.getcwd(), f"export_{book_id}_{timestamp}")
                
            os.makedirs(export_dir, exist_ok=True)
            
            # Export the book
            export_paths = storage.export_book(export_dir)
            
            # Export cover if it exists
            cover_data = storage.load_image("cover", "png")
            if cover_data:
                cover_path = os.path.join(export_dir, "cover.png")
                with open(cover_path, "wb") as f:
                    f.write(cover_data)
                export_paths["cover"] = cover_path
            
            return export_paths
            
        except Exception as e:
            logger.error(f"Error exporting book: {str(e)}")
            raise


# Global InkHarmony instance
ink_harmony = InkHarmony()

def main():
    """
    Main entry point when running as a script.
    """
    parser = argparse.ArgumentParser(description="InkHarmony - AI Book Generation System")
    parser.add_argument("--initialize", action="store_true", help="Initialize the system")
    parser.add_argument("--create-book", action="store_true", help="Create a new book")
    parser.add_argument("--title", help="Book title (for --create-book)")
    parser.add_argument("--genre", help="Book genre (for --create-book)")
    parser.add_argument("--description", help="Book description (for --create-book)")
    parser.add_argument("--list-books", action="store_true", help="List all books")
    parser.add_argument("--book-id", help="Book ID for operations")
    parser.add_argument("--get-status", action="store_true", help="Get book status")
    parser.add_argument("--export", action="store_true", help="Export a book")
    parser.add_argument("--export-dir", help="Export directory (for --export)")
    
    args = parser.parse_args()
    
    if args.initialize:
        ink_harmony.initialize()
        print("InkHarmony system initialized")
        
    elif args.create_book:
        if not args.title or not args.genre:
            print("Error: --title and --genre are required for book creation")
            return 1
            
        metadata = {
            "title": args.title,
            "genre": args.genre,
            "description": args.description or f"A {args.genre} book titled {args.title}",
            "style": "descriptive",
            "target_audience": "General"
        }
        
        book_id = ink_harmony.create_book(metadata)
        print(f"Book created with ID: {book_id}")
        
    elif args.list_books:
        books = ink_harmony.list_all_books()
        print(f"Found {len(books)} books:")
        for book in books:
            print(f"ID: {book.get('book_id', 'Unknown')}")
            print(f"  Title: {book.get('title', 'Untitled')}")
            print(f"  Genre: {book.get('genre', 'Unknown')}")
            print(f"  Status: {book.get('status', 'Unknown')}")
            print()
            
    elif args.get_status and args.book_id:
        status = ink_harmony.get_book_status(args.book_id)
        print(f"Status for book {args.book_id}:")
        print(f"  Title: {status.get('metadata', {}).get('title', 'Untitled')}")
        print(f"  Genre: {status.get('metadata', {}).get('genre', 'Unknown')}")
        print(f"  Status: {status.get('status', 'Unknown')}")
        print(f"  Current Phase: {status.get('current_phase', 'None')}")
        print("  Phases:")
        for phase_name, phase_info in status.get("phases", {}).items():
            print(f"    {phase_name}: {phase_info.get('status', 'Unknown')}")
            
    elif args.export and args.book_id:
        export_dir = args.export_dir
        paths = ink_harmony.export_book(args.book_id, export_dir)
        print(f"Book exported to: {paths}")
        
    else:
        print("No action specified. Use --help for options.")
        
    return 0

if __name__ == "__main__":
    sys.exit(main())