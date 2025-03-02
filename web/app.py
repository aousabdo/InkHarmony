"""
InkHarmony Web Application

Provides a simple web interface for using the InkHarmony book generation system.
"""
import os
import sys
import json
import time
import logging
from typing import Dict, List, Any, Optional
from threading import Thread
from flask import Flask, render_template, request, jsonify, redirect, url_for, send_file, abort

# Add parent directory to path to ensure modules can be imported
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

# Import from main module instead of app
from inkharmony import ink_harmony
from config import WEB_HOST, WEB_PORT, DEBUG_MODE, SUPPORTED_GENRES
from core.workflow import workflow_manager

# Initialize Flask app
app = Flask(__name__, 
            template_folder=os.path.join(os.path.dirname(__file__), "templates"),
            static_folder=os.path.join(os.path.dirname(__file__), "static"))
app.config['JSON_SORT_KEYS'] = False

# Set up logging
logger = logging.getLogger(__name__)

# Initialize InkHarmony system
try:
    ink_harmony.initialize()
except Exception as e:
    logger.error(f"Error initializing InkHarmony system: {str(e)}")

# Task queue for background tasks
task_results = {}

def run_background_task(task_id, func, *args, **kwargs):
    """Run a task in the background and store the result."""
    try:
        task_results[task_id] = {"status": "running", "started_at": time.time()}
        result = func(*args, **kwargs)
        task_results[task_id] = {"status": "completed", "result": result, "completed_at": time.time()}
    except Exception as e:
        logger.error(f"Error in background task {task_id}: {str(e)}")
        task_results[task_id] = {"status": "failed", "error": str(e), "completed_at": time.time()}

@app.route('/')
def index():
    """Render the main page."""
    # Get list of books
    try:
        books = ink_harmony.list_all_books()
    except Exception as e:
        logger.error(f"Error listing books: {str(e)}")
        books = []
    
    return render_template('index.html', books=books, genres=SUPPORTED_GENRES)

@app.route('/create_book', methods=['POST'])
def create_book():
    """Create a new book."""
    title = request.form.get('title', 'Untitled Book')
    genre = request.form.get('genre', 'fantasy')
    description = request.form.get('description', '')
    style = request.form.get('style', 'descriptive')
    target_audience = request.form.get('target_audience', 'General')
    
    metadata = {
        "title": title,
        "genre": genre,
        "description": description,
        "style": style,
        "target_audience": target_audience
    }
    
    try:
        book_id = ink_harmony.create_book(metadata)
        return redirect(url_for('book_detail', book_id=book_id))
    except Exception as e:
        logger.error(f"Error creating book: {str(e)}")
        return render_template('error.html', error=str(e))

@app.route('/book/<book_id>')
def book_detail(book_id):
    """Render the book detail page."""
    try:
        status = ink_harmony.get_book_status(book_id)
        book_content = ink_harmony.get_book_content(book_id)
        
        # Check if cover exists
        has_cover = book_content.get('has_cover', False)
        
        # Format chapter options for task form
        chapters = []
        for i in range(1, status.get('metadata', {}).get('chapters', 10) + 1):
            chapters.append(i)
        
        return render_template(
            'book_detail.html', 
            book_id=book_id, 
            status=status, 
            content=book_content,
            has_cover=has_cover,
            chapters=chapters
        )
    except Exception as e:
        logger.error(f"Error getting book details: {str(e)}")
        return render_template('error.html', error=str(e))

@app.route('/book/<book_id>/cover')
def book_cover(book_id):
    """Get the book cover image."""
    try:
        from core.storage import BookStorage
        storage = BookStorage(book_id)
        cover_data = storage.load_image("cover", "png")
        
        if not cover_data:
            # Return a default cover or placeholder
            return redirect(url_for('static', filename='placeholder_cover.svg'))
        
        # Save to a temporary file and serve it
        temp_path = os.path.join(os.path.dirname(__file__), "static", "temp", f"{book_id}_cover.png")
        os.makedirs(os.path.dirname(temp_path), exist_ok=True)
        
        with open(temp_path, "wb") as f:
            f.write(cover_data)
            
        return send_file(temp_path, mimetype='image/png')
    except Exception as e:
        logger.error(f"Error getting book cover: {str(e)}")
        return redirect(url_for('static', filename='placeholder_cover.svg'))

