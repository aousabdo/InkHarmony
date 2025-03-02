"""
Maestro Agent for InkHarmony.
Orchestrates the book creation process and manages agent interactions.
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
from core.workflow import workflow_manager, BookWorkflow, WorkflowStatus
from models.claude import get_claude_api, claude_api, ClaudeMessage, CompletionOptions
from templates.maestro_templates import (
    MAESTRO_SYSTEM_PROMPT,
    INITIALIZATION_PROMPT,
    TASK_ASSIGNMENT_PROMPT,
    RESULT_EVALUATION_PROMPT,
    WORKFLOW_MANAGEMENT_PROMPT,
    ERROR_HANDLING_PROMPT
)

# Set up logging
logger = logging.getLogger(__name__)

class MaestroTask(Enum):
    """Types of tasks the Maestro can perform."""
    INITIALIZE_BOOK = "initialize_book"
    ASSIGN_TASK = "assign_task"
    EVALUATE_RESULT = "evaluate_result"
    PROGRESS_WORKFLOW = "progress_workflow"
    HANDLE_ERROR = "handle_error"
    GENERATE_REPORT = "generate_report"


class MaestroAgent:
    """
    Maestro Agent that orchestrates the book creation process.
    """
    
    def __init__(self, agent_id: str = "maestro"):
        """
        Initialize the Maestro Agent.
        
        Args:
            agent_id: Identifier for this agent instance
        """
        self.agent_id = agent_id
        self.active_workflows: Dict[str, BookWorkflow] = {}
        
        # Register with message queue
        message_queue.register_agent(self.agent_id)
        
        logger.info(f"Maestro Agent initialized with ID: {self.agent_id}")
    
    def run(self) -> None:
        """
        Main agent loop. Processes messages and handles tasks.
        """
        logger.info(f"Maestro Agent {self.agent_id} started")
        
        while True:
            # Process incoming messages
            messages = message_queue.get_messages(self.agent_id)
            for message in messages:
                self._process_message(message)
            
            # Process active workflows (check for next steps)
            for book_id, workflow in list(self.active_workflows.items()):
                if workflow.status == WorkflowStatus.RUNNING:
                    self._process_workflow(workflow)
            
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
            elif message.message_type == MessageType.RESULT:
                self._handle_result(message)
            elif message.message_type == MessageType.ERROR:
                self._handle_error(message)
            elif message.message_type == MessageType.QUERY:
                self._handle_query(message)
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
        task_type = message.metadata.get("task_type")
        if not task_type:
            send_error(
                self.agent_id,
                message.sender,
                "Missing task_type in metadata",
                message.message_id
            )
            return
            
        if task_type == MaestroTask.INITIALIZE_BOOK.value:
            self._initialize_book(message)
        elif task_type == MaestroTask.ASSIGN_TASK.value:
            self._assign_task(message)
        elif task_type == MaestroTask.EVALUATE_RESULT.value:
            self._evaluate_result(message)
        elif task_type == MaestroTask.PROGRESS_WORKFLOW.value:
            self._progress_workflow(message)
        elif task_type == MaestroTask.HANDLE_ERROR.value:
            self._handle_workflow_error(message)
        elif task_type == MaestroTask.GENERATE_REPORT.value:
            self._generate_report(message)
        else:
            send_error(
                self.agent_id,
                message.sender,
                f"Unknown task type: {task_type}",
                message.message_id
            )
    
    def _handle_result(self, message: Message) -> None:
        """
        Handle a result message.
        
        Args:
            message: The result message
        """
        # Find the original task message
        task_messages = message_queue.get_history(
            {"message_id": message.parent_id, "message_type": MessageType.TASK}
        )
        
        if not task_messages:
            logger.warning(f"Could not find original task for result: {message.message_id}")
            return
            
        task_message = task_messages[0]
        
        # Update workflow with result
        book_id = message.metadata.get("book_id")
        if book_id:
            workflow = workflow_manager.get_workflow(book_id)
            if workflow:
                workflow.add_result(task_message.message_id, message.content)
                
        # Send acknowledgment
        send_feedback(
            self.agent_id,
            message.sender,
            "Result received and processed",
            message.message_id
        )
    
    def _handle_error(self, message: Message) -> None:
        """
        Handle an error message.
        
        Args:
            message: The error message
        """
        error_text = message.content.get("error", "Unknown error")
        logger.error(f"Error from {message.sender}: {error_text}")
        
        # Update workflow with error
        book_id = message.metadata.get("book_id")
        if book_id:
            workflow = workflow_manager.get_workflow(book_id)
            if workflow:
                workflow.fail(error_text)
    
    def _handle_query(self, message: Message) -> None:
        """
        Handle a query message.
        
        Args:
            message: The query message
        """
        query_type = message.metadata.get("query_type")
        book_id = message.metadata.get("book_id")
        
        if not query_type:
            send_error(
                self.agent_id,
                message.sender,
                "Missing query_type in metadata",
                message.message_id
            )
            return
            
        if query_type == "workflow_status" and book_id:
            # Retrieve workflow status
            status = workflow_manager.get_workflow_status(book_id)
            send_result(
                self.agent_id,
                message.sender,
                {"status": status},
                message.message_id
            )
        else:
            send_error(
                self.agent_id,
                message.sender,
                f"Unknown query type: {query_type}",
                message.message_id
            )
    
    def _initialize_book(self, message: Message) -> None:
        """
        Initialize a new book project.
        
        Args:
            message: The initialization task message
        """
        book_metadata = message.content.get("metadata", {})
        
        try:
            # Create prompt for Claude to help with initialization
            prompt_vars = {
                "title": book_metadata.get("title", "Untitled Book"),
                "genre": book_metadata.get("genre", "Unknown"),
                "description": book_metadata.get("description", "No description provided"),
                "style": book_metadata.get("style", "Standard"),
                "target_audience": book_metadata.get("target_audience", "General"),
                "length": book_metadata.get("length", "Novel"),
            }
            
            initialization_prompt = INITIALIZATION_PROMPT.format(**prompt_vars)
            
            # Get advice from Claude
            claude_messages = [
                get_claude_api().user_message(initialization_prompt)
            ]
            
            options = CompletionOptions(
                system=MAESTRO_SYSTEM_PROMPT,
                temperature=0.7
            )
            
            claude_response = get_claude_api().complete_with_retry(claude_messages, options)
            
            try:
                # Parse the result as JSON
                result = json.loads(claude_response)
            except json.JSONDecodeError:
                # If Claude didn't return valid JSON, create a structured result
                result = {
                    "title": book_metadata.get("title", "Untitled Book"),
                    "genre": book_metadata.get("genre", "Unknown"),
                    "concept": claude_response.strip(),
                    "estimated_chapters": book_metadata.get("chapter_count", 10),
                    "character_count": 0,
                    "target_audience": book_metadata.get("target_audience", "General"),
                    "themes": []
                }
            
            # Create new workflow
            book_id = workflow_manager.create_workflow(result)
            
            # Add to active workflows
            workflow = workflow_manager.get_workflow(book_id)
            if workflow:
                self.active_workflows[book_id] = workflow
            
            # Return the result
            send_result(
                self.agent_id,
                message.sender,
                {
                    "book_id": book_id,
                    "initialization": result
                },
                message.message_id
            )
            
            # Start the workflow
            workflow_manager.start_workflow(book_id)
            
        except Exception as e:
            logger.error(f"Error initializing book: {str(e)}")
            send_error(
                self.agent_id,
                message.sender,
                f"Error initializing book: {str(e)}",
                message.message_id
            )
    
    def _assign_task(self, message: Message) -> None:
        """
        Assign a task to another agent.
        
        Args:
            message: The task assignment message
        """
        book_id = message.content.get("book_id")
        target_agent = message.content.get("agent")
        task_details = message.content.get("task_details", {})
        
        if not book_id or not target_agent:
            send_error(
                self.agent_id,
                message.sender,
                "Missing book_id or agent in content",
                message.message_id
            )
            return
        
        try:
            # Get the workflow
            workflow = workflow_manager.get_workflow(book_id)
            if not workflow:
                send_error(
                    self.agent_id,
                    message.sender,
                    f"Workflow not found for book_id: {book_id}",
                    message.message_id
                )
                return
            
            # Create prompt for Claude to help with task assignment
            prompt_vars = {
                "book_id": book_id,
                "target_agent": target_agent,
                "task_details": json.dumps(task_details, indent=2),
                "workflow_phase": workflow.current_phase or "unknown",
                "book_metadata": json.dumps(workflow.metadata, indent=2)
            }
            
            task_prompt = TASK_ASSIGNMENT_PROMPT.format(**prompt_vars)
            
            # Get advice from Claude
            claude_messages = [
                get_claude_api().user_message(task_prompt)
            ]
            
            options = CompletionOptions(
                system=MAESTRO_SYSTEM_PROMPT,
                temperature=0.7
            )
            
            claude_response = get_claude_api().complete_with_retry(claude_messages, options)
            
            try:
                # Parse the result as JSON
                task_content = json.loads(claude_response)
            except json.JSONDecodeError:
                # If Claude didn't return valid JSON, create a structured task
                task_content = {
                    "task_description": claude_response.strip(),
                    "requirements": [],
                    "context": task_details,
                    "book_id": book_id
                }
            
            # Create the task
            task_id = create_task(
                self.agent_id,
                target_agent,
                "agent_task",
                task_content,
                message.message_id
            )
            
            # Store the task in the workflow
            workflow.add_task(task_id, {
                "agent": target_agent,
                "task_details": task_details,
                "assigned_at": time.time()
            })
            
            # Return the result
            send_result(
                self.agent_id,
                message.sender,
                {
                    "task_id": task_id,
                    "agent": target_agent,
                    "book_id": book_id
                },
                message.message_id
            )
            
        except Exception as e:
            logger.error(f"Error assigning task: {str(e)}")
            send_error(
                self.agent_id,
                message.sender,
                f"Error assigning task: {str(e)}",
                message.message_id
            )
    
    def _evaluate_result(self, message: Message) -> None:
        """
        Evaluate a task result.
        
        Args:
            message: The evaluation task message
        """
        book_id = message.content.get("book_id")
        result_id = message.content.get("result_id")
        eval_criteria = message.content.get("criteria", {})
        
        if not book_id or not result_id:
            send_error(
                self.agent_id,
                message.sender,
                "Missing book_id or result_id in content",
                message.message_id
            )
            return
        
        try:
            # Get the workflow
            workflow = workflow_manager.get_workflow(book_id)
            if not workflow:
                send_error(
                    self.agent_id,
                    message.sender,
                    f"Workflow not found for book_id: {book_id}",
                    message.message_id
                )
                return
            
            # Get the result message
            result_messages = message_queue.get_history(
                {"message_id": result_id, "message_type": MessageType.RESULT}
            )
            
            if not result_messages:
                send_error(
                    self.agent_id,
                    message.sender,
                    f"Result message not found for ID: {result_id}",
                    message.message_id
                )
                return
                
            result_message = result_messages[0]
            
            # Create prompt for Claude to help with evaluation
            prompt_vars = {
                "book_id": book_id,
                "agent": result_message.sender,
                "result_content": json.dumps(result_message.content, indent=2),
                "evaluation_criteria": json.dumps(eval_criteria, indent=2),
                "workflow_phase": workflow.current_phase or "unknown",
                "book_metadata": json.dumps(workflow.metadata, indent=2)
            }
            
            eval_prompt = RESULT_EVALUATION_PROMPT.format(**prompt_vars)
            
            # Get evaluation from Claude
            claude_messages = [
                get_claude_api().user_message(eval_prompt)
            ]
            
            options = CompletionOptions(
                system=MAESTRO_SYSTEM_PROMPT,
                temperature=0.4  # Lower temperature for more consistent evaluation
            )
            
            claude_response = get_claude_api().complete_with_retry(claude_messages, options)
            
            try:
                # Parse the result as JSON
                evaluation = json.loads(claude_response)
            except json.JSONDecodeError:
                # If Claude didn't return valid JSON, create a structured evaluation
                evaluation = {
                    "feedback": claude_response.strip(),
                    "quality_score": 3,
                    "meets_requirements": True,
                    "improvement_suggestions": []
                }
            
            # Send feedback to the agent
            send_feedback(
                self.agent_id,
                result_message.sender,
                evaluation.get("feedback", ""),
                result_id,
                evaluation.get("quality_score", 3)
            )
            
            # Return the evaluation
            send_result(
                self.agent_id,
                message.sender,
                {
                    "evaluation": evaluation,
                    "book_id": book_id,
                    "result_id": result_id
                },
                message.message_id
            )
            
        except Exception as e:
            logger.error(f"Error evaluating result: {str(e)}")
            send_error(
                self.agent_id,
                message.sender,
                f"Error evaluating result: {str(e)}",
                message.message_id
            )
    
    def _progress_workflow(self, message: Message) -> None:
        """
        Progress a workflow to the next step.
        
        Args:
            message: The progression task message
        """
        book_id = message.content.get("book_id")
        action = message.content.get("action", "next")
        
        if not book_id:
            send_error(
                self.agent_id,
                message.sender,
                "Missing book_id in content",
                message.message_id
            )
            return
        
        try:
            # Get the workflow
            workflow = workflow_manager.get_workflow(book_id)
            if not workflow:
                send_error(
                    self.agent_id,
                    message.sender,
                    f"Workflow not found for book_id: {book_id}",
                    message.message_id
                )
                return
            
            # Create prompt for Claude to help with workflow management
            prompt_vars = {
                "book_id": book_id,
                "current_phase": workflow.current_phase or "none",
                "workflow_status": workflow.status.value,
                "action": action,
                "book_metadata": json.dumps(workflow.metadata, indent=2),
                "workflow_status_full": json.dumps(workflow.get_status(), indent=2)
            }
            
            workflow_prompt = WORKFLOW_MANAGEMENT_PROMPT.format(**prompt_vars)
            
            # Get advice from Claude
            claude_messages = [
                get_claude_api().user_message(workflow_prompt)
            ]
            
            options = CompletionOptions(
                system=MAESTRO_SYSTEM_PROMPT,
                temperature=0.5
            )
            
            claude_response = get_claude_api().complete_with_retry(claude_messages, options)
            
            try:
                # Parse the result as JSON
                decision = json.loads(claude_response)
            except json.JSONDecodeError:
                # If Claude didn't return valid JSON, create a structured decision
                decision = {
                    "action": action,
                    "reasoning": claude_response.strip(),
                    "next_steps": []
                }
            
            # Execute the decision
            result = {
                "previous_status": workflow.get_status(),
                "action_taken": decision.get("action", action),
                "reasoning": decision.get("reasoning", ""),
                "next_steps": decision.get("next_steps", [])
            }
            
            if action == "next" or decision.get("action") == "next":
                if workflow.current_phase:
                    workflow_manager.complete_phase(book_id)
                    result["outcome"] = "Advanced to next phase"
                else:
                    workflow_manager.start_workflow(book_id)
                    result["outcome"] = "Started workflow"
            elif action == "pause" or decision.get("action") == "pause":
                workflow_manager.pause_workflow(book_id)
                result["outcome"] = "Paused workflow"
            elif action == "resume" or decision.get("action") == "resume":
                workflow_manager.resume_workflow(book_id)
                result["outcome"] = "Resumed workflow"
            else:
                result["outcome"] = "No action taken"
            
            # Get updated status
            result["current_status"] = workflow_manager.get_workflow_status(book_id)
            
            # Return the result
            send_result(
                self.agent_id,
                message.sender,
                result,
                message.message_id
            )
            
        except Exception as e:
            logger.error(f"Error progressing workflow: {str(e)}")
            send_error(
                self.agent_id,
                message.sender,
                f"Error progressing workflow: {str(e)}",
                message.message_id
            )
    
    def _handle_workflow_error(self, message: Message) -> None:
        """
        Handle a workflow error.
        
        Args:
            message: The error handling task message
        """
        book_id = message.content.get("book_id")
        error_details = message.content.get("error_details", {})
        
        if not book_id:
            send_error(
                self.agent_id,
                message.sender,
                "Missing book_id in content",
                message.message_id
            )
            return
        
        try:
            # Get the workflow
            workflow = workflow_manager.get_workflow(book_id)
            if not workflow:
                send_error(
                    self.agent_id,
                    message.sender,
                    f"Workflow not found for book_id: {book_id}",
                    message.message_id
                )
                return
            
            # Create prompt for Claude to help with error handling
            prompt_vars = {
                "book_id": book_id,
                "current_phase": workflow.current_phase or "none",
                "workflow_status": workflow.status.value,
                "error_details": json.dumps(error_details, indent=2),
                "book_metadata": json.dumps(workflow.metadata, indent=2),
                "workflow_status_full": json.dumps(workflow.get_status(), indent=2)
            }
            
            error_prompt = ERROR_HANDLING_PROMPT.format(**prompt_vars)
            
            # Get advice from Claude
            claude_messages = [
                get_claude_api().user_message(error_prompt)
            ]
            
            options = CompletionOptions(
                system=MAESTRO_SYSTEM_PROMPT,
                temperature=0.5
            )
            
            claude_response = get_claude_api().complete_with_retry(claude_messages, options)
            
            try:
                # Parse the result as JSON
                error_handling = json.loads(claude_response)
            except json.JSONDecodeError:
                # If Claude didn't return valid JSON, create a structured response
                error_handling = {
                    "assessment": claude_response.strip(),
                    "recommendation": "retry",
                    "recovery_steps": []
                }
            
            # Execute the recommendation
            result = {
                "error_assessment": error_handling.get("assessment", ""),
                "recommendation": error_handling.get("recommendation", ""),
                "recovery_steps": error_handling.get("recovery_steps", [])
            }
            
            # Return the result
            send_result(
                self.agent_id,
                message.sender,
                result,
                message.message_id
            )
            
        except Exception as e:
            logger.error(f"Error handling workflow error: {str(e)}")
            send_error(
                self.agent_id,
                message.sender,
                f"Error handling workflow error: {str(e)}",
                message.message_id
            )
    
    def _generate_report(self, message: Message) -> None:
        """
        Generate a report on workflow progress.
        
        Args:
            message: The report generation task message
        """
        book_id = message.content.get("book_id")
        report_type = message.content.get("report_type", "progress")
        
        if not book_id:
            send_error(
                self.agent_id,
                message.sender,
                "Missing book_id in content",
                message.message_id
            )
            return
        
        try:
            # Get the workflow
            workflow = workflow_manager.get_workflow(book_id)
            if not workflow:
                send_error(
                    self.agent_id,
                    message.sender,
                    f"Workflow not found for book_id: {book_id}",
                    message.message_id
                )
                return
            
            # Generate a status report
            status = workflow.get_status()
            
            # Return the result
            send_result(
                self.agent_id,
                message.sender,
                {
                    "report_type": report_type,
                    "book_id": book_id,
                    "status": status,
                    "generated_at": time.time()
                },
                message.message_id
            )
            
        except Exception as e:
            logger.error(f"Error generating report: {str(e)}")
            send_error(
                self.agent_id,
                message.sender,
                f"Error generating report: {str(e)}",
                message.message_id
            )
    
    def _process_workflow(self, workflow: BookWorkflow) -> None:
        """
        Process a running workflow, checking for next steps.
        
        Args:
            workflow: The workflow to process
        """
        # This is called periodically for each running workflow
        # Implement the logic for progress checking and task initiation
        pass
    
    def start_book_creation(self, metadata: Dict[str, Any]) -> str:
        """
        Start the creation of a new book.
        
        Args:
            metadata: Book metadata including title, genre, etc.
            
        Returns:
            Book ID
        """
        # Create a task for self to initialize the book
        message_id = create_task(
            "system",
            self.agent_id,
            MaestroTask.INITIALIZE_BOOK.value,
            {"metadata": metadata}
        )
        
        # Process the message immediately
        messages = message_queue.get_messages(self.agent_id)
        for message in messages:
            if message.message_id == message_id:
                self._process_message(message)
                break
        
        # Get the response
        responses = message_queue.get_history({
            "parent_id": message_id,
            "message_type": MessageType.RESULT,
            "sender": self.agent_id
        })
        
        if not responses:
            raise Exception("Failed to initialize book")
            
        response = responses[0]
        return response.content.get("book_id")
