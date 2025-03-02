"""
Storage utilities for InkHarmony book data.
Handles saving and loading book components and state.
"""
import os
import json
import shutil
from datetime import datetime
from typing import Dict, List, Any, Optional, BinaryIO, Union
import pickle
from pathlib import Path
import sys

# Add the project root directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import BOOK_STORAGE_DIR, IMAGE_STORAGE_DIR

class BookStorage:
    """Manages storage for a book project."""
    
    def __init__(self, book_id: str):
        """
        Initialize storage for a book.
        
        Args:
            book_id: Unique identifier for the book
        """
        self.book_id = book_id
        self.book_dir = os.path.join(BOOK_STORAGE_DIR, book_id)
        self.components_dir = os.path.join(self.book_dir, "components")
        self.versions_dir = os.path.join(self.book_dir, "versions")
        self.images_dir = os.path.join(self.book_dir, "images")
        self.metadata_file = os.path.join(self.book_dir, "metadata.json")
        self.state_file = os.path.join(self.book_dir, "state.pickle")
        
        # Create directories
        for directory in [self.book_dir, self.components_dir, 
                         self.versions_dir, self.images_dir]:
            os.makedirs(directory, exist_ok=True)
    
    def save_metadata(self, metadata: Dict[str, Any]) -> None:
        """
        Save book metadata.
        
        Args:
            metadata: Dictionary of metadata
        """
        with open(self.metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    def load_metadata(self) -> Dict[str, Any]:
        """
        Load book metadata.
        
        Returns:
            Dictionary of metadata
        """
        if not os.path.exists(self.metadata_file):
            return {}
        
        with open(self.metadata_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def save_component(self, component_name: str, content: str, 
                      version: Optional[str] = None) -> str:
        """
        Save a book component (e.g., outline, chapter).
        
        Args:
            component_name: Name of the component
            content: Component content
            version: Optional version label (default: timestamp)
            
        Returns:
            Path to the saved component
        """
        # Create version label if not provided
        if not version:
            version = datetime.now().strftime("%Y%m%d_%H%M%S")
            
        # Create component directory if needed
        component_dir = os.path.join(self.components_dir, component_name)
        os.makedirs(component_dir, exist_ok=True)
        
        # Save current version
        current_file = os.path.join(component_dir, "current.txt")
        with open(current_file, 'w', encoding='utf-8') as f:
            f.write(content)
            
        # Save versioned copy
        version_file = os.path.join(component_dir, f"{version}.txt")
        with open(version_file, 'w', encoding='utf-8') as f:
            f.write(content)
            
        return current_file
    
    def load_component(self, component_name: str, version: str = "current") -> Optional[str]:
        """
        Load a book component.
        
        Args:
            component_name: Name of the component
            version: Version to load (default: current)
            
        Returns:
            Component content or None if not found
        """
        component_dir = os.path.join(self.components_dir, component_name)
        file_path = os.path.join(component_dir, f"{version}.txt")
        
        if not os.path.exists(file_path):
            return None
            
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def list_components(self) -> List[str]:
        """
        List all component names.
        
        Returns:
            List of component names
        """
        if not os.path.exists(self.components_dir):
            return []
            
        return [d for d in os.listdir(self.components_dir) 
                if os.path.isdir(os.path.join(self.components_dir, d))]
    
    def list_component_versions(self, component_name: str) -> List[str]:
        """
        List all versions of a component.
        
        Args:
            component_name: Name of the component
            
        Returns:
            List of version labels
        """
        component_dir = os.path.join(self.components_dir, component_name)
        if not os.path.exists(component_dir):
            return []
            
        versions = [f.replace('.txt', '') for f in os.listdir(component_dir) 
                   if f.endswith('.txt') and f != 'current.txt']
        return sorted(versions)
    
    def save_image(self, image_name: str, image_data: Union[bytes, BinaryIO], 
                  format_extension: str = 'png') -> str:
        """
        Save an image (e.g., cover art).
        
        Args:
            image_name: Name of the image
            image_data: Binary image data or file-like object
            format_extension: File extension (default: png)
            
        Returns:
            Path to the saved image
        """
        # Ensure extension starts with a dot
        if not format_extension.startswith('.'):
            format_extension = f".{format_extension}"
            
        image_path = os.path.join(self.images_dir, f"{image_name}{format_extension}")
        
        # Handle both bytes and file-like objects
        if isinstance(image_data, bytes):
            with open(image_path, 'wb') as f:
                f.write(image_data)
        else:
            with open(image_path, 'wb') as f:
                shutil.copyfileobj(image_data, f)
                
        return image_path
    
    def load_image(self, image_name: str, format_extension: str = 'png') -> Optional[bytes]:
        """
        Load an image.
        
        Args:
            image_name: Name of the image
            format_extension: File extension (default: png)
            
        Returns:
            Binary image data or None if not found
        """
        # Ensure extension starts with a dot
        if not format_extension.startswith('.'):
            format_extension = f".{format_extension}"
            
        image_path = os.path.join(self.images_dir, f"{image_name}{format_extension}")
        
        if not os.path.exists(image_path):
            return None
            
        with open(image_path, 'rb') as f:
            return f.read()
    
    def save_state(self, state: Any) -> None:
        """
        Save workflow state.
        
        Args:
            state: Any pickleable state object
        """
        with open(self.state_file, 'wb') as f:
            pickle.dump(state, f)
    
    def load_state(self) -> Any:
        """
        Load workflow state.
        
        Returns:
            State object or None if not found
        """
        if not os.path.exists(self.state_file):
            return None
            
        with open(self.state_file, 'rb') as f:
            return pickle.load(f)
    
    def export_book(self, export_dir: str) -> Dict[str, str]:
        """
        Export the book to a specified directory.
        
        Args:
            export_dir: Directory to export to
            
        Returns:
            Dictionary mapping file types to paths
        """
        os.makedirs(export_dir, exist_ok=True)
        
        # Export metadata
        metadata = self.load_metadata()
        metadata_path = os.path.join(export_dir, "metadata.json")
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        # Export current components
        components = self.list_components()
        for component in components:
            content = self.load_component(component)
            if content is not None:
                component_path = os.path.join(export_dir, f"{component}.txt")
                with open(component_path, 'w', encoding='utf-8') as f:
                    f.write(content)
        
        # Export images
        if os.path.exists(self.images_dir):
            export_images_dir = os.path.join(export_dir, "images")
            os.makedirs(export_images_dir, exist_ok=True)
            for image_file in os.listdir(self.images_dir):
                src_path = os.path.join(self.images_dir, image_file)
                dst_path = os.path.join(export_images_dir, image_file)
                shutil.copy2(src_path, dst_path)
        
        return {
            "metadata": metadata_path,
            "components": os.path.join(export_dir),
            "images": os.path.join(export_dir, "images") if os.path.exists(self.images_dir) else None
        }


def create_new_book_id() -> str:
    """
    Generate a new unique book ID.
    
    Returns:
        Book ID string
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"book_{timestamp}"


def list_books() -> List[Dict[str, Any]]:
    """
    List all books in storage.
    
    Returns:
        List of book metadata dictionaries
    """
    books = []
    
    if not os.path.exists(BOOK_STORAGE_DIR):
        return books
    
    for book_id in os.listdir(BOOK_STORAGE_DIR):
        book_dir = os.path.join(BOOK_STORAGE_DIR, book_id)
        if not os.path.isdir(book_dir):
            continue
        
        # Load metadata
        metadata_file = os.path.join(book_dir, "metadata.json")
        metadata = {}
        if os.path.exists(metadata_file):
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
            except Exception:
                metadata = {}
        
        # Add book_id and path
        metadata["book_id"] = book_id
        metadata["path"] = book_dir
        
        # Ensure created_at exists
        if "created_at" not in metadata:
            metadata["created_at"] = 0
        
        books.append(metadata)
    
    return sorted(books, key=lambda x: x.get("created_at", 0))


def delete_book(book_id: str) -> bool:
    """
    Delete a book from storage.
    
    Args:
        book_id: ID of the book to delete
        
    Returns:
        True if successful, False otherwise
    """
    book_dir = os.path.join(BOOK_STORAGE_DIR, book_id)
    if not os.path.exists(book_dir):
        return False
    
    try:
        shutil.rmtree(book_dir)
        return True
    except Exception:
        return False