@app.route('/book/<book_id>/content/<content_type>')
def book_content(book_id, content_type):
    """Get specific book content."""
    try:
        content = ink_harmony.get_book_content(book_id, content_type)
        return jsonify(content)
    except Exception as e:
        logger.error(f"Error getting book content: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/book/<book_id>/assign_task', methods=['POST'])
def assign_task(book_id):
    """Assign a task to an agent."""
    agent_id = request.form.get('agent_id')
    task_type = request.form.get('task_type')
    
    # Build task details based on the task type
    task_details = {
        "task_description": f"Create {task_type}",
        "book_id": book_id
    }
    
    # Add type-specific details
    if task_type == "outline":
        task_details["task_type"] = "create_full_outline"
    elif task_type == "character_outline":
        task_details["task_type"] = "create_character_outline"
        task_details["character_count"] = int(request.form.get('character_count', 5))
    elif task_type == "chapter":
        task_details["task_type"] = "write_chapter"
        task_details["chapter_number"] = int(request.form.get('chapter_number', 1))
    elif task_type == "polish_chapter":
        task_details["task_type"] = "polish_chapter"
        task_details["chapter_number"] = int(request.form.get('chapter_number', 1))
    elif task_type == "cover_concept":
        task_details["task_type"] = "create_cover_concept"
    elif task_type == "cover_art":
        task_details["task_type"] = "generate_cover_art"
        task_details["prompt"] = request.form.get('prompt', '')
    
    try:
        # Create a background task ID
        task_id = f"task_{int(time.time())}"
        
        # Start the task in a background thread
        thread = Thread(
            target=run_background_task,
            args=(task_id, ink_harmony.assign_task, book_id, agent_id, task_details)
        )
        thread.daemon = True
        thread.start()
        
        return jsonify({"task_id": task_id, "status": "started"})
    except Exception as e:
        logger.error(f"Error assigning task: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/book/<book_id>/progress', methods=['POST'])
def progress_workflow(book_id):
    """Progress the book workflow."""
    action = request.form.get('action', 'next')
    
    try:
        # Start in background thread
        task_id = f"progress_{int(time.time())}"
        
        thread = Thread(
            target=run_background_task,
            args=(task_id, ink_harmony.progress_workflow, book_id, action)
        )
        thread.daemon = True
        thread.start()
        
        return jsonify({"task_id": task_id, "status": "started"})
    except Exception as e:
        logger.error(f"Error progressing workflow: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/book/<book_id>/export', methods=['POST'])
def export_book(book_id):
    """Export the book."""
    try:
        # Create a background task ID
        task_id = f"export_{int(time.time())}"
        
        # Start the export in a background thread
        thread = Thread(
            target=run_background_task,
            args=(task_id, ink_harmony.export_book, book_id)
        )
        thread.daemon = True
        thread.start()
        
        return jsonify({"task_id": task_id, "status": "started"})
    except Exception as e:
        logger.error(f"Error exporting book: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/book/<book_id>/download', methods=['GET'])
def download_book(book_id):
    """Download a book file."""
    from core.storage import BookStorage
    
    file_type = request.args.get('type', 'txt')
    
    try:
        storage = BookStorage(book_id)
        metadata = storage.load_metadata()
        title = metadata.get('title', 'untitled')
        
        if file_type == 'txt':
            # Compile all chapters into a single text file
            chapters = []
            i = 1
            while True:
                chapter = storage.load_component(f"chapter_{i}")
                if not chapter:
                    break
                chapters.append(f"CHAPTER {i}\n\n{chapter}\n\n")
                i += 1
            
            if not chapters:
                return jsonify({"error": "No chapters found"}), 404
                
            # Create a temp file
            temp_path = os.path.join(os.path.dirname(__file__), "static", "temp", f"{title}.txt")
            os.makedirs(os.path.dirname(temp_path), exist_ok=True)
            
            with open(temp_path, 'w', encoding='utf-8') as f:
                f.write(f"{title}\n\n")
                f.write("\n\n".join(chapters))
                
            return send_file(temp_path, as_attachment=True, download_name=f"{title}.txt")
            
        elif file_type == 'json':
            # Export metadata and structure
            book_content = ink_harmony.get_book_content(book_id)
            
            # Create a temp file
            temp_path = os.path.join(os.path.dirname(__file__), "static", "temp", f"{title}.json")
            os.makedirs(os.path.dirname(temp_path), exist_ok=True)
            
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(book_content, f, indent=2)
                
            return send_file(temp_path, as_attachment=True, download_name=f"{title}.json")
            
        elif file_type == 'cover':
            # Download the cover image
            cover_data = storage.load_image("cover", "png")
            if not cover_data:
                return jsonify({"error": "Cover not found"}), 404
                
            # Create a temp file
            temp_path = os.path.join(os.path.dirname(__file__), "static", "temp", f"{title}_cover.png")
            os.makedirs(os.path.dirname(temp_path), exist_ok=True)
            
            with open(temp_path, 'wb') as f:
                f.write(cover_data)
                
            return send_file(temp_path, as_attachment=True, download_name=f"{title}_cover.png")
                
        else:
            return jsonify({"error": "Unsupported file type"}), 400
            
    except Exception as e:
        logger.error(f"Error downloading book: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/task_status/<task_id>', methods=['GET'])
def task_status(task_id):
    """Get the status of a background task."""
    if task_id not in task_results:
        return jsonify({"status": "unknown"})
        
    return jsonify(task_results[task_id])

# Add timestamp filter for templates
@app.template_filter('strftime')
def strftime_filter(timestamp):
    from datetime import datetime
    return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

def main():
    """Start the web application."""
    # Create temp directories
    os.makedirs(os.path.join(os.path.dirname(__file__), "static", "temp"), exist_ok=True)
    
    # Start Flask app
    app.run(host=WEB_HOST, port=WEB_PORT, debug=DEBUG_MODE)

if __name__ == "__main__":
    main()