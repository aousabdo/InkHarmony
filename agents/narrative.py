"""
Narrative Writer Agent for InkHarmony.
Transforms outlines into engaging prose and dialogue.
"""
import logging
import json
import time
import re
from typing import Dict, List, Any, Optional, Tuple, Union
from enum import Enum

from config import AGENTS
from core.messaging import (
    message_queue, Message, MessageType, 
    create_task, send_result, send_feedback, send_error
)
from core.workflow import workflow_manager
from core.storage import BookStorage
from models.claude import get_claude_api, ClaudeMessage, CompletionOptions
from templates.narrative_templates import (
    NARRATIVE_SYSTEM_PROMPT,
    CHAPTER_WRITING_PROMPT,
    CHAPTER_REVISION_PROMPT,
    SCENE_WRITING_PROMPT,
    DIALOGUE_WRITING_PROMPT,
    DESCRIPTION_WRITING_PROMPT,
    OPENING_HOOK_PROMPT,
    CHAPTER_ENDING_PROMPT
)

# Set up logging
logger = logging.getLogger(__name__)

class NarrativeTask(Enum):
    """Types of tasks the Narrative Writer can perform."""
    WRITE_CHAPTER = "write_chapter"
    REVISE_CHAPTER = "revise_chapter"
    WRITE_SCENE = "write_scene"
    WRITE_DIALOGUE = "write_dialogue"
    WRITE_DESCRIPTION = "write_description"
    WRITE_OPENING = "write_opening"
    WRITE_ENDING = "write_ending"
    AGENT_TASK = "agent_task"  # Add this for internal agent communication


