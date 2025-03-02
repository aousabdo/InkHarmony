"""
Visual Design Coordinator Agent for InkHarmony.
Creates cover art concepts and manages image generation.
"""
import logging
import json
import time
import os
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
from models.stability import get_stability_api, stability_api, ImageGenerationOptions
from templates.visual_templates import (
    VISUAL_SYSTEM_PROMPT,
    COVER_CONCEPT_PROMPT,
    IMAGE_PROMPT_TEMPLATE,
    COVER_EVALUATION_PROMPT,
    COVER_REFINEMENT_PROMPT,
    TYPOGRAPHY_RECOMMENDATIONS_PROMPT,
    ILLUSTRATION_STYLE_GUIDE_PROMPT
)

# Set up logging
logger = logging.getLogger(__name__)

class VisualTask(Enum):
    """Types of tasks the Visual Design Coordinator can perform."""
    CREATE_COVER_CONCEPT = "create_cover_concept"
    GENERATE_IMAGE_PROMPTS = "generate_image_prompts"
    GENERATE_COVER_ART = "generate_cover_art"
    EVALUATE_COVER_ART = "evaluate_cover_art"
    REFINE_COVER_ART = "refine_cover_art"
    RECOMMEND_TYPOGRAPHY = "recommend_typography"
    CREATE_STYLE_GUIDE = "create_style_guide"
    AGENT_TASK = "agent_task"  # Add this for internal agent communication


