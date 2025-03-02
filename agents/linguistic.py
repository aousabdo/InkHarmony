"""
Linguistic Polisher Agent for InkHarmony.
Refines and enhances the language, grammar, style, and readability of book content.
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
from templates.linguistic_templates import (
    LINGUISTIC_SYSTEM_PROMPT,
    CHAPTER_POLISH_PROMPT,
    LANGUAGE_ANALYSIS_PROMPT,
    STYLE_CONSISTENCY_PROMPT,
    READABILITY_ENHANCEMENT_PROMPT,
    DIALOGUE_POLISH_PROMPT,
    CONTINUITY_CHECK_PROMPT
)

# Set up logging
logger = logging.getLogger(__name__)

class LinguisticTask(Enum):
    """Types of tasks the Linguistic Polisher can perform."""
    POLISH_CHAPTER = "polish_chapter"
    ANALYZE_TEXT = "analyze_text"
    IMPROVE_STYLE = "improve_style"
    ENHANCE_READABILITY = "enhance_readability"
    REFINE_DIALOGUE = "refine_dialogue"
    CHECK_CONTINUITY = "check_continuity"
    AGENT_TASK = "agent_task"  # Add this for internal agent communication


class LinguisticPolisherAgent:
    """
    Linguistic Polisher Agent that refines language quality.
    """
    
    def __init__(self, agent_id: str = "linguistic"):
        """
        Initialize the Linguistic Polisher Agent.
        
        Args:
            agent_id: Identifier for this agent instance
        """
        self.agent_id = agent_id
        self.active_tasks: Dict[str, Dict[str, Any]] = {}
        
        # Register with message queue
        message_queue.register_agent(self.agent_id)
        
        logger.info(f"Linguistic Polisher Agent initialized with ID: {self.agent_id}")
    
    def run(self) -> None:
        """
        Main agent loop. Processes messages and handles tasks.
        """
        logger.info(f"Linguistic Polisher Agent {self.agent_id} started")
        
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
            if "polish chapter" in task_desc or "chapter polish" in task_desc:
                task_type = LinguisticTask.POLISH_CHAPTER.value
            elif "language analysis" in task_desc or "analyze language" in task_desc:
                task_type = LinguisticTask.ANALYZE_TEXT.value
            elif "style consistency" in task_desc or "check style" in task_desc:
                task_type = LinguisticTask.IMPROVE_STYLE.value
            elif "readability" in task_desc or "enhance readability" in task_desc:
                task_type = LinguisticTask.ENHANCE_READABILITY.value
            elif "polish dialogue" in task_desc or "dialogue polish" in task_desc:
                task_type = LinguisticTask.REFINE_DIALOGUE.value
            elif "continuity" in task_desc or "check continuity" in task_desc:
                task_type = LinguisticTask.CHECK_CONTINUITY.value
                
        # If message type is "agent_task", use that as task type if no other type is set
        if not task_type and message.message_type == "agent_task":
            task_type = LinguisticTask.AGENT_TASK.value
            
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
            if task_type == LinguisticTask.POLISH_CHAPTER.value:
                self._polish_chapter(message)
            elif task_type == LinguisticTask.ANALYZE_TEXT.value:
                self._analyze_language(message)
            elif task_type == LinguisticTask.IMPROVE_STYLE.value:
                self._check_style_consistency(message)
            elif task_type == LinguisticTask.ENHANCE_READABILITY.value:
                self._enhance_readability(message)
            elif task_type == LinguisticTask.REFINE_DIALOGUE.value:
                self._polish_dialogue(message)
            elif task_type == LinguisticTask.CHECK_CONTINUITY.value:
                self._check_continuity(message)
            elif task_type == LinguisticTask.AGENT_TASK.value:
                # Handle agent-to-agent task - determine what to do based on task_description
                task_desc = message.content.get("task_description", "").lower()
                if "polish" in task_desc and "chapter" in task_desc:
                    self._polish_chapter(message)
                elif "dialogue" in task_desc:
                    self._polish_dialogue(message)
                else:
                    # Default to polish chapter if unclear
                    self._polish_chapter(message)
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
        
        # Log the feedback
        feedback_text = message.content.get("feedback", "")
        rating = message.metadata.get("rating", 0)
        logger.info(f"Received feedback for task {parent_id}. Rating: {rating}/5")
        logger.info(f"Feedback: {feedback_text}")
    
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
    
    def _polish_chapter(self, message: Message) -> None:
        """
        Polish a chapter's language, grammar, and style.
        
        Args:
            message: The task message
        """
        logger.info("Polishing chapter")
        
        try:
            # Extract content from message
            book_id = message.content.get("book_id")
            chapter_number = message.content.get("chapter_number")
            focus_areas = message.content.get("focus_areas", "")
            
            if not book_id or chapter_number is None:
                raise ValueError("Missing book_id or chapter_number in task content")
                
            # Get book metadata
            storage = BookStorage(book_id)
            metadata_json = storage.load_metadata()
            
            # Load the chapter content
            component_name = f"chapter_{chapter_number}"
            original_content = storage.load_component(component_name)
            
            if not original_content:
                raise ValueError(f"Chapter {chapter_number} not found")
            
            # Get chapter title from outline if available
            chapter_title = f"Chapter {chapter_number}"
            chapters_json = storage.load_component("chapters")
            if chapters_json:
                chapters = json.loads(chapters_json).get("chapters", [])
                if 0 <= int(chapter_number) - 1 < len(chapters):
                    chapter = chapters[int(chapter_number) - 1]
                    chapter_title = chapter.get("title", chapter_title)
            
            # Construct style guidelines from metadata
            style_guidelines = f"Writing style: {metadata_json.get('style', 'Not specified')}\n"
            style_guidelines += f"Tone: {metadata_json.get('tone', 'Not specified')}\n"
            style_guidelines += f"Genre: {metadata_json.get('genre', 'Fiction')}\n"
            style_guidelines += f"Target audience: {metadata_json.get('target_audience', 'General')}\n"
            
            # If focus_areas is a list, format it
            if isinstance(focus_areas, list):
                focus_areas = "\n".join([f"- {area}" for area in focus_areas])
            elif not focus_areas:
                focus_areas = "- Grammar and punctuation\n- Sentence structure and flow\n- Word choice and clarity\n- Consistency in tense and perspective\n- Paragraph structure and transitions"
            
            # Prepare prompt variables
            prompt_vars = {
                "chapter_number": chapter_number,
                "chapter_title": chapter_title,
                "genre": metadata_json.get("genre", "Fiction"),
                "book_title": metadata_json.get("title", "Untitled"),
                "original_content": original_content,
                "style_guidelines": style_guidelines,
                "focus_areas": focus_areas
            }
            
            # Create prompt
            polish_prompt = CHAPTER_POLISH_PROMPT.format(**prompt_vars)
            
            # Generate polished chapter from Claude
            claude_messages = [
                get_claude_api().user_message(polish_prompt)
            ]
            
            options = CompletionOptions(
                system=LINGUISTIC_SYSTEM_PROMPT,
                temperature=0.3,  # Lower temperature for more precise editing
                max_tokens=4000
            )
            
            claude_response = get_claude_api().complete_with_retry(claude_messages, options)
            
            # Save the polished chapter with a version number
            import datetime
            version = f"polished_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
            polished_content = claude_response.strip()
            chapter_path = storage.save_component(component_name, polished_content, version)
            
            # Save a comparison for reference
            comparison = f"ORIGINAL VERSION:\n\n{original_content}\n\n{'='*50}\n\nPOLISHED VERSION:\n\n{polished_content}"
            comparison_path = storage.save_component(f"{component_name}_comparison", comparison, version)
            
            # Return the result
            send_result(
                self.agent_id,
                message.sender,
                {
                    "book_id": book_id,
                    "chapter_number": chapter_number,
                    "chapter_title": chapter_title,
                    "content": polished_content,
                    "word_count": len(polished_content.split()),
                    "path": chapter_path,
                    "comparison_path": comparison_path,
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
                "word_count": len(polished_content.split()),
                "version": version
            }
            
        except Exception as e:
            logger.error(f"Error polishing chapter: {str(e)}")
            send_error(
                self.agent_id,
                message.sender,
                f"Error polishing chapter: {str(e)}",
                message.message_id,
                {"book_id": message.content.get("book_id")}
            )
            self.active_tasks[message.message_id]["status"] = "failed"
            self.active_tasks[message.message_id]["error"] = str(e)
    
    def _analyze_language(self, message: Message) -> None:
        """
        Perform detailed linguistic analysis on text.
        
        Args:
            message: The task message
        """
        logger.info("Analyzing language")
        
        try:
            # Extract content from message
            book_id = message.content.get("book_id")
            text_content = message.content.get("text_content")
            
            # If text_content is not provided directly, try to get it from a chapter
            if not text_content and "chapter_number" in message.content:
                chapter_number = message.content.get("chapter_number")
                storage = BookStorage(book_id)
                component_name = f"chapter_{chapter_number}"
                text_content = storage.load_component(component_name)
            
            if not book_id or not text_content:
                raise ValueError("Missing book_id or text_content in task content")
                
            # Get book metadata
            storage = BookStorage(book_id)
            metadata_json = storage.load_metadata()
            
            # Construct style guidelines from metadata
            style_guidelines = f"Writing style: {metadata_json.get('style', 'Not specified')}\n"
            style_guidelines += f"Tone: {metadata_json.get('tone', 'Not specified')}\n"
            style_guidelines += f"Genre: {metadata_json.get('genre', 'Fiction')}\n"
            style_guidelines += f"Target audience: {metadata_json.get('target_audience', 'General')}\n"
            
            # Prepare prompt variables
            prompt_vars = {
                "genre": metadata_json.get("genre", "Fiction"),
                "book_title": metadata_json.get("title", "Untitled"),
                "text_content": text_content,
                "style_guidelines": style_guidelines
            }
            
            # Create prompt
            analysis_prompt = LANGUAGE_ANALYSIS_PROMPT.format(**prompt_vars)
            
            # Generate analysis from Claude
            claude_messages = [
                get_claude_api().user_message(analysis_prompt)
            ]
            
            options = CompletionOptions(
                system=LINGUISTIC_SYSTEM_PROMPT,
                temperature=0.2,  # Lower temperature for analytical tasks
                max_tokens=3000
            )
            
            claude_response = get_claude_api().complete_with_retry(claude_messages, options)
            
            # Save the analysis
            analysis_content = claude_response.strip()
            
            # Save the analysis as a component
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            analysis_path = storage.save_component("language_analysis", analysis_content, timestamp)
            
            # Try to parse the analysis into structured form if possible
            try:
                # Look for key sections that might be in the analysis
                import re
                
                # Extract grammar assessment
                grammar_match = re.search(r'Grammar and [Pp]unctuation[:\s]+(.*?)(?=\d+\.|\Z)', analysis_content, re.DOTALL)
                grammar_assessment = grammar_match.group(1).strip() if grammar_match else ""
                
                # Extract sentence structure assessment
                sentence_match = re.search(r'Sentence [Ss]tructure[:\s]+(.*?)(?=\d+\.|\Z)', analysis_content, re.DOTALL)
                sentence_assessment = sentence_match.group(1).strip() if sentence_match else ""
                
                # Extract word choice assessment
                word_match = re.search(r'Word [Cc]hoice[:\s]+(.*?)(?=\d+\.|\Z)', analysis_content, re.DOTALL)
                word_assessment = word_match.group(1).strip() if word_match else ""
                
                # Extract strengths
                strengths_match = re.search(r'[Ss]trengths[:\s]+(.*?)(?=\d+\.|\Z|[Aa]reas for [Ii]mprovement)', analysis_content, re.DOTALL)
                strengths = strengths_match.group(1).strip() if strengths_match else ""
                
                # Extract improvements
                improvements_match = re.search(r'[Aa]reas for [Ii]mprovement[:\s]+(.*?)(?=\d+\.|\Z)', analysis_content, re.DOTALL)
                improvements = improvements_match.group(1).strip() if improvements_match else ""
                
                # Create structured analysis
                structured_analysis = {
                    "grammar_assessment": grammar_assessment,
                    "sentence_structure": sentence_assessment,
                    "word_choice": word_assessment,
                    "strengths": strengths,
                    "areas_for_improvement": improvements,
                    "full_analysis": analysis_content
                }
            except Exception:
                # If parsing fails, just use the full text
                structured_analysis = {
                    "full_analysis": analysis_content
                }
            
            # Return the result
            send_result(
                self.agent_id,
                message.sender,
                {
                    "book_id": book_id,
                    "analysis": structured_analysis,
                    "path": analysis_path,
                    "timestamp": timestamp
                },
                message.message_id,
                {"book_id": book_id}
            )
            
            # Update task status
            self.active_tasks[message.message_id]["status"] = "completed"
            self.active_tasks[message.message_id]["completed_at"] = time.time()
            self.active_tasks[message.message_id]["result"] = {
                "analysis": structured_analysis,
                "timestamp": timestamp
            }
            
        except Exception as e:
            logger.error(f"Error analyzing language: {str(e)}")
            send_error(
                self.agent_id,
                message.sender,
                f"Error analyzing language: {str(e)}",
                message.message_id,
                {"book_id": message.content.get("book_id")}
            )
            self.active_tasks[message.message_id]["status"] = "failed"
            self.active_tasks[message.message_id]["error"] = str(e)
    
    def _check_style_consistency(self, message: Message) -> None:
        """
        Check for style consistency across text.
        
        Args:
            message: The task message
        """
        logger.info("Checking style consistency")
        
        try:
            # Extract content from message
            book_id = message.content.get("book_id")
            text_content = message.content.get("text_content")
            reference_text = message.content.get("reference_text", "")
            
            # If text_content is not provided directly, try to get it from a chapter
            if not text_content and "chapter_number" in message.content:
                chapter_number = message.content.get("chapter_number")
                storage = BookStorage(book_id)
                component_name = f"chapter_{chapter_number}"
                text_content = storage.load_component(component_name)
            
            if not book_id or not text_content:
                raise ValueError("Missing book_id or text_content in task content")
                
            # Get book metadata
            storage = BookStorage(book_id)
            metadata_json = storage.load_metadata()
            
            # If reference_text not provided, try to get the first chapter as reference
            if not reference_text:
                # Try to get chapter 1 as a reference
                reference_text = storage.load_component("chapter_1") or ""
                
                # If still empty and checking a chapter, try to get previous chapter
                if not reference_text and "chapter_number" in message.content:
                    chapter_number = int(message.content.get("chapter_number"))
                    if chapter_number > 1:
                        reference_text = storage.load_component(f"chapter_{chapter_number-1}") or ""
            
            # Construct style guidelines from metadata
            style_guidelines = f"Writing style: {metadata_json.get('style', 'Not specified')}\n"
            style_guidelines += f"Tone: {metadata_json.get('tone', 'Not specified')}\n"
            style_guidelines += f"Genre: {metadata_json.get('genre', 'Fiction')}\n"
            style_guidelines += f"Target audience: {metadata_json.get('target_audience', 'General')}\n"
            
            # Prepare prompt variables
            prompt_vars = {
                "genre": metadata_json.get("genre", "Fiction"),
                "book_title": metadata_json.get("title", "Untitled"),
                "text_content": text_content,
                "style_guidelines": style_guidelines,
                "reference_text": reference_text if reference_text else "No reference text available."
            }
            
            # Create prompt
            style_prompt = STYLE_CONSISTENCY_PROMPT.format(**prompt_vars)
            
            # Generate analysis from Claude
            claude_messages = [
                get_claude_api().user_message(style_prompt)
            ]
            
            options = CompletionOptions(
                system=LINGUISTIC_SYSTEM_PROMPT,
                temperature=0.2,  # Lower temperature for analytical tasks
                max_tokens=3000
            )
            
            claude_response = get_claude_api().complete_with_retry(claude_messages, options)
            
            # Save the analysis
            style_analysis = claude_response.strip()
            
            # Save the analysis as a component
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            analysis_path = storage.save_component("style_consistency", style_analysis, timestamp)
            
            # Try to parse the analysis into structured form if possible
            try:
                # Look for key sections that might be in the analysis
                import re
                
                # Extract overall consistency assessment
                overall_match = re.search(r'Overall [Cc]onsistency[:\s]+(.*?)(?=\d+\.|\Z)', style_analysis, re.DOTALL)
                overall_assessment = overall_match.group(1).strip() if overall_match else ""
                
                # Extract strengths
                strengths_match = re.search(r'[Ss]trengths[:\s]+(.*?)(?=\d+\.|\Z|[Aa]reas for [Ii]mprovement)', style_analysis, re.DOTALL)
                strengths = strengths_match.group(1).strip() if strengths_match else ""
                
                # Extract improvements
                improvements_match = re.search(r'[Aa]reas for [Ii]mprovement[:\s]+(.*?)(?=\d+\.|\Z)', style_analysis, re.DOTALL)
                improvements = improvements_match.group(1).strip() if improvements_match else ""
                
                # Create structured analysis
                structured_analysis = {
                    "overall_assessment": overall_assessment,
                    "strengths": strengths,
                    "areas_for_improvement": improvements,
                    "full_analysis": style_analysis
                }
            except Exception:
                # If parsing fails, just use the full text
                structured_analysis = {
                    "full_analysis": style_analysis
                }
            
            # Return the result
            send_result(
                self.agent_id,
                message.sender,
                {
                    "book_id": book_id,
                    "style_analysis": structured_analysis,
                    "path": analysis_path,
                    "timestamp": timestamp
                },
                message.message_id,
                {"book_id": book_id}
            )
            
            # Update task status
            self.active_tasks[message.message_id]["status"] = "completed"
            self.active_tasks[message.message_id]["completed_at"] = time.time()
            self.active_tasks[message.message_id]["result"] = {
                "style_analysis": structured_analysis,
                "timestamp": timestamp
            }
            
        except Exception as e:
            logger.error(f"Error checking style consistency: {str(e)}")
            send_error(
                self.agent_id,
                message.sender,
                f"Error checking style consistency: {str(e)}",
                message.message_id,
                {"book_id": message.content.get("book_id")}
            )
            self.active_tasks[message.message_id]["status"] = "failed"
            self.active_tasks[message.message_id]["error"] = str(e)
    
    def _enhance_readability(self, message: Message) -> None:
        """
        Enhance the readability of text.
        
        Args:
            message: The task message
        """
        logger.info("Enhancing readability")
        
        try:
            # Extract content from message
            book_id = message.content.get("book_id")
            original_content = message.content.get("original_content")
            readability_issues = message.content.get("readability_issues", "")
            
            # If original_content is not provided directly, try to get it from a chapter
            if not original_content and "chapter_number" in message.content:
                chapter_number = message.content.get("chapter_number")
                storage = BookStorage(book_id)
                component_name = f"chapter_{chapter_number}"
                original_content = storage.load_component(component_name)
            
            if not book_id or not original_content:
                raise ValueError("Missing book_id or original_content in task content")
                
            # Get book metadata
            storage = BookStorage(book_id)
            metadata_json = storage.load_metadata()
            
            # Target audience
            target_audience = message.content.get("target_audience", metadata_json.get("target_audience", "General"))
            
            # If readability_issues is a list, format it
            if isinstance(readability_issues, list):
                readability_issues = "\n".join([f"- {issue}" for issue in readability_issues])
            elif not readability_issues:
                readability_issues = "- Sentence complexity\n- Paragraph length\n- Clarity of expression\n- Flow and transitions\n- Technical jargon usage"
            
            # Construct style guidelines from metadata
            style_guidelines = f"Writing style: {metadata_json.get('style', 'Not specified')}\n"
            style_guidelines += f"Tone: {metadata_json.get('tone', 'Not specified')}\n"
            style_guidelines += f"Genre: {metadata_json.get('genre', 'Fiction')}\n"
            
            # Prepare prompt variables
            prompt_vars = {
                "genre": metadata_json.get("genre", "Fiction"),
                "book_title": metadata_json.get("title", "Untitled"),
                "original_content": original_content,
                "target_audience": target_audience,
                "readability_issues": readability_issues,
                "style_guidelines": style_guidelines
            }
            
            # Create prompt
            readability_prompt = READABILITY_ENHANCEMENT_PROMPT.format(**prompt_vars)
            
            # Generate enhanced text from Claude
            claude_messages = [
                get_claude_api().user_message(readability_prompt)
            ]
            
            options = CompletionOptions(
                system=LINGUISTIC_SYSTEM_PROMPT,
                temperature=0.4,
                max_tokens=4000
            )
            
            claude_response = get_claude_api().complete_with_retry(claude_messages, options)
            
            # Save the enhanced text
            enhanced_content = claude_response.strip()
            
            # If working with a chapter, save it with a version
            if "chapter_number" in message.content:
                chapter_number = message.content.get("chapter_number")
                component_name = f"chapter_{chapter_number}"
                
                # Save with a version number
                import datetime
                version = f"readable_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
                content_path = storage.save_component(component_name, enhanced_content, version)
                
                # Save a comparison for reference
                comparison = f"ORIGINAL VERSION:\n\n{original_content}\n\n{'='*50}\n\nENHANCED VERSION:\n\n{enhanced_content}"
                comparison_path = storage.save_component(f"{component_name}_readability_comparison", comparison, version)
            else:
                # Save as a separate component if not a chapter
                import datetime
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                content_path = storage.save_component("enhanced_readability", enhanced_content, timestamp)
                comparison_path = None
            
            # Return the result
            result = {
                "book_id": book_id,
                "content": enhanced_content,
                "word_count": len(enhanced_content.split()),
                "path": content_path
            }
            
            if "chapter_number" in message.content:
                result["chapter_number"] = message.content.get("chapter_number")
                result["version"] = version
                if comparison_path:
                    result["comparison_path"] = comparison_path
            
            send_result(
                self.agent_id,
                message.sender,
                result,
                message.message_id,
                {"book_id": book_id}
            )
            
            # Update task status
            self.active_tasks[message.message_id]["status"] = "completed"
            self.active_tasks[message.message_id]["completed_at"] = time.time()
            self.active_tasks[message.message_id]["result"] = {
                "word_count": len(enhanced_content.split())
            }
            
        except Exception as e:
            logger.error(f"Error enhancing readability: {str(e)}")
            send_error(
                self.agent_id,
                message.sender,
                f"Error enhancing readability: {str(e)}",
                message.message_id,
                {"book_id": message.content.get("book_id")}
            )
            self.active_tasks[message.message_id]["status"] = "failed"
            self.active_tasks[message.message_id]["error"] = str(e)
    
    def _polish_dialogue(self, message: Message) -> None:
        """
        Polish dialogue in text.
        
        Args:
            message: The task message
        """
        logger.info("Polishing dialogue")
        
        try:
            # Extract content from message
            book_id = message.content.get("book_id")
            original_content = message.content.get("original_content")
            character_voices = message.content.get("character_voices", "")
            dialogue_focus = message.content.get("dialogue_focus", "")
            
            # If original_content is not provided directly, try to get it from a chapter
            if not original_content and "chapter_number" in message.content:
                chapter_number = message.content.get("chapter_number")
                storage = BookStorage(book_id)
                component_name = f"chapter_{chapter_number}"
                original_content = storage.load_component(component_name)
            
            if not book_id or not original_content:
                raise ValueError("Missing book_id or original_content in task content")
                
            # Get book metadata
            storage = BookStorage(book_id)
            metadata_json = storage.load_metadata()
            
            # If character_voices not provided, try to get them from character information
            if not character_voices:
                character_json = storage.load_component("characters")
                if character_json:
                    characters = json.loads(character_json).get("characters", [])
                    character_voices = ""
                    for char in characters:
                        character_voices += f"- {char.get('name', 'Unnamed')}: "
                        if 'personality' in char:
                            character_voices += f"{char.get('personality')} "
                        if 'background' in char:
                            character_voices += f"Background: {char.get('background')} "
                        character_voices += "\n"
            
            # If dialogue_focus is a list, format it
            if isinstance(dialogue_focus, list):
                dialogue_focus = "\n".join([f"- {focus}" for focus in dialogue_focus])
            elif not dialogue_focus:
                dialogue_focus = "- Natural speech patterns\n- Character-specific voices\n- Emotional authenticity\n- Dialogue flow and rhythm\n- Proper dialogue formatting"
            
            # Construct style guidelines from metadata
            style_guidelines = f"Writing style: {metadata_json.get('style', 'Not specified')}\n"
            style_guidelines += f"Tone: {metadata_json.get('tone', 'Not specified')}\n"
            style_guidelines += f"Genre: {metadata_json.get('genre', 'Fiction')}\n"
            
            # Prepare prompt variables
            prompt_vars = {
                "genre": metadata_json.get("genre", "Fiction"),
                "book_title": metadata_json.get("title", "Untitled"),
                "original_content": original_content,
                "character_voices": character_voices,
                "dialogue_focus": dialogue_focus,
                "style_guidelines": style_guidelines
            }
            
            # Create prompt
            dialogue_prompt = DIALOGUE_POLISH_PROMPT.format(**prompt_vars)
            
            # Generate polished dialogue from Claude
            claude_messages = [
                get_claude_api().user_message(dialogue_prompt)
            ]
            
            options = CompletionOptions(
                system=LINGUISTIC_SYSTEM_PROMPT,
                temperature=0.5,
                max_tokens=4000
            )
            
            claude_response = get_claude_api().complete_with_retry(claude_messages, options)
            
            # Save the polished dialogue
            polished_content = claude_response.strip()
            
            # If working with a chapter, save it with a version
            if "chapter_number" in message.content:
                chapter_number = message.content.get("chapter_number")
                component_name = f"chapter_{chapter_number}"
                
                # Save with a version number
                import datetime
                version = f"dialogue_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
                content_path = storage.save_component(component_name, polished_content, version)
                
                # Save a comparison for reference
                comparison = f"ORIGINAL VERSION:\n\n{original_content}\n\n{'='*50}\n\nPOLISHED DIALOGUE VERSION:\n\n{polished_content}"
                comparison_path = storage.save_component(f"{component_name}_dialogue_comparison", comparison, version)
            else:
                # Save as a separate component if not a chapter
                import datetime
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                content_path = storage.save_component("polished_dialogue", polished_content, timestamp)
                comparison_path = None
            
            # Return the result
            result = {
                "book_id": book_id,
                "content": polished_content,
                "word_count": len(polished_content.split()),
                "path": content_path
            }
            
            if "chapter_number" in message.content:
                result["chapter_number"] = message.content.get("chapter_number")
                result["version"] = version
                if comparison_path:
                    result["comparison_path"] = comparison_path
            
            send_result(
                self.agent_id,
                message.sender,
                result,
                message.message_id,
                {"book_id": book_id}
            )
            
            # Update task status
            self.active_tasks[message.message_id]["status"] = "completed"
            self.active_tasks[message.message_id]["completed_at"] = time.time()
            self.active_tasks[message.message_id]["result"] = {
                "word_count": len(polished_content.split())
            }
            
        except Exception as e:
            logger.error(f"Error polishing dialogue: {str(e)}")
            send_error(
                self.agent_id,
                message.sender,
                f"Error polishing dialogue: {str(e)}",
                message.message_id,
                {"book_id": message.content.get("book_id")}
            )
            self.active_tasks[message.message_id]["status"] = "failed"
            self.active_tasks[message.message_id]["error"] = str(e)
    
    def _check_continuity(self, message: Message) -> None:
        """
        Check for linguistic continuity between text sections.
        
        Args:
            message: The task message
        """
        logger.info("Checking continuity")
        
        try:
            # Extract content from message
            book_id = message.content.get("book_id")
            current_text = message.content.get("current_text")
            previous_text = message.content.get("previous_text")
            
            # If texts are not provided directly, try to get them from chapters
            if not current_text and "chapter_number" in message.content:
                chapter_number = int(message.content.get("chapter_number"))
                storage = BookStorage(book_id)
                current_text = storage.load_component(f"chapter_{chapter_number}")
                
                # Get previous chapter if available
                if chapter_number > 1 and not previous_text:
                    previous_text = storage.load_component(f"chapter_{chapter_number-1}")
            
            if not book_id or not current_text:
                raise ValueError("Missing book_id or current_text in task content")
                
            if not previous_text:
                previous_text = "No previous text available for continuity checking."
            
            # Get book metadata
            storage = BookStorage(book_id)
            metadata_json = storage.load_metadata()
            
            # Construct style guidelines from metadata
            style_guidelines = f"Writing style: {metadata_json.get('style', 'Not specified')}\n"
            style_guidelines += f"Tone: {metadata_json.get('tone', 'Not specified')}\n"
            style_guidelines += f"Genre: {metadata_json.get('genre', 'Fiction')}\n"
            
            # Prepare prompt variables
            prompt_vars = {
                "genre": metadata_json.get("genre", "Fiction"),
                "book_title": metadata_json.get("title", "Untitled"),
                "current_text": current_text,
                "previous_text": previous_text,
                "style_guidelines": style_guidelines
            }
            
            # Create prompt
            continuity_prompt = CONTINUITY_CHECK_PROMPT.format(**prompt_vars)
            
            # Generate continuity analysis from Claude
            claude_messages = [
                get_claude_api().user_message(continuity_prompt)
            ]
            
            options = CompletionOptions(
                system=LINGUISTIC_SYSTEM_PROMPT,
                temperature=0.2,  # Lower temperature for analytical tasks
                max_tokens=3000
            )
            
            claude_response = get_claude_api().complete_with_retry(claude_messages, options)
            
            # Save the analysis
            continuity_analysis = claude_response.strip()
            
            # Save the analysis as a component
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Create component name based on what we're analyzing
            if "chapter_number" in message.content:
                chapter_number = message.content.get("chapter_number")
                component_name = f"chapter_{chapter_number}_continuity"
            else:
                component_name = "continuity_analysis"
                
            analysis_path = storage.save_component(component_name, continuity_analysis, timestamp)
            
            # Try to parse the analysis into structured form if possible
            try:
                # Look for key sections that might be in the analysis
                import re
                
                # Extract issues found
                issues_match = re.search(r'[Ii]ssues [Ff]ound[:\s]+(.*?)(?=\d+\.|\Z|[Rr]ecommendations)', continuity_analysis, re.DOTALL)
                issues = issues_match.group(1).strip() if issues_match else ""
                
                # Extract recommendations
                recommendations_match = re.search(r'[Rr]ecommendations[:\s]+(.*?)(?=\d+\.|\Z)', continuity_analysis, re.DOTALL)
                recommendations = recommendations_match.group(1).strip() if recommendations_match else ""
                
                # Create structured analysis
                structured_analysis = {
                    "issues_found": issues,
                    "recommendations": recommendations,
                    "full_analysis": continuity_analysis
                }
            except Exception:
                # If parsing fails, just use the full text
                structured_analysis = {
                    "full_analysis": continuity_analysis
                }
            
            # Return the result
            result = {
                "book_id": book_id,
                "continuity_analysis": structured_analysis,
                "path": analysis_path,
                "timestamp": timestamp
            }
            
            if "chapter_number" in message.content:
                result["chapter_number"] = message.content.get("chapter_number")
            
            send_result(
                self.agent_id,
                message.sender,
                result,
                message.message_id,
                {"book_id": book_id}
            )
            
            # Update task status
            self.active_tasks[message.message_id]["status"] = "completed"
            self.active_tasks[message.message_id]["completed_at"] = time.time()
            self.active_tasks[message.message_id]["result"] = {
                "continuity_analysis": structured_analysis,
                "timestamp": timestamp
            }
            
        except Exception as e:
            logger.error(f"Error checking continuity: {str(e)}")
            send_error(
                self.agent_id,
                message.sender,
                f"Error checking continuity: {str(e)}",
                message.message_id,
                {"book_id": message.content.get("book_id")}
            )
            self.active_tasks[message.message_id]["status"] = "failed"
            self.active_tasks[message.message_id]["error"] = str(e)
