"""
Workflow management for the InkHarmony book generation process.
Coordinates the different phases and agent interactions.
"""
import time
import uuid
import logging
from enum import Enum
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass, field

# Change relative imports to absolute imports
import sys
import os
# Add the project root directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import WORKFLOW_PHASES
from core.messaging import message_queue, Message, MessageType, create_task, send_error
from core.storage import BookStorage, create_new_book_id

# Set up logging
logger = logging.getLogger(__name__)

class WorkflowStatus(Enum):
    """Possible statuses for a workflow."""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class PhaseStatus(Enum):
    """Possible statuses for a workflow phase."""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Phase:
    """A phase in the workflow."""
    name: str
    status: PhaseStatus = PhaseStatus.PENDING
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    tasks: Dict[str, Any] = field(default_factory=dict)
    results: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    
    def start(self) -> None:
        """Mark phase as started."""
        self.status = PhaseStatus.RUNNING
        self.started_at = time.time()
    
    def complete(self) -> None:
        """Mark phase as completed."""
        self.status = PhaseStatus.COMPLETED
        self.completed_at = time.time()
    
    def fail(self, error: str) -> None:
        """Mark phase as failed."""
        self.status = PhaseStatus.FAILED
        self.errors.append(error)
    
    def pause(self) -> None:
        """Mark phase as paused."""
        self.status = PhaseStatus.PAUSED
    
    def add_task(self, task_id: str, task_data: Any) -> None:
        """Add a task to the phase."""
        self.tasks[task_id] = task_data
    
    def add_result(self, task_id: str, result_data: Any) -> None:
        """Add a result to the phase."""
        self.results[task_id] = result_data
    
    @property
    def duration(self) -> Optional[float]:
        """Calculate the duration of the phase."""
        if not self.started_at:
            return None
        end_time = self.completed_at or time.time()
        return end_time - self.started_at