class VisualDesignCoordinatorAgent:
    """
    Visual Design Coordinator Agent that creates cover art.
    """
    
    def __init__(self, agent_id: str = "visual"):
        """
        Initialize the Visual Design Coordinator Agent.
        
        Args:
            agent_id: Identifier for this agent instance
        """
        self.agent_id = agent_id
        self.active_tasks: Dict[str, Dict[str, Any]] = {}
        
        # Register with message queue
        message_queue.register_agent(self.agent_id)
        
        logger.info(f"Visual Design Coordinator Agent initialized with ID: {self.agent_id}")
    
    def run(self) -> None:
        """
        Main agent loop. Processes messages and handles tasks.
        """
        logger.info(f"Visual Design Coordinator Agent {self.agent_id} started")
        
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
            if "cover concept" in task_desc:
                task_type = VisualTask.CREATE_COVER_CONCEPT.value
            elif "image prompt" in task_desc:
                task_type = VisualTask.GENERATE_IMAGE_PROMPTS.value
            elif "cover art" in task_desc and "generate" in task_desc:
                task_type = VisualTask.GENERATE_COVER_ART.value
            elif "evaluate" in task_desc and "cover" in task_desc:
                task_type = VisualTask.EVALUATE_COVER_ART.value
            elif "refine" in task_desc and "cover" in task_desc:
                task_type = VisualTask.REFINE_COVER_ART.value
            elif "typography" in task_desc:
                task_type = VisualTask.RECOMMEND_TYPOGRAPHY.value
            elif "style guide" in task_desc:
                task_type = VisualTask.CREATE_STYLE_GUIDE.value
                
        # If message type is "agent_task", use that as task type if no other type is set
        if not task_type and message.message_type == "agent_task":
            task_type = VisualTask.AGENT_TASK.value
            
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
            if task_type == VisualTask.CREATE_COVER_CONCEPT.value:
                self._create_cover_concept(message)
            elif task_type == VisualTask.GENERATE_IMAGE_PROMPTS.value:
                self._generate_image_prompts(message)
            elif task_type == VisualTask.GENERATE_COVER_ART.value:
                self._generate_cover_art(message)
            elif task_type == VisualTask.EVALUATE_COVER_ART.value:
                self._evaluate_cover_art(message)
            elif task_type == VisualTask.REFINE_COVER_ART.value:
                self._refine_cover_art(message)
            elif task_type == VisualTask.RECOMMEND_TYPOGRAPHY.value:
                self._recommend_typography(message)
            elif task_type == VisualTask.CREATE_STYLE_GUIDE.value:
                self._create_style_guide(message)
            elif task_type == VisualTask.AGENT_TASK.value:
                # Handle agent-to-agent task - determine what to do based on task_description
                task_desc = message.content.get("task_description", "").lower()
                if "cover concept" in task_desc:
                    self._create_cover_concept(message)
                elif "refine" in task_desc and "cover" in task_desc:
                    self._refine_cover_art(message)
                else:
                    # Default to refine cover art if unclear
                    self._refine_cover_art(message)
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
        
        if rating < 3 or "refine" in feedback_text.lower() or "improve" in feedback_text.lower():
            # Create a refinement task
            logger.info(f"Creating refinement task based on feedback for: {parent_id}")
            
            # Get the original task and result
            original_task = self.active_tasks[parent_id]["message"]
            original_book_id = original_task.content.get("book_id")
            
            if not original_book_id:
                logger.warning("Cannot create refinement task: missing book_id")
                return
                
            # Determine what type of refinement is needed
            if "cover concept" in feedback_text.lower() or VisualTask.CREATE_COVER_CONCEPT.value in original_task.metadata.get("task_type", ""):
                self._refine_cover_concept(original_book_id, parent_id, feedback_text)
            elif "cover art" in feedback_text.lower() or VisualTask.GENERATE_COVER_ART.value in original_task.metadata.get("task_type", ""):
                self._create_refinement_from_feedback(original_book_id, parent_id, feedback_text)
    
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
    
    def _create_cover_concept(self, message: Message) -> None:
        """
        Create a cover art concept.
        
        Args:
            message: The task message
        """
        logger.info("Creating cover concept")
        
        try:
            # Extract content from message
            book_id = message.content.get("book_id")
            
            if not book_id:
                raise ValueError("Missing book_id in task content")
                
            # Get book metadata and outline
            storage = BookStorage(book_id)
            metadata_json = storage.load_metadata()
            
            outline_json = storage.load_component("outline")
            if not outline_json:
                raise ValueError("No outline found. Please create an outline first.")
                
            outline = json.loads(outline_json)
            
            # Extract key themes
            themes = outline.get("themes", [])
            if isinstance(themes, list):
                themes_text = "\n".join([f"- {theme}" for theme in themes])
            else:
                themes_text = str(themes)
            
            # Extract any design preferences from the message
            design_preferences = message.content.get("design_preferences", "")
            if not design_preferences:
                design_preferences = "No specific design preferences provided. Use genre conventions and create an appealing, marketable cover."
            
            # Prepare prompt variables
            prompt_vars = {
                "genre": metadata_json.get("genre", "Fiction"),
                "book_title": metadata_json.get("title", "Untitled"),
                "book_synopsis": outline.get("synopsis", "No synopsis available."),
                "key_themes": themes_text,
                "target_audience": metadata_json.get("target_audience", "General readers"),
                "design_preferences": design_preferences
            }
            
            # Create prompt
            cover_prompt = COVER_CONCEPT_PROMPT.format(**prompt_vars)
            
            # Generate cover concept from Claude
            claude_messages = [
                get_claude_api().user_message(cover_prompt)
            ]
            
            options = CompletionOptions(
                system=VISUAL_SYSTEM_PROMPT,
                temperature=0.7,
                max_tokens=2500
            )
            
            claude_response = get_claude_api().complete_with_retry(claude_messages, options)
            
            # Save the cover concept
            concept_content = claude_response.strip()
            concept_path = storage.save_component("cover_concept", concept_content)
            
            # Try to extract structured info from the concept
            try:
                import re
                
                # Extract high-level concept
                concept_match = re.search(r'(?:concept|description):(.*?)(?:\d+\.|\n\n)', concept_content, re.DOTALL | re.IGNORECASE)
                concept_description = concept_match.group(1).strip() if concept_match else ""
                
                # Extract key visual elements
                elements_match = re.search(r'(?:key visual elements|elements to include):(.*?)(?:\d+\.|\n\n)', concept_content, re.DOTALL | re.IGNORECASE)
                visual_elements = elements_match.group(1).strip() if elements_match else ""
                
                # Extract color palette
                color_match = re.search(r'(?:color palette|recommended colors):(.*?)(?:\d+\.|\n\n)', concept_content, re.DOTALL | re.IGNORECASE)
                color_palette = color_match.group(1).strip() if color_match else ""
                
                # Extract style recommendations
                style_match = re.search(r'(?:style recommendations|style|visual style):(.*?)(?:\d+\.|\n\n)', concept_content, re.DOTALL | re.IGNORECASE)
                style = style_match.group(1).strip() if style_match else ""
                
                # Create structured concept
                structured_concept = {
                    "concept_description": concept_description,
                    "visual_elements": visual_elements,
                    "color_palette": color_palette,
                    "style": style,
                    "full_concept": concept_content
                }
            except Exception as e:
                logger.warning(f"Error parsing cover concept: {str(e)}")
                structured_concept = {
                    "full_concept": concept_content
                }
            
            # Return the result
            send_result(
                self.agent_id,
                message.sender,
                {
                    "book_id": book_id,
                    "cover_concept": structured_concept,
                    "path": concept_path
                },
                message.message_id,
                {"book_id": book_id}
            )
            
            # Update task status
            self.active_tasks[message.message_id]["status"] = "completed"
            self.active_tasks[message.message_id]["completed_at"] = time.time()
            self.active_tasks[message.message_id]["result"] = structured_concept
            
        except Exception as e:
            logger.error(f"Error creating cover concept: {str(e)}")
            send_error(
                self.agent_id,
                message.sender,
                f"Error creating cover concept: {str(e)}",
                message.message_id,
                {"book_id": message.content.get("book_id")}
            )
            self.active_tasks[message.message_id]["status"] = "failed"
            self.active_tasks[message.message_id]["error"] = str(e)
    
    def _generate_image_prompts(self, message: Message) -> None:
        """
        Generate image prompts for cover art.
        
        Args:
            message: The task message
        """
        logger.info("Generating image prompts")
        
        try:
            # Extract content from message
            book_id = message.content.get("book_id")
            cover_concept = message.content.get("cover_concept")
            generation_system = message.content.get("generation_system", "Stability AI")
            
            if not book_id:
                raise ValueError("Missing book_id in task content")
                
            # If cover concept is not provided, try to load it
            if not cover_concept:
                storage = BookStorage(book_id)
                concept_text = storage.load_component("cover_concept")
                if not concept_text:
                    raise ValueError("No cover concept found. Please create a cover concept first.")
                cover_concept = concept_text
            
            # Get book metadata
            storage = BookStorage(book_id)
            metadata_json = storage.load_metadata()
            
            # Extract key visual elements and style preference
            key_elements = message.content.get("key_elements", "")
            style_preference = message.content.get("style_preference", "")
            
            if not key_elements or not style_preference:
                # Try to extract from cover concept
                try:
                    import re
                    
                    if not key_elements:
                        # Extract key visual elements
                        elements_match = re.search(r'(?:key visual elements|elements to include):(.*?)(?:\d+\.|\n\n)', cover_concept, re.DOTALL | re.IGNORECASE)
                        key_elements = elements_match.group(1).strip() if elements_match else "No specific elements provided."
                    
                    if not style_preference:
                        # Extract style recommendations
                        style_match = re.search(r'(?:style recommendations|style|visual style):(.*?)(?:\d+\.|\n\n)', cover_concept, re.DOTALL | re.IGNORECASE)
                        style_preference = style_match.group(1).strip() if style_match else "No specific style provided."
                except Exception:
                    if not key_elements:
                        key_elements = "No specific elements provided."
                    if not style_preference:
                        style_preference = "No specific style provided."
            
            # Prepare prompt variables
            prompt_vars = {
                "genre": metadata_json.get("genre", "Fiction"),
                "book_title": metadata_json.get("title", "Untitled"),
                "cover_concept": cover_concept,
                "key_elements": key_elements,
                "style_preference": style_preference,
                "generation_system": generation_system
            }
            
            # Create prompt
            prompt_template = IMAGE_PROMPT_TEMPLATE.format(**prompt_vars)
            
            # Generate image prompts from Claude
            claude_messages = [
                get_claude_api().user_message(prompt_template)
            ]
            
            options = CompletionOptions(
                system=VISUAL_SYSTEM_PROMPT,
                temperature=0.7,
                max_tokens=2000
            )
            
            claude_response = get_claude_api().complete_with_retry(claude_messages, options)
            
            # Save the image prompts
            prompts_content = claude_response.strip()
            prompts_path = storage.save_component("image_prompts", prompts_content)
            
            # Parse the prompts
            import re
            prompt_pattern = r'Prompt (\d+):(.*?)(?:Prompt \d+:|$)'
            prompts = re.findall(prompt_pattern, prompts_content, re.DOTALL | re.IGNORECASE) or []
            
            if not prompts:
                # Try another format
                prompt_pattern = r'(?:Prompt|Option) (\d+)[\s\-:]+(.*?)(?:(?:Prompt|Option) \d+[\s\-:]+|\Z)'
                prompts = re.findall(prompt_pattern, prompts_content, re.DOTALL | re.IGNORECASE) or []
            
            if not prompts:
                # Final fallback - just split by lines
                prompt_list = [line.strip() for line in prompts_content.split('\n\n') if line.strip()]
                prompts = [(str(i+1), prompt) for i, prompt in enumerate(prompt_list)]
            
            # Format prompts
            formatted_prompts = []
            for prompt_num, prompt_text in prompts:
                formatted_prompts.append({
                    "prompt_number": prompt_num,
                    "prompt_text": prompt_text.strip()
                })
            
            # Return the result
            send_result(
                self.agent_id,
                message.sender,
                {
                    "book_id": book_id,
                    "image_prompts": formatted_prompts,
                    "full_prompts_text": prompts_content,
                    "path": prompts_path,
                    "generation_system": generation_system
                },
                message.message_id,
                {"book_id": book_id}
            )
            
            # Update task status
            self.active_tasks[message.message_id]["status"] = "completed"
            self.active_tasks[message.message_id]["completed_at"] = time.time()
            self.active_tasks[message.message_id]["result"] = {
                "prompt_count": len(formatted_prompts),
                "generation_system": generation_system
            }
            
        except Exception as e:
            logger.error(f"Error generating image prompts: {str(e)}")
            send_error(
                self.agent_id,
                message.sender,
                f"Error generating image prompts: {str(e)}",
                message.message_id,
                {"book_id": message.content.get("book_id")}
            )
            self.active_tasks[message.message_id]["status"] = "failed"
            self.active_tasks[message.message_id]["error"] = str(e)
    
    def _generate_cover_art(self, message: Message) -> None:
        """
        Generate cover art using Stability AI.
        
        Args:
            message: The task message
        """
        logger.info("Generating cover art")
        
        try:
            # Extract content from message
            book_id = message.content.get("book_id")
            prompt = message.content.get("prompt")
            negative_prompt = message.content.get("negative_prompt", "")
            orientation = message.content.get("orientation", "portrait")
            
            if not book_id or not prompt:
                # If prompt is not provided, try to use a saved prompt
                if not prompt and book_id:
                    storage = BookStorage(book_id)
                    prompts_text = storage.load_component("image_prompts")
                    if prompts_text:
                        # Extract the first prompt
                        import re
                        prompt_match = re.search(r'Prompt 1:(.*?)(?:Prompt \d+:|$)', prompts_text, re.DOTALL | re.IGNORECASE)
                        if prompt_match:
                            prompt = prompt_match.group(1).strip()
                    
                    # If still no prompt, try to use cover concept
                    if not prompt:
                        concept_text = storage.load_component("cover_concept")
                        if concept_text:
                            # Create a summary prompt from the concept
                            prompt = f"Book cover for {metadata_json.get('genre', 'fiction')} book titled '{metadata_json.get('title', 'Untitled')}'. Professional quality, highly detailed, trending on artstation."
                
            if not book_id or not prompt:
                raise ValueError("Missing book_id or prompt in task content")
                
            # Get book metadata
            storage = BookStorage(book_id)
            metadata_json = storage.load_metadata()
            
            # Set up image generation options
            if orientation == "portrait":
                width, height = 1152, 1600  # Common book cover ratio (portrait)
            elif orientation == "landscape":
                width, height = 1600, 1152  # Landscape orientation
            else:  # square
                width, height = 1200, 1200  # Square
            
            # Set negative prompt if not provided
            if not negative_prompt:
                negative_prompt = "text, title, author name, words, letters, blurry, low quality, deformed, unfinished, deformed features, disfigured"
            
            # Set up options for stability
            options = ImageGenerationOptions(
                prompt=prompt,
                negative_prompt=negative_prompt,
                width=width,
                height=height,
                steps=40,  # Higher quality
                cfg_scale=8.0,  # More adherence to prompt
                samples=1
            )
            
            # Generate the image
            try:
                image_data = get_stability_api().generate_with_retry(options)
                
                # Save the image to storage
                image_path = storage.save_image("cover", image_data, "png")
                
                # Save the prompt used
                prompt_content = f"Prompt: {prompt}\n\nNegative prompt: {negative_prompt}"
                prompt_path = storage.save_component("used_cover_prompt", prompt_content)
                
                # Update metadata
                metadata_json["cover_generated"] = True
                metadata_json["cover_prompt"] = prompt
                storage.save_metadata(metadata_json)
                
                # Return the result
                send_result(
                    self.agent_id,
                    message.sender,
                    {
                        "book_id": book_id,
                        "cover_generated": True,
                        "prompt_used": prompt,
                        "image_path": image_path,
                        "prompt_path": prompt_path
                    },
                    message.message_id,
                    {"book_id": book_id}
                )
                
                # Update task status
                self.active_tasks[message.message_id]["status"] = "completed"
                self.active_tasks[message.message_id]["completed_at"] = time.time()
                self.active_tasks[message.message_id]["result"] = {
                    "cover_generated": True,
                    "image_path": image_path
                }
            except Exception as e:
                logger.error(f"Error generating image with Stability AI: {str(e)}")
                raise ValueError(f"Error generating image: {str(e)}")
            
        except Exception as e:
            logger.error(f"Error generating cover art: {str(e)}")
            send_error(
                self.agent_id,
                message.sender,
                f"Error generating cover art: {str(e)}",
                message.message_id,
                {"book_id": message.content.get("book_id")}
            )
            self.active_tasks[message.message_id]["status"] = "failed"
            self.active_tasks[message.message_id]["error"] = str(e)
    
    def _evaluate_cover_art(self, message: Message) -> None:
        """
        Evaluate generated cover art.
        
        Args:
            message: The task message
        """
        logger.info("Evaluating cover art")
        
        try:
            # Extract content from message
            book_id = message.content.get("book_id")
            cover_concept = message.content.get("cover_concept")
            key_requirements = message.content.get("key_requirements", "")
            
            if not book_id:
                raise ValueError("Missing book_id in task content")
                
            # Get book metadata and cover concept if not provided
            storage = BookStorage(book_id)
            metadata_json = storage.load_metadata()
            
            if not cover_concept:
                concept_text = storage.load_component("cover_concept")
                if concept_text:
                    cover_concept = concept_text
                else:
                    cover_concept = "No detailed cover concept available."
            
            # If key requirements not provided, extract from metadata or create default
            if not key_requirements:
                key_requirements = f"- Appropriate for {metadata_json.get('genre', 'fiction')} genre\n"
                key_requirements += f"- Appealing to {metadata_json.get('target_audience', 'general readers')}\n"
                key_requirements += "- Professional quality\n"
                key_requirements += "- Visual impact and marketability\n"
                key_requirements += "- Space for title and author name\n"
            
            # Check if cover image exists
            cover_image_data = storage.load_image("cover", "png")
            if not cover_image_data:
                raise ValueError("No cover image found to evaluate.")
            
            # For evaluation, we need to describe the image since Claude can't see it
            # Get the prompt used to generate it
            prompt_text = storage.load_component("used_cover_prompt") or ""
            if not prompt_text:
                prompt_text = "No prompt information available."
            
            # Create an image description that combines the prompt with an explanation
            image_description = f"The cover image was generated based on this prompt:\n\n{prompt_text}\n\n"
            image_description += "The image was generated by an AI image generation system (Stability AI) according to this prompt. "
            image_description += "For the purpose of this evaluation, please assume the generated image follows the prompt closely and evaluate based on how well the described cover would meet the book's needs."
            
            # Prepare prompt variables
            prompt_vars = {
                "genre": metadata_json.get("genre", "Fiction"),
                "book_title": metadata_json.get("title", "Untitled"),
                "cover_concept": cover_concept,
                "key_requirements": key_requirements
            }
            
            # Create evaluation prompt
            evaluation_prompt = COVER_EVALUATION_PROMPT.format(**prompt_vars)
            evaluation_prompt += f"\n\nNote: Since I can't directly see the image, here's the information used to create it:\n\n{image_description}"
            
            # Generate evaluation from Claude
            claude_messages = [
                get_claude_api().user_message(evaluation_prompt)
            ]
            
            options = CompletionOptions(
                system=VISUAL_SYSTEM_PROMPT,
                temperature=0.4,  # Lower for more reliable evaluation
                max_tokens=2000
            )
            
            claude_response = get_claude_api().complete_with_retry(claude_messages, options)
            
            # Save the evaluation
            evaluation_content = claude_response.strip()
            evaluation_path = storage.save_component("cover_evaluation", evaluation_content)
            
            # Try to extract structured evaluation
            try:
                import re
                
                # Extract overall rating or recommendation
                overall_match = re.search(r'(?:Overall|Recommendation):(.*?)(?:$|\n\n)', evaluation_content, re.DOTALL | re.IGNORECASE)
                overall = overall_match.group(1).strip() if overall_match else ""
                
                # Extract strengths
                strengths_match = re.search(r'(?:Strengths|Positives):(.*?)(?:$|\n\n)', evaluation_content, re.DOTALL | re.IGNORECASE)
                strengths = strengths_match.group(1).strip() if strengths_match else ""
                
                # Extract weaknesses or areas for improvement
                weaknesses_match = re.search(r'(?:Weaknesses|Areas for Improvement):(.*?)(?:$|\n\n)', evaluation_content, re.DOTALL | re.IGNORECASE)
                weaknesses = weaknesses_match.group(1).strip() if weaknesses_match else ""
                
                # Create structured evaluation
                structured_evaluation = {
                    "overall_assessment": overall,
                    "strengths": strengths,
                    "areas_for_improvement": weaknesses,
                    "full_evaluation": evaluation_content
                }
            except Exception:
                # If parsing fails, just use the full text
                structured_evaluation = {
                    "full_evaluation": evaluation_content
                }
            
            # Return the result
            send_result(
                self.agent_id,
                message.sender,
                {
                    "book_id": book_id,
                    "cover_evaluation": structured_evaluation,
                    "evaluation_path": evaluation_path
                },
                message.message_id,
                {"book_id": book_id}
            )
            
            # Update task status
            self.active_tasks[message.message_id]["status"] = "completed"
            self.active_tasks[message.message_id]["completed_at"] = time.time()
            self.active_tasks[message.message_id]["result"] = structured_evaluation
            
        except Exception as e:
            logger.error(f"Error evaluating cover art: {str(e)}")
            send_error(
                self.agent_id,
                message.sender,
                f"Error evaluating cover art: {str(e)}",
                message.message_id,
                {"book_id": message.content.get("book_id")}
            )
            self.active_tasks[message.message_id]["status"] = "failed"
            self.active_tasks[message.message_id]["error"] = str(e)
    
    def _refine_cover_art(self, message: Message) -> None:
        """
        Create recommendations for refining cover art.
        
        Args:
            message: The task message
        """
        logger.info("Creating cover refinement recommendations")
        
        try:
            # Extract content from message
            book_id = message.content.get("book_id")
            current_cover = message.content.get("current_cover", "")
            issues_to_address = message.content.get("issues_to_address", "")
            
            if not book_id:
                raise ValueError("Missing book_id in task content")
                
            # Get book metadata
            storage = BookStorage(book_id)
            metadata_json = storage.load_metadata()
            
            # If current_cover description not provided, use the prompt
            if not current_cover:
                prompt_text = storage.load_component("used_cover_prompt")
                if prompt_text:
                    current_cover = f"Cover generated using the following prompt:\n\n{prompt_text}"
                else:
                    current_cover = "No current cover description available."
            
            # If issues not provided and we have an evaluation, extract from there
            if not issues_to_address:
                eval_text = storage.load_component("cover_evaluation")
                if eval_text:
                    import re
                    weaknesses_match = re.search(r'(?:Weaknesses|Areas for Improvement):(.*?)(?:$|\n\n)', eval_text, re.DOTALL | re.IGNORECASE)
                    if weaknesses_match:
                        issues_to_address = weaknesses_match.group(1).strip()
                    else:
                        # Just use the evaluation as context
                        issues_to_address = f"Based on the following evaluation, suggest refinements to improve the cover:\n\n{eval_text}"
            
            # If still no issues, create a default
            if not issues_to_address:
                issues_to_address = "- Enhance visual impact and marketability\n"
                issues_to_address += "- Improve genre clarity\n"
                issues_to_address += "- Create better space for title and author name\n"
                issues_to_address += "- Enhance composition and focal point\n"
            
            # Target audience
            target_audience = metadata_json.get("target_audience", "General readers")
            
            # Prepare prompt variables
            prompt_vars = {
                "genre": metadata_json.get("genre", "Fiction"),
                "book_title": metadata_json.get("title", "Untitled"),
                "current_cover": current_cover,
                "issues_to_address": issues_to_address,
                "target_audience": target_audience
            }
            
            # Create refinement prompt
            refinement_prompt = COVER_REFINEMENT_PROMPT.format(**prompt_vars)
            
            # Generate refinement recommendations from Claude
            claude_messages = [
                get_claude_api().user_message(refinement_prompt)
            ]
            
            options = CompletionOptions(
                system=VISUAL_SYSTEM_PROMPT,
                temperature=0.6,
                max_tokens=2000
            )
            
            claude_response = get_claude_api().complete_with_retry(claude_messages, options)
            
            # Save the refinement recommendations
            refinement_content = claude_response.strip()
            refinement_path = storage.save_component("cover_refinement", refinement_content)
            
            # Extract the revised prompt from the recommendations
            import re
            revised_prompt_match = re.search(r'(?:Revised|New) (?:Image|Generation) Prompt:(.*?)(?:$|\n\n)', refinement_content, re.DOTALL | re.IGNORECASE)
            revised_prompt = revised_prompt_match.group(1).strip() if revised_prompt_match else ""
            
            if not revised_prompt:
                # Try another format
                revised_prompt_match = re.search(r'(?:Prompt|New prompt):(.*?)(?:$|\n\n)', refinement_content, re.DOTALL | re.IGNORECASE)
                revised_prompt = revised_prompt_match.group(1).strip() if revised_prompt_match else ""
            
            # Try to extract structured recommendations
            try:
                # Extract key sections
                composition_match = re.search(r'(?:Composition|Layout):(.*?)(?:\d+\.|\n\n)', refinement_content, re.DOTALL | re.IGNORECASE)
                composition = composition_match.group(1).strip() if composition_match else ""
                
                color_match = re.search(r'(?:Color|Palette):(.*?)(?:\d+\.|\n\n)', refinement_content, re.DOTALL | re.IGNORECASE)
                color = color_match.group(1).strip() if color_match else ""
                
                elements_match = re.search(r'(?:Elements|Content):(.*?)(?:\d+\.|\n\n)', refinement_content, re.DOTALL | re.IGNORECASE)
                elements = elements_match.group(1).strip() if elements_match else ""
                
                # Create structured recommendations
                structured_refinements = {
                    "composition_adjustments": composition,
                    "color_adjustments": color,
                    "element_adjustments": elements,
                    "revised_prompt": revised_prompt,
                    "full_recommendations": refinement_content
                }
            except Exception:
                # If parsing fails, just use the full text
                structured_refinements = {
                    "revised_prompt": revised_prompt,
                    "full_recommendations": refinement_content
                }
            
            # Return the result
            send_result(
                self.agent_id,
                message.sender,
                {
                    "book_id": book_id,
                    "refinement_recommendations": structured_refinements,
                    "revised_prompt": revised_prompt,
                    "refinement_path": refinement_path
                },
                message.message_id,
                {"book_id": book_id}
            )
            
            # Update task status
            self.active_tasks[message.message_id]["status"] = "completed"
            self.active_tasks[message.message_id]["completed_at"] = time.time()
            self.active_tasks[message.message_id]["result"] = structured_refinements
            
        except Exception as e:
            logger.error(f"Error creating cover refinement recommendations: {str(e)}")
            send_error(
                self.agent_id,
                message.sender,
                f"Error creating cover refinement recommendations: {str(e)}",
                message.message_id,
                {"book_id": message.content.get("book_id")}
            )
            self.active_tasks[message.message_id]["status"] = "failed"
            self.active_tasks[message.message_id]["error"] = str(e)
    
    def _recommend_typography(self, message: Message) -> None:
        """
        Recommend typography for cover design.
        
        Args:
            message: The task message
        """
        logger.info("Recommending typography")
        
        try:
            # Extract content from message
            book_id = message.content.get("book_id")
            cover_description = message.content.get("cover_description", "")
            
            if not book_id:
                raise ValueError("Missing book_id in task content")
                
            # Get book metadata
            storage = BookStorage(book_id)
            metadata_json = storage.load_metadata()
            
            # If cover description not provided, use the prompt or concept
            if not cover_description:
                prompt_text = storage.load_component("used_cover_prompt")
                if prompt_text:
                    cover_description = prompt_text
                else:
                    concept_text = storage.load_component("cover_concept")
                    if concept_text:
                        cover_description = concept_text
                    else:
                        cover_description = "No cover description available."
            
            # Get book themes 
            book_themes = ""
            outline_json = storage.load_component("outline")
            if outline_json:
                outline = json.loads(outline_json)
                themes = outline.get("themes", [])
                if isinstance(themes, list):
                    book_themes = "\n".join([f"- {theme}" for theme in themes])
                else:
                    book_themes = str(themes)
            
            if not book_themes:
                book_themes = f"Themes typical of {metadata_json.get('genre', 'fiction')} books."
            
            # Target audience
            target_audience = metadata_json.get("target_audience", "General readers")
            
            # Prepare prompt variables
            prompt_vars = {
                "genre": metadata_json.get("genre", "Fiction"),
                "book_title": metadata_json.get("title", "Untitled"),
                "cover_description": cover_description,
                "book_themes": book_themes,
                "target_audience": target_audience
            }
            
            # Create typography prompt
            typography_prompt = TYPOGRAPHY_RECOMMENDATIONS_PROMPT.format(**prompt_vars)
            
            # Generate typography recommendations from Claude
            claude_messages = [
                get_claude_api().user_message(typography_prompt)
            ]
            
            options = CompletionOptions(
                system=VISUAL_SYSTEM_PROMPT,
                temperature=0.6,
                max_tokens=2000
            )
            
            claude_response = get_claude_api().complete_with_retry(claude_messages, options)
            
            # Save the typography recommendations
            typography_content = claude_response.strip()
            typography_path = storage.save_component("typography_recommendations", typography_content)
            
            # Try to extract structured recommendations
            try:
                import re
                
                # Extract title typography
                title_match = re.search(r'(?:Title Typography|Title Font):(.*?)(?:\d+\.|\n\n)', typography_content, re.DOTALL | re.IGNORECASE)
                title_typography = title_match.group(1).strip() if title_match else ""
                
                # Extract author name typography
                author_match = re.search(r'(?:Author Name Typography|Author Font):(.*?)(?:\d+\.|\n\n)', typography_content, re.DOTALL | re.IGNORECASE)
                author_typography = author_match.group(1).strip() if author_match else ""
                
                # Extract font recommendations
                font_match = re.search(r'(?:Recommended Fonts|Font Suggestions|Specific Fonts):(.*?)(?:\d+\.|\n\n)', typography_content, re.DOTALL | re.IGNORECASE)
                font_recommendations = font_match.group(1).strip() if font_match else ""
                
                # Create structured recommendations
                structured_recommendations = {
                    "title_typography": title_typography,
                    "author_typography": author_typography,
                    "font_recommendations": font_recommendations,
                    "full_recommendations": typography_content
                }
            except Exception:
                # If parsing fails, just use the full text
                structured_recommendations = {
                    "full_recommendations": typography_content
                }
            
            # Return the result
            send_result(
                self.agent_id,
                message.sender,
                {
                    "book_id": book_id,
                    "typography_recommendations": structured_recommendations,
                    "typography_path": typography_path
                },
                message.message_id,
                {"book_id": book_id}
            )
            
            # Update task status
            self.active_tasks[message.message_id]["status"] = "completed"
            self.active_tasks[message.message_id]["completed_at"] = time.time()
            self.active_tasks[message.message_id]["result"] = structured_recommendations
            
        except Exception as e:
            logger.error(f"Error recommending typography: {str(e)}")
            send_error(
                self.agent_id,
                message.sender,
                f"Error recommending typography: {str(e)}",
                message.message_id,
                {"book_id": message.content.get("book_id")}
            )
            self.active_tasks[message.message_id]["status"] = "failed"
            self.active_tasks[message.message_id]["error"] = str(e)
    
    def _create_style_guide(self, message: Message) -> None:
        """
        Create a visual style guide.
        
        Args:
            message: The task message
        """
        logger.info("Creating style guide")
        
        try:
            # Extract content from message
            book_id = message.content.get("book_id")
            book_description = message.content.get("book_description", "")
            visual_requirements = message.content.get("visual_requirements", "")
            
            if not book_id:
                raise ValueError("Missing book_id in task content")
                
            # Get book metadata and outline
            storage = BookStorage(book_id)
            metadata_json = storage.load_metadata()
            
            if not book_description:
                outline_json = storage.load_component("outline")
                if outline_json:
                    outline = json.loads(outline_json)
                    book_description = outline.get("synopsis", "")
                
            if not book_description:
                book_description = f"A {metadata_json.get('genre', 'fiction')} book titled '{metadata_json.get('title', 'Untitled')}'."
            
            # If visual requirements not provided, create default
            if not visual_requirements:
                visual_requirements = "- Professional quality visual elements\n"
                visual_requirements += f"- Style appropriate for {metadata_json.get('genre', 'fiction')} genre\n"
                visual_requirements += f"- Appeal to {metadata_json.get('target_audience', 'general readers')}\n"
                visual_requirements += "- Consistent visual language across all materials\n"
                visual_requirements += "- Marketable and eye-catching design\n"
            
            # Target audience
            target_audience = metadata_json.get("target_audience", "General readers")
            
            # Prepare prompt variables
            prompt_vars = {
                "genre": metadata_json.get("genre", "Fiction"),
                "book_title": metadata_json.get("title", "Untitled"),
                "book_description": book_description,
                "visual_requirements": visual_requirements,
                "target_audience": target_audience
            }
            
            # Create style guide prompt
            style_guide_prompt = ILLUSTRATION_STYLE_GUIDE_PROMPT.format(**prompt_vars)
            
            # Generate style guide from Claude
            claude_messages = [
                get_claude_api().user_message(style_guide_prompt)
            ]
            
            options = CompletionOptions(
                system=VISUAL_SYSTEM_PROMPT,
                temperature=0.6,
                max_tokens=3000
            )
            
            claude_response = get_claude_api().complete_with_retry(claude_messages, options)
            
            # Save the style guide
            style_guide_content = claude_response.strip()
            style_guide_path = storage.save_component("style_guide", style_guide_content)
            
            # Try to extract key sections
            try:
                import re
                
                # Extract visual style
                style_match = re.search(r'(?:Visual Style|Style Definition):(.*?)(?:\d+\.|\n\n)', style_guide_content, re.DOTALL | re.IGNORECASE)
                visual_style = style_match.group(1).strip() if style_match else ""
                
                # Extract color palette
                color_match = re.search(r'(?:Color Palette|Colors):(.*?)(?:\d+\.|\n\n)', style_guide_content, re.DOTALL | re.IGNORECASE)
                color_palette = color_match.group(1).strip() if color_match else ""
                
                # Extract composition principles
                composition_match = re.search(r'(?:Composition|Layout):(.*?)(?:\d+\.|\n\n)', style_guide_content, re.DOTALL | re.IGNORECASE)
                composition = composition_match.group(1).strip() if composition_match else ""
                
                # Create structured style guide
                structured_style_guide = {
                    "visual_style": visual_style,
                    "color_palette": color_palette,
                    "composition": composition,
                    "full_style_guide": style_guide_content
                }
            except Exception:
                # If parsing fails, just use the full text
                structured_style_guide = {
                    "full_style_guide": style_guide_content
                }
            
            # Return the result
            send_result(
                self.agent_id,
                message.sender,
                {
                    "book_id": book_id,
                    "style_guide": structured_style_guide,
                    "style_guide_path": style_guide_path
                },
                message.message_id,
                {"book_id": book_id}
            )
            
            # Update task status
            self.active_tasks[message.message_id]["status"] = "completed"
            self.active_tasks[message.message_id]["completed_at"] = time.time()
            self.active_tasks[message.message_id]["result"] = structured_style_guide
            
        except Exception as e:
            logger.error(f"Error creating style guide: {str(e)}")
            send_error(
                self.agent_id,
                message.sender,
                f"Error creating style guide: {str(e)}",
                message.message_id,
                {"book_id": message.content.get("book_id")}
            )
            self.active_tasks[message.message_id]["status"] = "failed"
            self.active_tasks[message.message_id]["error"] = str(e)
    
    def _refine_cover_concept(self, book_id: str, parent_task_id: str, feedback: str) -> None:
        """
        Refine a cover concept based on feedback.
        
        Args:
            book_id: Book ID
            parent_task_id: Parent task ID that received feedback
            feedback: Feedback text
        """
        # Create a new task for self to refine the cover concept
        task_id = create_task(
            self.agent_id,  # Send from self to self
            self.agent_id,
            "agent_task", 
            {
                "book_id": book_id,
                "task_description": "Refine the cover concept based on feedback",
                "feedback": feedback,
                "parent_task_id": parent_task_id
            },
            parent_task_id
        )
        
        # Process the message
        messages = message_queue.get_messages(self.agent_id)
        for message in messages:
            if message.message_id == task_id:
                self._process_message(message)
                break
    
    def _create_refinement_from_feedback(self, book_id: str, parent_task_id: str, feedback: str) -> None:
        """
        Create a cover art refinement task based on feedback.
        
        Args:
            book_id: Book ID
            parent_task_id: Parent task ID that received feedback
            feedback: Feedback text
        """
        # Create a new task for self to refine the cover art
        task_id = create_task(
            self.agent_id,  # Send from self to self
            self.agent_id,
            VisualTask.REFINE_COVER_ART.value, 
            {
                "book_id": book_id,
                "task_description": "Refine the cover art based on feedback",
                "issues_to_address": feedback,
                "parent_task_id": parent_task_id
            },
            parent_task_id
        )
        
        # Process the message
        messages = message_queue.get_messages(self.agent_id)
        for message in messages:
            if message.message_id == task_id:
                self._process_message(message)
                break
