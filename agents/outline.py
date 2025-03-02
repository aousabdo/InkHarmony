"""
Outline Architect Agent for InkHarmony.
Creates detailed book outlines, chapter structures, and character arcs.
"""
import logging
import json
import time
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
from templates.outline_templates import (
    OUTLINE_SYSTEM_PROMPT,
    FULL_OUTLINE_PROMPT,
    CHARACTER_OUTLINE_PROMPT,
    CHAPTER_OUTLINE_PROMPT,
    OUTLINE_REFINEMENT_PROMPT,
    PLOT_ENHANCEMENT_PROMPT
)

# Set up logging
logger = logging.getLogger(__name__)

class OutlineTask(Enum):
    """Types of tasks the Outline Architect can perform."""
    CREATE_FULL_OUTLINE = "create_full_outline"
    CREATE_CHARACTER_OUTLINE = "create_character_outline"
    CREATE_CHAPTER_OUTLINE = "create_chapter_outline"
    REFINE_OUTLINE = "refine_outline"
    ENHANCE_PLOT = "enhance_plot"
    AGENT_TASK = "agent_task"  # Add this for internal agent communication


class OutlineArchitectAgent:
    """
    Outline Architect Agent that creates book structures and plots.
    """
    
    def __init__(self, agent_id: str = "outline"):
        """
        Initialize the Outline Architect Agent.
        
        Args:
            agent_id: Identifier for this agent instance
        """
        self.agent_id = agent_id
        self.active_tasks: Dict[str, Dict[str, Any]] = {}
        
        # Register with message queue
        message_queue.register_agent(self.agent_id)
        
        logger.info(f"Outline Architect Agent initialized with ID: {self.agent_id}")
    
    def run(self) -> None:
        """
        Main agent loop. Processes messages and handles tasks.
        """
        logger.info(f"Outline Architect Agent {self.agent_id} started")
        
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
            if "full outline" in task_desc:
                task_type = OutlineTask.CREATE_FULL_OUTLINE.value
            elif "character" in task_desc:
                task_type = OutlineTask.CREATE_CHARACTER_OUTLINE.value
            elif "chapter" in task_desc:
                task_type = OutlineTask.CREATE_CHAPTER_OUTLINE.value
            elif "refine" in task_desc or "revision" in task_desc:
                task_type = OutlineTask.REFINE_OUTLINE.value
            elif "enhance" in task_desc or "twist" in task_desc:
                task_type = OutlineTask.ENHANCE_PLOT.value
            
        # If message type is "agent_task", use that as task type if no other type is set
        if not task_type and message.message_type == "agent_task":
            task_type = OutlineTask.AGENT_TASK.value
        
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
            if task_type == OutlineTask.CREATE_FULL_OUTLINE.value:
                self._create_full_outline(message)
            elif task_type == OutlineTask.CREATE_CHARACTER_OUTLINE.value:
                self._create_character_outline(message)
            elif task_type == OutlineTask.CREATE_CHAPTER_OUTLINE.value:
                self._create_chapter_outline(message)
            elif task_type == OutlineTask.REFINE_OUTLINE.value:
                self._refine_outline(message)
            elif task_type == OutlineTask.ENHANCE_PLOT.value:
                self._enhance_plot(message)
            elif task_type == OutlineTask.AGENT_TASK.value:
                # Handle agent-to-agent task - determine what to do based on task_description
                task_desc = message.content.get("task_description", "").lower()
                if "refine" in task_desc:
                    self._refine_outline(message)
                elif "enhance" in task_desc:
                    self._enhance_plot(message)
                else:
                    # Default to refine outline if unclear
                    self._refine_outline(message)
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
        
        # Check if we need to refine based on feedback
        feedback_text = message.content.get("feedback", "")
        rating = message.metadata.get("rating", 0)
        
        if rating < 3 or "revise" in feedback_text.lower() or "improve" in feedback_text.lower():
            # Create a refinement task
            logger.info(f"Creating refinement task based on feedback for: {parent_id}")
            
            # Get the original task and result
            original_task = self.active_tasks[parent_id]["message"]
            original_book_id = original_task.content.get("book_id")
            
            if not original_book_id:
                logger.warning("Cannot create refinement task: missing book_id")
                return
                
            # Start a refinement task
            self._refine_based_on_feedback(original_book_id, parent_id, feedback_text)
    
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
    
    def _create_full_outline(self, message: Message) -> None:
        """
        Create a full book outline.
        
        Args:
            message: The task message
        """
        logger.info("Creating full book outline")
        
        try:
            # Extract content from message
            book_id = message.content.get("book_id")
            if not book_id:
                raise ValueError("Missing book_id in task content")
                
            # Get book metadata from workflow
            workflow = workflow_manager.get_workflow(book_id)
            if not workflow:
                raise ValueError(f"Workflow not found for book_id: {book_id}")
                
            metadata = workflow.metadata
            
            # Prepare prompt variables
            prompt_vars = {
                "title": metadata.get("title", "Untitled"),
                "genre": metadata.get("genre", "Fiction"),
                "concept": metadata.get("concept", ""),
                "target_audience": metadata.get("target_audience", "General"),
                "estimated_chapters": metadata.get("estimated_chapters", 10),
                "themes": ", ".join(metadata.get("themes", [""])),
                "additional_notes": message.content.get("additional_notes", "")
            }
            
            # Create prompt
            outline_prompt = FULL_OUTLINE_PROMPT.format(**prompt_vars)
            
            # Get outline from Claude
            claude_messages = [
                get_claude_api().user_message(outline_prompt)
            ]
            
            options = CompletionOptions(
                system=OUTLINE_SYSTEM_PROMPT,
                temperature=0.7,
                max_tokens=4000  # Outlines can be lengthy
            )
            
            claude_response = get_claude_api().complete_with_retry(claude_messages, options)
            
            # Process the response
            try:
                # Parse the response as JSON
                outline = json.loads(claude_response)
            except json.JSONDecodeError:
                # If Claude didn't return valid JSON, try to extract JSON from the response
                import re
                json_match = re.search(r'```json\n(.*?)\n```', claude_response, re.DOTALL)
                if json_match:
                    try:
                        outline = json.loads(json_match.group(1))
                    except json.JSONDecodeError:
                        outline = {"error": "Failed to parse JSON from Claude response"}
                else:
                    # Create a structured outline from the text
                    outline = {
                        "synopsis": claude_response,
                        "error": "Claude did not return valid JSON"
                    }
            
            # Store the outline
            storage = BookStorage(book_id)
            outline_path = storage.save_component("outline", json.dumps(outline, indent=2))
            
            # Update workflow metadata
            metadata.update({
                "outline_created": True,
                "chapters": len(outline.get("chapters", [])),
                "characters": len(outline.get("characters", []))
            })
            workflow.metadata.update(metadata)
            workflow.save_state()
            
            # Return the result
            send_result(
                self.agent_id,
                message.sender,
                {
                    "book_id": book_id,
                    "outline": outline,
                    "outline_path": outline_path
                },
                message.message_id,
                {"book_id": book_id}
            )
            
            # Update task status
            self.active_tasks[message.message_id]["status"] = "completed"
            self.active_tasks[message.message_id]["completed_at"] = time.time()
            self.active_tasks[message.message_id]["result"] = outline
            
        except Exception as e:
            logger.error(f"Error creating outline: {str(e)}")
            send_error(
                self.agent_id,
                message.sender,
                f"Error creating outline: {str(e)}",
                message.message_id,
                {"book_id": message.content.get("book_id")}
            )
            self.active_tasks[message.message_id]["status"] = "failed"
            self.active_tasks[message.message_id]["error"] = str(e)
    
    def _create_character_outline(self, message: Message) -> None:
        """
        Create character outlines.
        
        Args:
            message: The task message
        """
        logger.info("Creating character outline")
        
        try:
            # Extract content from message
            book_id = message.content.get("book_id")
            if not book_id:
                raise ValueError("Missing book_id in task content")
                
            # Get book metadata and existing outline
            storage = BookStorage(book_id)
            metadata_json = storage.load_metadata()
            outline_json = storage.load_component("outline")
            
            if not outline_json:
                raise ValueError("No outline found. Create a full outline first.")
                
            outline = json.loads(outline_json)
            
            # Prepare prompt variables
            prompt_vars = {
                "title": metadata_json.get("title", "Untitled"),
                "genre": metadata_json.get("genre", "Fiction"),
                "concept": metadata_json.get("concept", ""),
                "character_notes": message.content.get("character_notes", ""),
                "synopsis": outline.get("synopsis", ""),
                "character_count": message.content.get("character_count", 5)
            }
            
            # Create prompt
            character_prompt = CHARACTER_OUTLINE_PROMPT.format(**prompt_vars)
            
            # Get character outline from Claude
            claude_messages = [
                get_claude_api().user_message(character_prompt)
            ]
            
            options = CompletionOptions(
                system=OUTLINE_SYSTEM_PROMPT,
                temperature=0.7
            )
            
            claude_response = get_claude_api().complete_with_retry(claude_messages, options)
            
            # Process the response
            try:
                # Parse the response as JSON
                characters = json.loads(claude_response)
            except json.JSONDecodeError:
                # If Claude didn't return valid JSON, try to extract JSON from the response
                import re
                json_match = re.search(r'```json\n(.*?)\n```', claude_response, re.DOTALL)
                if json_match:
                    try:
                        characters = json.loads(json_match.group(1))
                    except json.JSONDecodeError:
                        characters = {"error": "Failed to parse JSON from Claude response"}
                else:
                    # Create a structured character outline from the text
                    characters = {
                        "characters": [
                            {"name": "Character", "description": claude_response}
                        ],
                        "error": "Claude did not return valid JSON"
                    }
            
            # Update the outline with the new character information
            if "characters" in outline:
                outline["characters"] = characters.get("characters", [])
            else:
                outline["characters"] = characters.get("characters", [])
                
            # Save updated outline
            outline_path = storage.save_component("outline", json.dumps(outline, indent=2))
            
            # Save characters as a separate component
            character_path = storage.save_component("characters", json.dumps(characters, indent=2))
            
            # Return the result
            send_result(
                self.agent_id,
                message.sender,
                {
                    "book_id": book_id,
                    "characters": characters,
                    "character_path": character_path,
                    "updated_outline_path": outline_path
                },
                message.message_id,
                {"book_id": book_id}
            )
            
            # Update task status
            self.active_tasks[message.message_id]["status"] = "completed"
            self.active_tasks[message.message_id]["completed_at"] = time.time()
            self.active_tasks[message.message_id]["result"] = characters
            
        except Exception as e:
            logger.error(f"Error creating character outline: {str(e)}")
            send_error(
                self.agent_id,
                message.sender,
                f"Error creating character outline: {str(e)}",
                message.message_id,
                {"book_id": message.content.get("book_id")}
            )
            self.active_tasks[message.message_id]["status"] = "failed"
            self.active_tasks[message.message_id]["error"] = str(e)
    
    def _create_chapter_outline(self, message: Message) -> None:
        """
        Create chapter outlines.
        
        Args:
            message: The task message
        """
        logger.info("Creating chapter outline")
        
        try:
            # Extract content from message
            book_id = message.content.get("book_id")
            if not book_id:
                raise ValueError("Missing book_id in task content")
                
            # Get book metadata and existing outline
            storage = BookStorage(book_id)
            metadata_json = storage.load_metadata()
            outline_json = storage.load_component("outline")
            
            if not outline_json:
                raise ValueError("No outline found. Create a full outline first.")
                
            outline = json.loads(outline_json)
            
            # Get character information
            character_json = storage.load_component("characters")
            characters_text = ""
            if character_json:
                characters = json.loads(character_json)
                for char in characters.get("characters", []):
                    characters_text += f"- {char.get('name', 'Unnamed')}: {char.get('role', 'Unknown role')} - {char.get('description', '')}\n"
            else:
                characters_text = "No detailed character information available."
            
            # Prepare prompt variables
            prompt_vars = {
                "title": metadata_json.get("title", "Untitled"),
                "genre": metadata_json.get("genre", "Fiction"),
                "chapter_count": message.content.get("chapter_count", metadata_json.get("estimated_chapters", 10)),
                "synopsis": outline.get("synopsis", ""),
                "characters": characters_text
            }
            
            # Create prompt
            chapter_prompt = CHAPTER_OUTLINE_PROMPT.format(**prompt_vars)
            
            # Get chapter outline from Claude
            claude_messages = [
                get_claude_api().user_message(chapter_prompt)
            ]
            
            options = CompletionOptions(
                system=OUTLINE_SYSTEM_PROMPT,
                temperature=0.7,
                max_tokens=4000  # Chapter outlines can be lengthy
            )
            
            claude_response = get_claude_api().complete_with_retry(claude_messages, options)
            
            # Process the response
            try:
                # Parse the response as JSON
                chapters = json.loads(claude_response)
            except json.JSONDecodeError:
                # If Claude didn't return valid JSON, try to extract JSON from the response
                import re
                json_match = re.search(r'```json\n(.*?)\n```', claude_response, re.DOTALL)
                if json_match:
                    try:
                        chapters = json.loads(json_match.group(1))
                    except json.JSONDecodeError:
                        chapters = {"error": "Failed to parse JSON from Claude response"}
                else:
                    # Create a structured chapter outline from the text
                    chapters = {
                        "chapters": [
                            {"title": "Chapter", "summary": claude_response}
                        ],
                        "error": "Claude did not return valid JSON"
                    }
            
            # Update the outline with the new chapter information
            if "chapters" in outline:
                outline["chapters"] = chapters.get("chapters", [])
            else:
                outline["chapters"] = chapters.get("chapters", [])
                
            # Save updated outline
            outline_path = storage.save_component("outline", json.dumps(outline, indent=2))
            
            # Save chapters as a separate component
            chapter_path = storage.save_component("chapters", json.dumps(chapters, indent=2))
            
            # Return the result
            send_result(
                self.agent_id,
                message.sender,
                {
                    "book_id": book_id,
                    "chapters": chapters,
                    "chapter_path": chapter_path,
                    "updated_outline_path": outline_path
                },
                message.message_id,
                {"book_id": book_id}
            )
            
            # Update task status
            self.active_tasks[message.message_id]["status"] = "completed"
            self.active_tasks[message.message_id]["completed_at"] = time.time()
            self.active_tasks[message.message_id]["result"] = chapters
            
        except Exception as e:
            logger.error(f"Error creating chapter outline: {str(e)}")
            send_error(
                self.agent_id,
                message.sender,
                f"Error creating chapter outline: {str(e)}",
                message.message_id,
                {"book_id": message.content.get("book_id")}
            )
            self.active_tasks[message.message_id]["status"] = "failed"
            self.active_tasks[message.message_id]["error"] = str(e)
    
    def _refine_outline(self, message: Message) -> None:
        """
        Refine an existing outline.
        
        Args:
            message: The task message
        """
        logger.info("Refining outline")
        
        try:
            # Extract content from message
            book_id = message.content.get("book_id")
            if not book_id:
                raise ValueError("Missing book_id in task content")
                
            # Get existing outline
            storage = BookStorage(book_id)
            outline_json = storage.load_component("outline")
            
            if not outline_json:
                raise ValueError("No outline found to refine.")
                
            # Get feedback from the message
            feedback = message.content.get("feedback", "")
            
            # Prepare prompt variables
            prompt_vars = {
                "current_outline": outline_json,
                "feedback": feedback
            }
            
            # Create prompt
            refinement_prompt = OUTLINE_REFINEMENT_PROMPT.format(**prompt_vars)
            
            # Get refined outline from Claude
            claude_messages = [
                get_claude_api().user_message(refinement_prompt)
            ]
            
            options = CompletionOptions(
                system=OUTLINE_SYSTEM_PROMPT,
                temperature=0.6,  # Slightly lower temperature for refinement
                max_tokens=4000
            )
            
            claude_response = get_claude_api().complete_with_retry(claude_messages, options)
            
            # Process the response
            try:
                # Parse the response as JSON
                refined_outline = json.loads(claude_response)
            except json.JSONDecodeError:
                # If Claude didn't return valid JSON, try to extract JSON from the response
                import re
                json_match = re.search(r'```json\n(.*?)\n```', claude_response, re.DOTALL)
                if json_match:
                    try:
                        refined_outline = json.loads(json_match.group(1))
                    except json.JSONDecodeError:
                        refined_outline = json.loads(outline_json)  # Use original as fallback
                        refined_outline["refinement_error"] = "Failed to parse JSON from Claude response"
                        refined_outline["raw_refinement"] = claude_response
                else:
                    # Use original outline as structure but add refinement notes
                    refined_outline = json.loads(outline_json)
                    refined_outline["refinement_notes"] = claude_response
            
            # Save the refined outline with a version number
            import datetime
            version = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            outline_path = storage.save_component("outline", json.dumps(refined_outline, indent=2), version)
            
            # Return the result
            send_result(
                self.agent_id,
                message.sender,
                {
                    "book_id": book_id,
                    "refined_outline": refined_outline,
                    "outline_path": outline_path,
                    "version": version
                },
                message.message_id,
                {"book_id": book_id}
            )
            
            # Update task status
            self.active_tasks[message.message_id]["status"] = "completed"
            self.active_tasks[message.message_id]["completed_at"] = time.time()
            self.active_tasks[message.message_id]["result"] = refined_outline
            
        except Exception as e:
            logger.error(f"Error refining outline: {str(e)}")
            send_error(
                self.agent_id,
                message.sender,
                f"Error refining outline: {str(e)}",
                message.message_id,
                {"book_id": message.content.get("book_id")}
            )
            self.active_tasks[message.message_id]["status"] = "failed"
            self.active_tasks[message.message_id]["error"] = str(e)
    
    def _enhance_plot(self, message: Message) -> None:
        """
        Enhance a plot with twists or additional elements.
        
        Args:
            message: The task message
        """
        logger.info("Enhancing plot")
        
        try:
            # Extract content from message
            book_id = message.content.get("book_id")
            if not book_id:
                raise ValueError("Missing book_id in task content")
                
            # Get book metadata and existing outline
            storage = BookStorage(book_id)
            metadata_json = storage.load_metadata()
            outline_json = storage.load_component("outline")
            
            if not outline_json:
                raise ValueError("No outline found to enhance.")
                
            # Get enhancement areas from the message
            enhancement_areas = message.content.get("enhancement_areas", "")
            
            # Prepare prompt variables
            prompt_vars = {
                "title": metadata_json.get("title", "Untitled"),
                "genre": metadata_json.get("genre", "Fiction"),
                "current_outline": outline_json,
                "enhancement_areas": enhancement_areas
            }
            
            # Create prompt
            enhancement_prompt = PLOT_ENHANCEMENT_PROMPT.format(**prompt_vars)
            
            # Get plot enhancements from Claude
            claude_messages = [
                get_claude_api().user_message(enhancement_prompt)
            ]
            
            options = CompletionOptions(
                system=OUTLINE_SYSTEM_PROMPT,
                temperature=0.8,  # Higher temperature for creative enhancements
                max_tokens=3000
            )
            
            claude_response = get_claude_api().complete_with_retry(claude_messages, options)
            
            # Process the response
            try:
                # Parse the response as JSON
                enhancements = json.loads(claude_response)
            except json.JSONDecodeError:
                # If Claude didn't return valid JSON, try to extract JSON from the response
                import re
                json_match = re.search(r'```json\n(.*?)\n```', claude_response, re.DOTALL)
                if json_match:
                    try:
                        enhancements = json.loads(json_match.group(1))
                    except json.JSONDecodeError:
                        enhancements = {"error": "Failed to parse JSON from Claude response"}
                else:
                    # Create a structured enhancement from the text
                    enhancements = {
                        "enhancements": [
                            {"description": claude_response}
                        ],
                        "error": "Claude did not return valid JSON"
                    }
            
            # Save the enhancements as a separate component
            enhancement_path = storage.save_component("plot_enhancements", json.dumps(enhancements, indent=2))
            
            # Return the result
            send_result(
                self.agent_id,
                message.sender,
                {
                    "book_id": book_id,
                    "enhancements": enhancements,
                    "enhancement_path": enhancement_path
                },
                message.message_id,
                {"book_id": book_id}
            )
            
            # Update task status
            self.active_tasks[message.message_id]["status"] = "completed"
            self.active_tasks[message.message_id]["completed_at"] = time.time()
            self.active_tasks[message.message_id]["result"] = enhancements
            
        except Exception as e:
            logger.error(f"Error enhancing plot: {str(e)}")
            send_error(
                self.agent_id,
                message.sender,
                f"Error enhancing plot: {str(e)}",
                message.message_id,
                {"book_id": message.content.get("book_id")}
            )
            self.active_tasks[message.message_id]["status"] = "failed"
            self.active_tasks[message.message_id]["error"] = str(e)
    
    def _refine_based_on_feedback(self, book_id: str, parent_task_id: str, feedback: str) -> None:
        """
        Create a refinement task based on feedback.
        
        Args:
            book_id: The book ID
            parent_task_id: The original task ID that received feedback
            feedback: The feedback text
        """
        # Create a new task for self to refine the outline
        task_id = create_task(
            self.agent_id,  # Send from self to self
            self.agent_id,
            "agent_task", 
            {
                "book_id": book_id,
                "task_description": "Refine the book outline based on feedback",
                "feedback": feedback,
                "parent_task_id": parent_task_id
            }
        )
        
        # Process the message
        messages = message_queue.get_messages(self.agent_id)
        for message in messages:
            if message.message_id == task_id:
                self._process_message(message)
                break