@dataclass
class BookWorkflow:
    """Workflow for generating a book."""
    book_id: str = field(default_factory=create_new_book_id)
    status: WorkflowStatus = WorkflowStatus.PENDING
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    current_phase: Optional[str] = None
    phases: Dict[str, Phase] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    storage: Optional[BookStorage] = None
    
    def __post_init__(self):
        """Initialize after creation."""
        # Initialize phases
        for phase_name in WORKFLOW_PHASES:
            self.phases[phase_name] = Phase(name=phase_name)
        
        # Initialize storage
        if not self.storage:
            self.storage = BookStorage(self.book_id)
    
    def start(self) -> None:
        """Start the workflow."""
        self.status = WorkflowStatus.RUNNING
        self.started_at = time.time()
        
        # Start the first phase
        first_phase = WORKFLOW_PHASES[0]
        self.start_phase(first_phase)
    
    def complete(self) -> None:
        """Mark workflow as completed."""
        self.status = WorkflowStatus.COMPLETED
        self.completed_at = time.time()
        self.current_phase = None
        
        # Save final state
        self.save_state()
    
    def fail(self, error: str) -> None:
        """Mark workflow as failed."""
        self.status = WorkflowStatus.FAILED
        
        # If a phase is active, mark it as failed too
        if self.current_phase:
            self.phases[self.current_phase].fail(error)
        
        logger.error(f"Workflow {self.book_id} failed: {error}")
        self.save_state()
    
    def pause(self) -> None:
        """Pause the workflow."""
        self.status = WorkflowStatus.PAUSED
        
        # If a phase is active, pause it too
        if self.current_phase:
            self.phases[self.current_phase].pause()
        
        self.save_state()
    
    def resume(self) -> None:
        """Resume the workflow."""
        if self.status != WorkflowStatus.PAUSED:
            return
            
        self.status = WorkflowStatus.RUNNING
        
        # If a phase was active, resume it
        if self.current_phase:
            self.phases[self.current_phase].status = PhaseStatus.RUNNING
        
        self.save_state()
    
    def start_phase(self, phase_name: str) -> None:
        """
        Start a specific phase.
        
        Args:
            phase_name: Name of the phase to start
        """
        if phase_name not in self.phases:
            raise ValueError(f"Unknown phase: {phase_name}")
            
        # Complete the current phase if there is one
        if self.current_phase:
            self.complete_phase()
            
        # Start the new phase
        self.current_phase = phase_name
        phase = self.phases[phase_name]
        phase.start()
        
        logger.info(f"Started phase: {phase_name} for book {self.book_id}")
        self.save_state()
    
    def complete_phase(self) -> None:
        """Complete the current phase and move to the next."""
        if not self.current_phase:
            return
            
        # Complete the current phase
        phase = self.phases[self.current_phase]
        phase.complete()
        
        logger.info(f"Completed phase: {self.current_phase} for book {self.book_id}")
        
        # Find the next phase
        current_index = WORKFLOW_PHASES.index(self.current_phase)
        if current_index < len(WORKFLOW_PHASES) - 1:
            next_phase = WORKFLOW_PHASES[current_index + 1]
            self.current_phase = None  # Clear before starting next
            self.start_phase(next_phase)
        else:
            # This was the last phase
            self.complete()
        
        self.save_state()
    
    def add_task(self, task_id: str, task_data: Any) -> None:
        """Add a task to the current phase."""
        if not self.current_phase:
            logger.warning(f"Cannot add task {task_id}: no active phase")
            return
            
        self.phases[self.current_phase].add_task(task_id, task_data)
        self.save_state()
    
    def add_result(self, task_id: str, result_data: Any) -> None:
        """Add a result to the current phase."""
        if not self.current_phase:
            logger.warning(f"Cannot add result for task {task_id}: no active phase")
            return
            
        self.phases[self.current_phase].add_result(task_id, result_data)
        self.save_state()
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get the current status of the workflow.
        
        Returns:
            Dictionary with workflow status info
        """
        phase_info = {}
        for name, phase in self.phases.items():
            phase_info[name] = {
                "status": phase.status.value,
                "duration": phase.duration,
                "task_count": len(phase.tasks),
                "result_count": len(phase.results),
                "error_count": len(phase.errors)
            }
            
        return {
            "book_id": self.book_id,
            "status": self.status.value,
            "current_phase": self.current_phase,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration": self.duration,
            "phases": phase_info,
            "metadata": self.metadata
        }
    
    @property
    def duration(self) -> Optional[float]:
        """Calculate the duration of the workflow."""
        if not self.started_at:
            return None
        end_time = self.completed_at or time.time()
        return end_time - self.started_at
    
    def save_state(self) -> None:
        """Save workflow state to storage."""
        self.storage.save_state(self)
        
        # Also save metadata
        metadata = self.metadata.copy()
        metadata.update({
            "book_id": self.book_id,
            "status": self.status.value,
            "current_phase": self.current_phase,
            "started_at": self.started_at,
            "completed_at": self.completed_at
        })
        self.storage.save_metadata(metadata)
    
    @classmethod
    def load(cls, book_id: str) -> Optional['BookWorkflow']:
        """
        Load workflow state from storage.
        
        Args:
            book_id: ID of the book workflow to load
            
        Returns:
            BookWorkflow object or None if not found
        """
        storage = BookStorage(book_id)
        workflow = storage.load_state()
        
        if not workflow or not isinstance(workflow, cls):
            return None
            
        # Refresh storage reference
        workflow.storage = storage
        return workflow


class WorkflowManager:
    """Manages active book generation workflows."""
    
    def __init__(self):
        """Initialize the workflow manager."""
        self.active_workflows: Dict[str, BookWorkflow] = {}
    
    def create_workflow(self, metadata: Dict[str, Any]) -> str:
        """
        Create a new book generation workflow.
        
        Args:
            metadata: Book metadata
            
        Returns:
            Book ID
        """
        workflow = BookWorkflow()
        workflow.metadata = metadata
        
        # Save initial state
        workflow.save_state()
        
        # Add to active workflows
        self.active_workflows[workflow.book_id] = workflow
        
        return workflow.book_id
    
    def get_workflow(self, book_id: str) -> Optional[BookWorkflow]:
        """
        Get a workflow by book ID.
        
        Args:
            book_id: ID of the book
            
        Returns:
            BookWorkflow or None if not found
        """
        # Check active workflows first
        if book_id in self.active_workflows:
            return self.active_workflows[book_id]
            
        # Try to load from storage
        workflow = BookWorkflow.load(book_id)
        if workflow:
            self.active_workflows[book_id] = workflow
            
        return workflow
    
    def start_workflow(self, book_id: str) -> bool:
        """
        Start a workflow.
        
        Args:
            book_id: ID of the book
            
        Returns:
            True if successful, False otherwise
        """
        workflow = self.get_workflow(book_id)
        if not workflow:
            return False
            
        workflow.start()
        return True
    
    def pause_workflow(self, book_id: str) -> bool:
        """
        Pause a workflow.
        
        Args:
            book_id: ID of the book
            
        Returns:
            True if successful, False otherwise
        """
        workflow = self.get_workflow(book_id)
        if not workflow:
            return False
            
        workflow.pause()
        return True
    
    def resume_workflow(self, book_id: str) -> bool:
        """
        Resume a paused workflow.
        
        Args:
            book_id: ID of the book
            
        Returns:
            True if successful, False otherwise
        """
        workflow = self.get_workflow(book_id)
        if not workflow:
            return False
            
        workflow.resume()
        return True
    
    def complete_phase(self, book_id: str) -> bool:
        """
        Complete the current phase of a workflow.
        
        Args:
            book_id: ID of the book
            
        Returns:
            True if successful, False otherwise
        """
        workflow = self.get_workflow(book_id)
        if not workflow:
            return False
            
        workflow.complete_phase()
        return True
    
    def add_task_result(self, book_id: str, task_id: str, result: Any) -> bool:
        """
        Add a task result to a workflow.
        
        Args:
            book_id: ID of the book
            task_id: ID of the task
            result: Task result data
            
        Returns:
            True if successful, False otherwise
        """
        workflow = self.get_workflow(book_id)
        if not workflow:
            return False
            
        workflow.add_result(task_id, result)
        return True
    
    def get_workflow_status(self, book_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the status of a workflow.
        
        Args:
            book_id: ID of the book
            
        Returns:
            Status dictionary or None if workflow not found
        """
        workflow = self.get_workflow(book_id)
        if not workflow:
            return None
            
        return workflow.get_status()
    
    def list_workflows(self) -> List[Dict[str, Any]]:
        """
        List all active workflows.
        
        Returns:
            List of workflow status dictionaries
        """
        return [workflow.get_status() for workflow in self.active_workflows.values()]


# Global workflow manager instance
workflow_manager = WorkflowManager()