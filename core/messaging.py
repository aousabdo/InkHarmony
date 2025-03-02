"""
Agent communication system for InkHarmony.
Handles message passing between agents with standardized formats.
"""
import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, List, Any, Optional, Union
from enum import Enum

class MessageType(Enum):
    """Types of messages that can be exchanged between agents."""
    TASK = "task"  # A task assignment
    RESULT = "result"  # Results of a completed task
    FEEDBACK = "feedback"  # Feedback on a result
    QUERY = "query"  # A question for another agent
    RESPONSE = "response"  # A response to a query
    STATUS = "status"  # Status update
    ERROR = "error"  # Error notification


@dataclass
class Message:
    """Standard message format for agent communication."""
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    message_type: MessageType = MessageType.TASK
    sender: str = "system"
    recipient: str = "maestro"
    content: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    parent_id: Optional[str] = None  # ID of the message this is responding to
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary format."""
        result = asdict(self)
        result["message_type"] = self.message_type.value
        return result
    
    def to_json(self) -> str:
        """Convert message to JSON string."""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        """Create message from dictionary."""
        if isinstance(data.get("message_type"), str):
            data["message_type"] = MessageType(data["message_type"])
        return cls(**data)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'Message':
        """Create message from JSON string."""
        return cls.from_dict(json.loads(json_str))


class MessageQueue:
    """Simple in-memory queue for message passing between agents."""
    def __init__(self):
        self.queues: Dict[str, List[Message]] = {}
        self.history: List[Message] = []
    
    def register_agent(self, agent_id: str) -> None:
        """Register an agent to receive messages."""
        if agent_id not in self.queues:
            self.queues[agent_id] = []
    
    def send_message(self, message: Message) -> str:
        """
        Send a message to an agent.
        Returns the message ID.
        """
        # Register agents if they don't exist
        self.register_agent(message.sender)
        self.register_agent(message.recipient)
        
        # Add message to recipient's queue
        self.queues[message.recipient].append(message)
        
        # Add to history
        self.history.append(message)
        
        return message.message_id
    
    def get_messages(self, agent_id: str) -> List[Message]:
        """Get all messages for an agent."""
        self.register_agent(agent_id)
        messages = self.queues[agent_id].copy()
        self.queues[agent_id] = []
        return messages
    
    def peek_messages(self, agent_id: str) -> List[Message]:
        """Peek at messages without removing them."""
        self.register_agent(agent_id)
        return self.queues[agent_id].copy()
    
    def get_history(self, filter_by: Optional[Dict[str, Any]] = None) -> List[Message]:
        """
        Get message history, optionally filtered.
        
        Args:
            filter_by: Dictionary of field/value pairs to filter messages.
                      For example: {'sender': 'maestro', 'message_type': MessageType.TASK}
        
        Returns:
            List of messages that match the filter.
        """
        if not filter_by:
            return self.history.copy()
        
        result = self.history.copy()
        for key, value in filter_by.items():
            result = [msg for msg in result if getattr(msg, key) == value]
        
        return result
    
    def get_conversation(self, message_id: str) -> List[Message]:
        """
        Get the conversation thread for a message.
        Traces parent_id links to reconstruct the conversation.
        """
        # Find the root message by following parent_id links
        msg = next((m for m in self.history if m.message_id == message_id), None)
        if not msg:
            return []
        
        # Find the root message
        root_msg = msg
        while root_msg.parent_id:
            parent = next((m for m in self.history if m.message_id == root_msg.parent_id), None)
            if not parent:
                break
            root_msg = parent
        
        # Get all messages in the thread
        thread_msgs = [root_msg]
        self._add_children_to_thread(root_msg.message_id, thread_msgs)
        
        # Sort by timestamp
        thread_msgs.sort(key=lambda m: m.timestamp)
        return thread_msgs
    
    def _add_children_to_thread(self, parent_id: str, thread_msgs: List[Message]) -> None:
        """Recursively add child messages to a thread."""
        children = [m for m in self.history if m.parent_id == parent_id]
        for child in children:
            thread_msgs.append(child)
            self._add_children_to_thread(child.message_id, thread_msgs)


# Global message queue instance
message_queue = MessageQueue()

def create_task(sender: str, recipient: str, task_type: str, content: Dict[str, Any], 
                parent_id: Optional[str] = None) -> str:
    """
    Create and send a task message.
    
    Args:
        sender: ID of the sending agent
        recipient: ID of the receiving agent
        task_type: Type of task (used in metadata)
        content: Task content
        parent_id: Optional ID of parent message
    
    Returns:
        The message ID
    """
    msg = Message(
        message_type=MessageType.TASK,
        sender=sender,
        recipient=recipient,
        content=content,
        parent_id=parent_id,
        metadata={"task_type": task_type}
    )
    return message_queue.send_message(msg)

def send_result(sender: str, recipient: str, content: Dict[str, Any], 
               parent_id: str, metadata: Dict[str, Any] = None) -> str:
    """
    Send a result message in response to a task.
    
    Args:
        sender: ID of the sending agent
        recipient: ID of the receiving agent
        content: Result content
        parent_id: ID of the task message
        metadata: Optional additional metadata
    
    Returns:
        The message ID
    """
    msg = Message(
        message_type=MessageType.RESULT,
        sender=sender,
        recipient=recipient,
        content=content,
        parent_id=parent_id,
        metadata=metadata or {}
    )
    return message_queue.send_message(msg)

def send_feedback(sender: str, recipient: str, feedback: str, 
                 parent_id: str, rating: Optional[int] = None) -> str:
    """
    Send feedback on a result.
    
    Args:
        sender: ID of the sending agent
        recipient: ID of the receiving agent
        feedback: Feedback text
        parent_id: ID of the result message
        rating: Optional numerical rating (1-5)
    
    Returns:
        The message ID
    """
    content = {"feedback": feedback}
    metadata = {}
    if rating is not None:
        metadata["rating"] = rating
    
    msg = Message(
        message_type=MessageType.FEEDBACK,
        sender=sender,
        recipient=recipient,
        content=content,
        parent_id=parent_id,
        metadata=metadata
    )
    return message_queue.send_message(msg)

def send_error(sender: str, recipient: str, error_message: str, 
              parent_id: Optional[str] = None, details: Dict[str, Any] = None) -> str:
    """
    Send error notification.
    
    Args:
        sender: ID of the sending agent
        recipient: ID of the receiving agent
        error_message: Error description
        parent_id: Optional ID of related message
        details: Optional error details
    
    Returns:
        The message ID
    """
    msg = Message(
        message_type=MessageType.ERROR,
        sender=sender,
        recipient=recipient,
        content={"error": error_message},
        parent_id=parent_id,
        metadata=details or {}
    )
    return message_queue.send_message(msg)