"""
Prompt templates for the Maestro Agent.
"""

# System prompt that defines the maestro agent's role and capabilities
MAESTRO_SYSTEM_PROMPT = """
You are the Maestro Agent in the InkHarmony book generation system. Your role is to orchestrate the book creation process by coordinating specialized AI agents, making strategic decisions, and ensuring quality and coherence.

Your responsibilities include:
1. Initializing book projects based on user specifications
2. Assigning appropriate tasks to specialized agents
3. Evaluating agent outputs for quality and consistency
4. Managing workflow progression through different phases
5. Handling errors and making recovery decisions
6. Generating status reports and monitoring overall progress

You have a strategic view of the entire book creation process and are responsible for maintaining narrative coherence, character consistency, and stylistic alignment throughout the project.

Key skills:
- Decision-making: Make informed choices about task assignment and workflow progression
- Critical evaluation: Assess the quality and appropriateness of agent outputs
- Problem-solving: Address issues that arise during the book creation process
- Strategic planning: Determine the optimal sequence of tasks to achieve the desired outcome

Your responses should be clear, structured, and actionable. When asked to provide task assignments or evaluations, format your responses as JSON objects with appropriate fields for easy parsing and integration into the workflow system.

Remember that you are coordinating a collaborative process among multiple specialized agents to create a cohesive, high-quality book that meets the user's specifications.
"""

# Template for initializing a new book project
INITIALIZATION_PROMPT = """
I need to initialize a new book project with the following specifications:

Title: {title}
Genre: {genre}
Description: {description}
Writing Style: {style}
Target Audience: {target_audience}
Length: {length}

Please help me develop an initial concept and structure for this book. Consider the genre conventions, target audience expectations, and the description provided.

Provide your response as a JSON object with the following fields:
- title: The refined book title
- genre: The primary genre and possibly sub-genres
- concept: A concise 1-2 paragraph description of the book's core concept
- estimated_chapters: Suggested number of chapters
- character_count: Estimated number of significant characters
- target_audience: Refined target audience description
- themes: Array of main themes or motifs

Your JSON should be properly formatted and ready for direct parsing.
"""

# Template for assigning tasks to other agents
TASK_ASSIGNMENT_PROMPT = """
I need to assign a task to the {target_agent} agent for book ID: {book_id}

The current workflow phase is: {workflow_phase}

Task details:
{task_details}

Book metadata:
{book_metadata}

Please help me create a detailed task assignment that provides the agent with clear instructions, context, and requirements.

Provide your response as a JSON object with the following fields:
- task_description: Detailed description of what the agent needs to do
- requirements: Array of specific requirements or constraints
- context: Relevant context information from the book project
- reference_materials: Optional array of references to existing components
- completion_criteria: Clear criteria for task completion
- book_id: The book ID

Your JSON should be properly formatted and ready for direct parsing.
"""

# Template for evaluating agent results
RESULT_EVALUATION_PROMPT = """
I need to evaluate a result provided by the {agent} agent for book ID: {book_id}

The current workflow phase is: {workflow_phase}

Result content:
{result_content}

Evaluation criteria:
{evaluation_criteria}

Book metadata:
{book_metadata}

Please help me evaluate this result based on the provided criteria and in the context of the book project.

Provide your response as a JSON object with the following fields:
- feedback: Constructive feedback about the result
- quality_score: Numerical score from 1-5
- meets_requirements: Boolean indicating if the result meets basic requirements
- improvement_suggestions: Array of specific suggestions for improvement
- strengths: Array of notable strengths
- acceptance_decision: String with one of: "accept", "revise", "reject"

Your JSON should be properly formatted and ready for direct parsing.
"""

# Template for workflow management decisions
WORKFLOW_MANAGEMENT_PROMPT = """
I need to make a decision about workflow progression for book ID: {book_id}

Current phase: {current_phase}
Current workflow status: {workflow_status}
Requested action: {action}

Book metadata:
{book_metadata}

Detailed workflow status:
{workflow_status_full}

Please help me determine if the workflow is ready to progress to the next phase or if additional work is needed in the current phase.

Provide your response as a JSON object with the following fields:
- action: The recommended action (e.g., "next", "pause", "resume", "stay")
- reasoning: Detailed explanation of your recommendation
- next_steps: Array of recommended next steps if staying in current phase
- blockers: Array of any issues blocking progression
- requirements_met: Boolean indicating if phase requirements are met

Your JSON should be properly formatted and ready for direct parsing.
"""

# Template for error handling
ERROR_HANDLING_PROMPT = """
I need to handle an error that occurred in the workflow for book ID: {book_id}

Current phase: {current_phase}
Current workflow status: {workflow_status}

Error details:
{error_details}

Book metadata:
{book_metadata}

Detailed workflow status:
{workflow_status_full}

Please help me assess the error and determine an appropriate recovery strategy.

Provide your response as a JSON object with the following fields:
- assessment: Analysis of the error and its impact
- severity: String with one of: "critical", "major", "minor"
- recommendation: String with one of: "retry", "workaround", "revert", "escalate", "abort"
- recovery_steps: Array of specific steps to recover
- prevention_advice: Suggestions to prevent similar errors

Your JSON should be properly formatted and ready for direct parsing.
"""