class NarrativeWriterAgent:
    """
    Narrative Writer Agent that transforms outlines into prose.
    """
    
    def __init__(self, agent_id: str = "narrative"):
        """
        Initialize the Narrative Writer Agent.
        
        Args:
            agent_id: Identifier for this agent instance
        """
        self.agent_id = agent_id
        self.active_tasks: Dict[str, Dict[str, Any]] = {}
        
        # Register with message queue
        message_queue.register_agent(self.agent_id)
        
        logger.info(f"Narrative Writer Agent initialized with ID: {self.agent_id}")
    
    def run(self) -> None:
        """
        Main agent loop. Processes messages and handles tasks.
        """
        logger.info(f"Narrative Writer Agent {self.agent_id} started")
        
        while True:
            # Process incoming messages
            messages = message_queue.get_messages(self.agent_id)
            for message in messages:
                self._process_message(message)
            
            # Add small delay to avoid CPU spinning
            time.sleep(0.1)
    
    def _process_message(self, message: Message) -> None:
        """
        Process an incoming message.
        
        Args:
            message: The message to process
        """
        logger.debug(f"Processing message: {message.message_id} of type {message.message_type}")
        
        try:
            if message.message_type == MessageType.TASK:
                self._handle_task(message)
            elif message.message_type == MessageType.FEEDBACK:
                self._handle_feedback(message)
            elif message.message_type == MessageType.ERROR:
                self._handle_error(message)
            else:
                logger.warning(f"Unhandled message type: {message.message_type}")
        except Exception as e:
            logger.error(f"Error processing message {message.message_id}: {str(e)}")
            send_error(
                self.agent_id,
                message.sender,
                f"Error processing message: {str(e)}",
                message.message_id
            )
    
    def _handle_task(self, message: Message) -> None:
        """
        Handle a task message.
        
        Args:
            message: The task message
        """
        logger.info(f"Handling task: {message.message_id}")
        
        # Store task in active tasks
        self.active_tasks[message.message_id] = {
            "message": message,
            "status": "processing",
            "started_at": time.time()
        }
        
        # Extract task type from metadata if available, otherwise from content
        task_type = message.metadata.get("task_type")
        if not task_type and "task_description" in message.content:
            task_desc = message.content["task_description"].lower()
            if "write chapter" in task_desc:
                task_type = NarrativeTask.WRITE_CHAPTER.value
            elif "revise chapter" in task_desc:
                task_type = NarrativeTask.REVISE_CHAPTER.value
            elif "write scene" in task_desc:
                task_type = NarrativeTask.WRITE_SCENE.value
            elif "write dialogue" in task_desc:
                task_type = NarrativeTask.WRITE_DIALOGUE.value
            elif "write description" in task_desc:
                task_type = NarrativeTask.WRITE_DESCRIPTION.value
            elif "write opening" in task_desc:
                task_type = NarrativeTask.WRITE_OPENING.value
            elif "write ending" in task_desc:
                task_type = NarrativeTask.WRITE_ENDING.value
                
        # If message type is "agent_task", use that as task type if no other type is set
        if not task_type and message.message_type == "agent_task":
            task_type = NarrativeTask.AGENT_TASK.value
            
        if not task_type:
            send_error(
                self.agent_id,
                message.sender,
                "Could not determine task type",
                message.message_id
            )
            self.active_tasks[message.message_id]["status"] = "failed"
            return
            
        # Process based on task type
        try:
            if task_type == NarrativeTask.WRITE_CHAPTER.value:
                self._write_chapter(message)
            elif task_type == NarrativeTask.REVISE_CHAPTER.value:
                self._revise_chapter(message)
            elif task_type == NarrativeTask.WRITE_SCENE.value:
                self._write_scene(message)
            elif task_type == NarrativeTask.WRITE_DIALOGUE.value:
                self._write_dialogue(message)
            elif task_type == NarrativeTask.WRITE_DESCRIPTION.value:
                self._write_description(message)
            elif task_type == NarrativeTask.WRITE_OPENING.value:
                self._write_opening(message)
            elif task_type == NarrativeTask.WRITE_ENDING.value:
                self._write_ending(message)
            elif task_type == NarrativeTask.AGENT_TASK.value:
                # Handle agent-to-agent task - determine what to do based on task_description
                task_desc = message.content.get("task_description", "").lower()
                if "chapter" in task_desc and "revise" in task_desc:
                    self._revise_chapter(message)
                elif "chapter" in task_desc:
                    self._write_chapter(message)
                else:
                    # Default to revising chapter if unclear
                    self._revise_chapter(message)
            else:
                send_error(
                    self.agent_id,
                    message.sender,
                    f"Unknown task type: {task_type}",
                    message.message_id
                )
                self.active_tasks[message.message_id]["status"] = "failed"
        except Exception as e:
            logger.error(f"Error handling task {message.message_id}: {str(e)}")
            send_error(
                self.agent_id,
                message.sender,
                f"Error handling task: {str(e)}",
                message.message_id
            )
            self.active_tasks[message.message_id]["status"] = "failed"
    
    def _handle_feedback(self, message: Message) -> None:
        """
        Handle feedback on a previous result.
        
        Args:
            message: The feedback message
        """
        parent_id = message.parent_id
        if not parent_id or parent_id not in self.active_tasks:
            logger.warning(f"Received feedback for unknown task: {parent_id}")
            return
            
        # Store feedback
        self.active_tasks[parent_id]["feedback"] = message.content
        
        # Check if we need to revise based on feedback
        feedback_text = message.content.get("feedback", "")
        rating = message.metadata.get("rating", 0)
        
        if rating < 3 or "revise" in feedback_text.lower() or "improve" in feedback_text.lower():
            # Create a revision task
            logger.info(f"Creating revision task based on feedback for: {parent_id}")
            
            # Get the original task and result
            original_task = self.active_tasks[parent_id]["message"]
            original_book_id = original_task.content.get("book_id")
            
            if not original_book_id:
                logger.warning("Cannot create revision task: missing book_id")
                return
                
            # Start a revision task
            self._create_revision_from_feedback(original_book_id, parent_id, feedback_text)
    
    def _handle_error(self, message: Message) -> None:
        """
        Handle an error message.
        
        Args:
            message: The error message
        """
        parent_id = message.parent_id
        if parent_id and parent_id in self.active_tasks:
            self.active_tasks[parent_id]["status"] = "failed"
            self.active_tasks[parent_id]["error"] = message.content.get("error", "Unknown error")
            
        logger.error(f"Received error: {message.content.get('error', 'Unknown error')}")
    
    def _write_chapter(self, message: Message) -> None:
        """
        Write a full chapter.
        
        Args:
            message: The task message
        """
        logger.info("Writing full chapter")
        
        try:
            # Extract content from message
            book_id = message.content.get("book_id")
            chapter_number = message.content.get("chapter_number")
            
            if not book_id or chapter_number is None:
                raise ValueError("Missing book_id or chapter_number in task content")
                
            # Get book metadata, outline, and character info
            storage = BookStorage(book_id)
            metadata_json = storage.load_metadata()
            
            # Load chapter outline
            chapters_json = storage.load_component("chapters")
            if not chapters_json:
                # Try to get chapters from the main outline
                outline_json = storage.load_component("outline")
                if outline_json:
                    outline = json.loads(outline_json)
                    chapters = outline.get("chapters", [])
                else:
                    raise ValueError("No chapters or outline found")
            else:
                chapters = json.loads(chapters_json).get("chapters", [])
            
            # Get specific chapter
            if int(chapter_number) <= 0 or int(chapter_number) > len(chapters):
                raise ValueError(f"Invalid chapter number: {chapter_number}")
                
            chapter_index = int(chapter_number) - 1
            chapter = chapters[chapter_index]
            
            # Get character information
            character_info = "No detailed character information available."
            character_json = storage.load_component("characters")
            if character_json:
                characters = json.loads(character_json).get("characters", [])
                character_info = ""
                for char in characters:
                    character_info += f"- {char.get('name', 'Unnamed')}: {char.get('role', 'Unknown role')}"
                    if 'description' in char:
                        character_info += f" - {char.get('description', '')}"
                    character_info += "\n"
            
            # Get previous chapter summary if available
            previous_chapter = "This is the first chapter."
            if chapter_index > 0:
                prev_chapter = chapters[chapter_index - 1]
                previous_chapter = prev_chapter.get("summary", "No detailed summary available.")
            
            # Construct style guidelines from metadata
            style_guidelines = f"Writing style: {metadata_json.get('style', 'Not specified')}\n"
            style_guidelines += f"Tone: {metadata_json.get('tone', 'Not specified')}\n"
            
            # Key elements to include
            key_elements = ""
            if 'key_events' in chapter:
                key_elements += "Key events:\n"
                for event in chapter.get('key_events', []):
                    key_elements += f"- {event}\n"
                
            if 'character_development' in chapter:
                key_elements += "\nCharacter development:\n"
                for dev in chapter.get('character_development', []):
                    key_elements += f"- {dev}\n"
                    
            if 'themes' in chapter:
                key_elements += "\nThemes to develop:\n"
                for theme in chapter.get('themes', []):
                    key_elements += f"- {theme}\n"
            
            # Target word count (approximately 2000-3000 words per chapter)
            target_word_count = message.content.get("target_word_count", 2500)
            
            # Prepare prompt variables
            prompt_vars = {
                "chapter_number": chapter_number,
                "chapter_title": chapter.get("title", f"Chapter {chapter_number}"),
                "genre": metadata_json.get("genre", "Fiction"),
                "book_title": metadata_json.get("title", "Untitled"),
                "chapter_outline": chapter.get("summary", "No detailed outline available."),
                "character_info": character_info,
                "previous_chapter": previous_chapter,
                "style_guidelines": style_guidelines,
                "key_elements": key_elements,
                "target_word_count": target_word_count
            }
            
            # Create prompt
            chapter_prompt = CHAPTER_WRITING_PROMPT.format(**prompt_vars)
            
            # Generate chapter from Claude
            claude_messages = [
                get_claude_api().user_message(chapter_prompt)
            ]
            
            options = CompletionOptions(
                system=NARRATIVE_SYSTEM_PROMPT,
                temperature=0.7,
                max_tokens=4000  # Chapters can be quite long
            )
            
            claude_response = get_claude_api().complete_with_retry(claude_messages, options)
            
            # Save the chapter
            chapter_content = claude_response.strip()
            
            # Save the chapter
            component_name = f"chapter_{chapter_number}"
            chapter_path = storage.save_component(component_name, chapter_content)
            
            # Update metadata if tracking progress
            if 'chapters_completed' in metadata_json:
                metadata_json['chapters_completed'] = max(
                    metadata_json['chapters_completed'], 
                    int(chapter_number)
                )
            else:
                metadata_json['chapters_completed'] = int(chapter_number)
                
            storage.save_metadata(metadata_json)
            
            # Return the result
            send_result(
                self.agent_id,
                message.sender,
                {
                    "book_id": book_id,
                    "chapter_number": chapter_number,
                    "chapter_title": chapter.get("title", f"Chapter {chapter_number}"),
                    "content": chapter_content,
                    "word_count": len(chapter_content.split()),
                    "path": chapter_path
                },
                message.message_id,
                {"book_id": book_id}
            )
            
            # Update task status
            self.active_tasks[message.message_id]["status"] = "completed"
            self.active_tasks[message.message_id]["completed_at"] = time.time()
            self.active_tasks[message.message_id]["result"] = {
                "chapter_number": chapter_number,
                "title": chapter.get("title", f"Chapter {chapter_number}"),
                "word_count": len(chapter_content.split())
            }
            
        except Exception as e:
            logger.error(f"Error writing chapter: {str(e)}")
            send_error(
                self.agent_id,
                message.sender,
                f"Error writing chapter: {str(e)}",
                message.message_id,
                {"book_id": message.content.get("book_id")}
            )
            self.active_tasks[message.message_id]["status"] = "failed"
            self.active_tasks[message.message_id]["error"] = str(e)
    
    def _revise_chapter(self, message: Message) -> None:
        """
        Revise an existing chapter.
        
        Args:
            message: The task message
        """
        logger.info("Revising chapter")
        
        try:
            # Extract content from message
            book_id = message.content.get("book_id")
            chapter_number = message.content.get("chapter_number")
            revision_instructions = message.content.get("revision_instructions", "")
            
            if not book_id or chapter_number is None:
                raise ValueError("Missing book_id or chapter_number in task content")
                
            # Get book metadata
            storage = BookStorage(book_id)
            metadata_json = storage.load_metadata()
            
            # Load the original chapter
            component_name = f"chapter_{chapter_number}"
            original_chapter = storage.load_component(component_name)
            
            if not original_chapter:
                raise ValueError(f"Chapter {chapter_number} not found")
            
            # Get chapter title from outline if available
            chapter_title = f"Chapter {chapter_number}"
            chapters_json = storage.load_component("chapters")
            if chapters_json:
                chapters = json.loads(chapters_json).get("chapters", [])
                if 0 <= int(chapter_number) - 1 < len(chapters):
                    chapter = chapters[int(chapter_number) - 1]
                    chapter_title = chapter.get("title", chapter_title)
            
            # Get character information
            character_info = "No detailed character information available."
            character_json = storage.load_component("characters")
            if character_json:
                characters = json.loads(character_json).get("characters", [])
                character_info = ""
                for char in characters:
                    character_info += f"- {char.get('name', 'Unnamed')}: {char.get('role', 'Unknown role')}"
                    if 'description' in char:
                        character_info += f" - {char.get('description', '')}"
                    character_info += "\n"
            
            # Construct style guidelines from metadata
            style_guidelines = f"Writing style: {metadata_json.get('style', 'Not specified')}\n"
            style_guidelines += f"Tone: {metadata_json.get('tone', 'Not specified')}\n"
            
            # Prepare prompt variables
            prompt_vars = {
                "chapter_number": chapter_number,
                "chapter_title": chapter_title,
                "genre": metadata_json.get("genre", "Fiction"),
                "book_title": metadata_json.get("title", "Untitled"),
                "original_chapter": original_chapter,
                "revision_instructions": revision_instructions,
                "character_info": character_info,
                "style_guidelines": style_guidelines
            }
            
            # Create prompt
            revision_prompt = CHAPTER_REVISION_PROMPT.format(**prompt_vars)
            
            # Generate revised chapter from Claude
            claude_messages = [
                get_claude_api().user_message(revision_prompt)
            ]
            
            options = CompletionOptions(
                system=NARRATIVE_SYSTEM_PROMPT,
                temperature=0.6,  # Slightly lower temperature for revisions
                max_tokens=4000
            )
            
            claude_response = get_claude_api().complete_with_retry(claude_messages, options)
            
            # Save the revised chapter with a version number
            import datetime
            version = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            revised_content = claude_response.strip()
            chapter_path = storage.save_component(component_name, revised_content, version)
            
            # Return the result
            send_result(
                self.agent_id,
                message.sender,
                {
                    "book_id": book_id,
                    "chapter_number": chapter_number,
                    "chapter_title": chapter_title,
                    "content": revised_content,
                    "word_count": len(revised_content.split()),
                    "path": chapter_path,
                    "version": version
                },
                message.message_id,
                {"book_id": book_id}
            )
            
            # Update task status
            self.active_tasks[message.message_id]["status"] = "completed"
            self.active_tasks[message.message_id]["completed_at"] = time.time()
            self.active_tasks[message.message_id]["result"] = {
                "chapter_number": chapter_number,
                "title": chapter_title,
                "word_count": len(revised_content.split()),
                "version": version
            }
            
        except Exception as e:
            logger.error(f"Error revising chapter: {str(e)}")
            send_error(
                self.agent_id,
                message.sender,
                f"Error revising chapter: {str(e)}",
                message.message_id,
                {"book_id": message.content.get("book_id")}
            )
            self.active_tasks[message.message_id]["status"] = "failed"
            self.active_tasks[message.message_id]["error"] = str(e)
    
    def _write_scene(self, message: Message) -> None:
        """
        Write a specific scene.
        
        Args:
            message: The task message
        """
        logger.info("Writing scene")
        
        try:
            # Extract content from message
            book_id = message.content.get("book_id")
            chapter_number = message.content.get("chapter_number")
            scene_context = message.content.get("scene_context", "")
            characters_present = message.content.get("characters_present", "")
            setting = message.content.get("setting", "")
            key_events = message.content.get("key_events", "")
            emotional_tone = message.content.get("emotional_tone", "")
            
            if not book_id or chapter_number is None:
                raise ValueError("Missing book_id or chapter_number in task content")
                
            # Get book metadata
            storage = BookStorage(book_id)
            metadata_json = storage.load_metadata()
            
            # Construct style guidelines from metadata
            style_guidelines = f"Writing style: {metadata_json.get('style', 'Not specified')}\n"
            style_guidelines += f"Tone: {metadata_json.get('tone', 'Not specified')}\n"
            
            # If characters_present is a list, format it
            if isinstance(characters_present, list):
                characters_present = "\n".join([f"- {char}" for char in characters_present])
                
            # If key_events is a list, format it
            if isinstance(key_events, list):
                key_events = "\n".join([f"- {event}" for event in key_events])
            
            # Prepare prompt variables
            prompt_vars = {
                "chapter_number": chapter_number,
                "genre": metadata_json.get("genre", "Fiction"),
                "book_title": metadata_json.get("title", "Untitled"),
                "scene_context": scene_context,
                "characters_present": characters_present,
                "setting": setting,
                "key_events": key_events,
                "emotional_tone": emotional_tone,
                "style_guidelines": style_guidelines
            }
            
            # Create prompt
            scene_prompt = SCENE_WRITING_PROMPT.format(**prompt_vars)
            
            # Generate scene from Claude
            claude_messages = [
                get_claude_api().user_message(scene_prompt)
            ]
            
            options = CompletionOptions(
                system=NARRATIVE_SYSTEM_PROMPT,
                temperature=0.7,
                max_tokens=3000
            )
            
            claude_response = get_claude_api().complete_with_retry(claude_messages, options)
            
            # Process and save the scene
            scene_content = claude_response.strip()
            
            # Create a clean scene identifier
            scene_id = re.sub(r'[^a-zA-Z0-9]', '_', scene_context[:20]).lower()
            scene_id = f"scene_{scene_id}_{int(time.time())}"
            
            # Save as a component
            scene_path = storage.save_component(f"chapter_{chapter_number}_scenes", 
                                              f"{scene_id}\n\n{scene_content}")
            
            # Return the result
            send_result(
                self.agent_id,
                message.sender,
                {
                    "book_id": book_id,
                    "chapter_number": chapter_number,
                    "scene_id": scene_id,
                    "content": scene_content,
                    "word_count": len(scene_content.split()),
                    "path": scene_path
                },
                message.message_id,
                {"book_id": book_id}
            )
            
            # Update task status
            self.active_tasks[message.message_id]["status"] = "completed"
            self.active_tasks[message.message_id]["completed_at"] = time.time()
            self.active_tasks[message.message_id]["result"] = {
                "chapter_number": chapter_number,
                "scene_id": scene_id,
                "word_count": len(scene_content.split())
            }
            
        except Exception as e:
            logger.error(f"Error writing scene: {str(e)}")
            send_error(
                self.agent_id,
                message.sender,
                f"Error writing scene: {str(e)}",
                message.message_id,
                {"book_id": message.content.get("book_id")}
            )
            self.active_tasks[message.message_id]["status"] = "failed"
            self.active_tasks[message.message_id]["error"] = str(e)
    
    def _write_dialogue(self, message: Message) -> None:
        """
        Write dialogue for a scene.
        
        Args:
            message: The task message
        """
        logger.info("Writing dialogue")
        
        try:
            # Extract content from message
            book_id = message.content.get("book_id")
            chapter_number = message.content.get("chapter_number")
            scene_context = message.content.get("scene_context", "")
            characters = message.content.get("characters", "")
            conversation_purpose = message.content.get("conversation_purpose", "")
            character_relationships = message.content.get("character_relationships", "")
            emotional_undercurrents = message.content.get("emotional_undercurrents", "")
            key_reveals = message.content.get("key_reveals", "")
            
            if not book_id or chapter_number is None:
                raise ValueError("Missing book_id or chapter_number in task content")
                
            # Get book metadata
            storage = BookStorage(book_id)
            metadata_json = storage.load_metadata()
            
            # Construct style guidelines from metadata
            style_guidelines = f"Writing style: {metadata_json.get('style', 'Not specified')}\n"
            style_guidelines += f"Tone: {metadata_json.get('tone', 'Not specified')}\n"
            
            # If characters is a list, format it
            if isinstance(characters, list):
                characters = "\n".join([f"- {char}" for char in characters])
                
            # If key_reveals is a list, format it
            if isinstance(key_reveals, list):
                key_reveals = "\n".join([f"- {reveal}" for reveal in key_reveals])
            
            # Prepare prompt variables
            prompt_vars = {
                "chapter_number": chapter_number,
                "genre": metadata_json.get("genre", "Fiction"),
                "book_title": metadata_json.get("title", "Untitled"),
                "scene_context": scene_context,
                "characters": characters,
                "conversation_purpose": conversation_purpose,
                "character_relationships": character_relationships,
                "emotional_undercurrents": emotional_undercurrents,
                "key_reveals": key_reveals,
                "style_guidelines": style_guidelines
            }
            
            # Create prompt
            dialogue_prompt = DIALOGUE_WRITING_PROMPT.format(**prompt_vars)
            
            # Generate dialogue from Claude
            claude_messages = [
                get_claude_api().user_message(dialogue_prompt)
            ]
            
            options = CompletionOptions(
                system=NARRATIVE_SYSTEM_PROMPT,
                temperature=0.7,
                max_tokens=2500
            )
            
            claude_response = get_claude_api().complete_with_retry(claude_messages, options)
            
            # Process and save the dialogue
            dialogue_content = claude_response.strip()
            
            # Create a clean dialogue identifier
            dialogue_id = re.sub(r'[^a-zA-Z0-9]', '_', conversation_purpose[:20]).lower()
            dialogue_id = f"dialogue_{dialogue_id}_{int(time.time())}"
            
            # Save as a component
            dialogue_path = storage.save_component(f"chapter_{chapter_number}_dialogues", 
                                                 f"{dialogue_id}\n\n{dialogue_content}")
            
            # Return the result
            send_result(
                self.agent_id,
                message.sender,
                {
                    "book_id": book_id,
                    "chapter_number": chapter_number,
                    "dialogue_id": dialogue_id,
                    "content": dialogue_content,
                    "word_count": len(dialogue_content.split()),
                    "path": dialogue_path
                },
                message.message_id,
                {"book_id": book_id}
            )
            
            # Update task status
            self.active_tasks[message.message_id]["status"] = "completed"
            self.active_tasks[message.message_id]["completed_at"] = time.time()
            self.active_tasks[message.message_id]["result"] = {
                "chapter_number": chapter_number,
                "dialogue_id": dialogue_id,
                "word_count": len(dialogue_content.split())
            }
            
        except Exception as e:
            logger.error(f"Error writing dialogue: {str(e)}")
            send_error(
                self.agent_id,
                message.sender,
                f"Error writing dialogue: {str(e)}",
                message.message_id,
                {"book_id": message.content.get("book_id")}
            )
            self.active_tasks[message.message_id]["status"] = "failed"
            self.active_tasks[message.message_id]["error"] = str(e)
    
    def _write_description(self, message: Message) -> None:
        """
        Write a descriptive passage.
        
        Args:
            message: The task message
        """
        logger.info("Writing description")
        
        try:
            # Extract content from message
            book_id = message.content.get("book_id")
            chapter_number = message.content.get("chapter_number")
            description_subject = message.content.get("description_subject", "")
            story_relevance = message.content.get("story_relevance", "")
            emotional_tone = message.content.get("emotional_tone", "")
            sensory_elements = message.content.get("sensory_elements", "")
            pov_perspective = message.content.get("pov_perspective", "")
            
            if not book_id or chapter_number is None:
                raise ValueError("Missing book_id or chapter_number in task content")
                
            # Get book metadata
            storage = BookStorage(book_id)
            metadata_json = storage.load_metadata()
            
            # Construct style guidelines from metadata
            style_guidelines = f"Writing style: {metadata_json.get('style', 'Not specified')}\n"
            style_guidelines += f"Tone: {metadata_json.get('tone', 'Not specified')}\n"
            
            # If sensory_elements is a list, format it
            if isinstance(sensory_elements, list):
                sensory_elements = "\n".join([f"- {sense}" for sense in sensory_elements])
            
            # Prepare prompt variables
            prompt_vars = {
                "chapter_number": chapter_number,
                "genre": metadata_json.get("genre", "Fiction"),
                "book_title": metadata_json.get("title", "Untitled"),
                "description_subject": description_subject,
                "story_relevance": story_relevance,
                "emotional_tone": emotional_tone,
                "sensory_elements": sensory_elements,
                "pov_perspective": pov_perspective,
                "style_guidelines": style_guidelines
            }
            
            # Create prompt
            description_prompt = DESCRIPTION_WRITING_PROMPT.format(**prompt_vars)
            
            # Generate description from Claude
            claude_messages = [
                get_claude_api().user_message(description_prompt)
            ]
            
            options = CompletionOptions(
                system=NARRATIVE_SYSTEM_PROMPT,
                temperature=0.7,
                max_tokens=2000
            )
            
            claude_response = get_claude_api().complete_with_retry(claude_messages, options)
            
            # Process and save the description
            description_content = claude_response.strip()
            
            # Create a clean description identifier
            description_id = re.sub(r'[^a-zA-Z0-9]', '_', description_subject[:20]).lower()
            description_id = f"desc_{description_id}_{int(time.time())}"
            
            # Save as a component
            description_path = storage.save_component(f"chapter_{chapter_number}_descriptions", 
                                                    f"{description_id}\n\n{description_content}")
            
            # Return the result
            send_result(
                self.agent_id,
                message.sender,
                {
                    "book_id": book_id,
                    "chapter_number": chapter_number,
                    "description_id": description_id,
                    "content": description_content,
                    "word_count": len(description_content.split()),
                    "path": description_path
                },
                message.message_id,
                {"book_id": book_id}
            )
            
            # Update task status
            self.active_tasks[message.message_id]["status"] = "completed"
            self.active_tasks[message.message_id]["completed_at"] = time.time()
            self.active_tasks[message.message_id]["result"] = {
                "chapter_number": chapter_number,
                "description_id": description_id,
                "word_count": len(description_content.split())
            }
            
        except Exception as e:
            logger.error(f"Error writing description: {str(e)}")
            send_error(
                self.agent_id,
                message.sender,
                f"Error writing description: {str(e)}",
                message.message_id,
                {"book_id": message.content.get("book_id")}
            )
            self.active_tasks[message.message_id]["status"] = "failed"
            self.active_tasks[message.message_id]["error"] = str(e)
    
    def _write_opening(self, message: Message) -> None:
        """
        Write a chapter opening hook.
        
        Args:
            message: The task message
        """
        logger.info("Writing chapter opening")
        
        try:
            # Extract content from message
            book_id = message.content.get("book_id")
            chapter_number = message.content.get("chapter_number")
            chapter_context = message.content.get("chapter_context", "")
            chapter_purpose = message.content.get("chapter_purpose", "")
            emotional_tone = message.content.get("emotional_tone", "")
            pov_character = message.content.get("pov_character", "")
            
            if not book_id or chapter_number is None:
                raise ValueError("Missing book_id or chapter_number in task content")
                
            # Get book metadata
            storage = BookStorage(book_id)
            metadata_json = storage.load_metadata()
            
            # Construct style guidelines from metadata
            style_guidelines = f"Writing style: {metadata_json.get('style', 'Not specified')}\n"
            style_guidelines += f"Tone: {metadata_json.get('tone', 'Not specified')}\n"
            
            # Prepare prompt variables
            prompt_vars = {
                "chapter_number": chapter_number,
                "genre": metadata_json.get("genre", "Fiction"),
                "book_title": metadata_json.get("title", "Untitled"),
                "chapter_context": chapter_context,
                "chapter_purpose": chapter_purpose,
                "emotional_tone": emotional_tone,
                "pov_character": pov_character,
                "style_guidelines": style_guidelines
            }
            
            # Create prompt
            opening_prompt = OPENING_HOOK_PROMPT.format(**prompt_vars)
            
            # Generate opening from Claude
            claude_messages = [
                get_claude_api().user_message(opening_prompt)
            ]
            
            options = CompletionOptions(
                system=NARRATIVE_SYSTEM_PROMPT,
                temperature=0.8,  # Higher temperature for creative openings
                max_tokens=1500
            )
            
            claude_response = get_claude_api().complete_with_retry(claude_messages, options)
            
            # Process and save the opening
            opening_content = claude_response.strip()
            
            # Save as a component
            opening_path = storage.save_component(f"chapter_{chapter_number}_opening", opening_content)
            
            # Return the result
            send_result(
                self.agent_id,
                message.sender,
                {
                    "book_id": book_id,
                    "chapter_number": chapter_number,
                    "content": opening_content,
                    "word_count": len(opening_content.split()),
                    "path": opening_path
                },
                message.message_id,
                {"book_id": book_id}
            )
            
            # Update task status
            self.active_tasks[message.message_id]["status"] = "completed"
            self.active_tasks[message.message_id]["completed_at"] = time.time()
            self.active_tasks[message.message_id]["result"] = {
                "chapter_number": chapter_number,
                "word_count": len(opening_content.split())
            }
            
        except Exception as e:
            logger.error(f"Error writing chapter opening: {str(e)}")
            send_error(
                self.agent_id,
                message.sender,
                f"Error writing chapter opening: {str(e)}",
                message.message_id,
                {"book_id": message.content.get("book_id")}
            )
            self.active_tasks[message.message_id]["status"] = "failed"
            self.active_tasks[message.message_id]["error"] = str(e)
    
    def _write_ending(self, message: Message) -> None:
        """
        Write a chapter ending.
        
        Args:
            message: The task message
        """
        logger.info("Writing chapter ending")
        
        try:
            # Extract content from message
            book_id = message.content.get("book_id")
            chapter_number = message.content.get("chapter_number")
            chapter_summary = message.content.get("chapter_summary", "")
            next_chapter_preview = message.content.get("next_chapter_preview", "")
            emotional_impact = message.content.get("emotional_impact", "")
            plot_threads = message.content.get("plot_threads", "")
            
            if not book_id or chapter_number is None:
                raise ValueError("Missing book_id or chapter_number in task content")
                
            # Get book metadata
            storage = BookStorage(book_id)
            metadata_json = storage.load_metadata()
            
            # Construct style guidelines from metadata
            style_guidelines = f"Writing style: {metadata_json.get('style', 'Not specified')}\n"
            style_guidelines += f"Tone: {metadata_json.get('tone', 'Not specified')}\n"
            
            # If plot_threads is a list, format it
            if isinstance(plot_threads, list):
                plot_threads = "\n".join([f"- {thread}" for thread in plot_threads])
            
            # Prepare prompt variables
            prompt_vars = {
                "chapter_number": chapter_number,
                "genre": metadata_json.get("genre", "Fiction"),
                "book_title": metadata_json.get("title", "Untitled"),
                "chapter_summary": chapter_summary,
                "next_chapter_preview": next_chapter_preview,
                "emotional_impact": emotional_impact,
                "plot_threads": plot_threads,
                "style_guidelines": style_guidelines
            }
            
            # Create prompt
            ending_prompt = CHAPTER_ENDING_PROMPT.format(**prompt_vars)
            
            # Generate ending from Claude
            claude_messages = [
                get_claude_api().user_message(ending_prompt)
            ]
            
            options = CompletionOptions(
                system=NARRATIVE_SYSTEM_PROMPT,
                temperature=0.7,
                max_tokens=1500
            )
            
            claude_response = get_claude_api().complete_with_retry(claude_messages, options)
            
            # Process and save the ending
            ending_content = claude_response.strip()
            
            # Save as a component
            ending_path = storage.save_component(f"chapter_{chapter_number}_ending", ending_content)
            
            # Return the result
            send_result(
                self.agent_id,
                message.sender,
                {
                    "book_id": book_id,
                    "chapter_number": chapter_number,
                    "content": ending_content,
                    "word_count": len(ending_content.split()),
                    "path": ending_path
                },
                message.message_id,
                {"book_id": book_id}
            )
            
            # Update task status
            self.active_tasks[message.message_id]["status"] = "completed"
            self.active_tasks[message.message_id]["completed_at"] = time.time()
            self.active_tasks[message.message_id]["result"] = {
                "chapter_number": chapter_number,
                "word_count": len(ending_content.split())
            }
            
        except Exception as e:
            logger.error(f"Error writing chapter ending: {str(e)}")
            send_error(
                self.agent_id,
                message.sender,
                f"Error writing chapter ending: {str(e)}",
                message.message_id,
                {"book_id": message.content.get("book_id")}
            )
            self.active_tasks[message.message_id]["status"] = "failed"
            self.active_tasks[message.message_id]["error"] = str(e)
    
    def _create_revision_from_feedback(self, book_id: str, parent_task_id: str, feedback: str) -> None:
        """
        Create a revision task based on feedback.
        
        Args:
            book_id: The book ID
            parent_task_id: The original task ID that received feedback
            feedback: The feedback text
        """
        # Get original task details
        original_task = self.active_tasks[parent_task_id]["message"]
        
        # Determine what type of content needs revision
        task_content = {
            "book_id": book_id,
            "revision_instructions": feedback,
            "parent_task_id": parent_task_id
        }
        
        # Add specific fields based on the original task
        if "chapter_number" in original_task.content:
            task_content["chapter_number"] = original_task.content["chapter_number"]
            task_content["task_description"] = f"Revise chapter {original_task.content['chapter_number']} based on feedback"
        
        # Create a new task for self to revise the content
        task_id = create_task(
            self.agent_id,  # Send from self to self
            self.agent_id,
            "agent_task", 
            task_content
        )
        
        # Process the message
        messages = message_queue.get_messages(self.agent_id)
        for message in messages:
            if message.message_id == task_id:
                self._process_message(message)
                break
