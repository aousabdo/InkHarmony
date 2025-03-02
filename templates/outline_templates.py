"""
Prompt templates for the Outline Architect Agent.
"""

# System prompt that defines the outline architect agent's role and capabilities
OUTLINE_SYSTEM_PROMPT = """
You are the Outline Architect Agent in the InkHarmony book generation system. Your role is to create detailed, well-structured outlines for books based on high-level concepts and specifications.

Your responsibilities include:
1. Creating comprehensive plot outlines with strong narrative arcs
2. Designing chapter structures with appropriate pacing and flow
3. Planning character development arcs throughout the story
4. Establishing settings and worldbuilding elements
5. Ensuring plot coherence and logical progression
6. Identifying themes and motifs to be developed

Your expertise lies in narrative structure, storytelling principles, genre conventions, and pacing. You understand the fundamental elements that make a compelling book in various genres.

When creating outlines, consider:
- The target audience's expectations and preferences
- Genre conventions and tropes (while avoiding clichés)
- Narrative tension and release patterns
- Character development opportunities
- Thematic depth and progression
- Satisfying resolution of plot threads

Provide your outlines in a clear, structured format with sufficient detail to guide the creation of a complete book. Include chapter breakdowns, key plot points, character moments, and setting details.

Always format your responses as JSON objects with appropriate fields for easy parsing and integration into the workflow system.
"""

# Template for creating a full book outline
FULL_OUTLINE_PROMPT = """
I need to create a comprehensive outline for a new book with the following specifications:

Title: {title}
Genre: {genre}
Concept: {concept}
Target Audience: {target_audience}
Estimated Length: {estimated_chapters} chapters
Key Themes: {themes}

{additional_notes}

Please create a detailed outline that includes:
1. A high-level synopsis (1-2 paragraphs)
2. Main character descriptions and arcs
3. Setting descriptions and worldbuilding elements
4. A chapter-by-chapter breakdown with key events
5. Major plot points and turning points
6. Thematic development throughout the narrative

Provide your response as a JSON object with the following fields:
- synopsis: A comprehensive overview of the entire story
- characters: Array of character objects with name, role, description, and arc
- settings: Array of important locations/settings with descriptions
- themes: Array of themes with notes on their development
- chapters: Array of chapter objects with title, summary, key_events, and character_development
- plot_points: Array of major plot points with their chapter locations
- narrative_structure: Object describing the overall structure (e.g., three-act, hero's journey)

Your JSON should be properly formatted with appropriate nesting and ready for direct parsing.
"""

# Template for creating a character outline
CHARACTER_OUTLINE_PROMPT = """
I need to create detailed character outlines for a book with the following specifications:

Title: {title}
Genre: {genre}
Concept: {concept}
Character Notes: {character_notes}

Book Synopsis:
{synopsis}

Please develop {character_count} well-rounded characters for this story, including protagonists, antagonists, and supporting characters as appropriate.

Provide your response as a JSON object with an array of character objects, each containing:
- name: Character's full name
- role: Character's role in the story (protagonist, antagonist, supporting, etc.)
- age: Approximate age (or age range)
- physical_description: Notable physical characteristics
- personality: Key personality traits and attributes
- background: Relevant backstory and history
- motivation: Primary motivations and goals
- conflicts: Internal and external conflicts faced
- relationships: Key relationships with other characters
- arc: Character development throughout the story
- key_scenes: Array of important scenes/moments for this character

Your JSON should be properly formatted with appropriate nesting and ready for direct parsing.
"""

# Template for creating a chapter outline
CHAPTER_OUTLINE_PROMPT = """
I need to create a detailed chapter-by-chapter outline for a book with the following specifications:

Title: {title}
Genre: {genre}
Total Chapters: {chapter_count}

Book Synopsis:
{synopsis}

Characters:
{characters}

Please create a chapter-by-chapter breakdown that forms a cohesive narrative with proper pacing, tension, and character development.

Provide your response as a JSON object with an array of chapter objects, each containing:
- chapter_number: The chapter number
- title: A fitting title for the chapter
- pov_character: The point-of-view character (if applicable)
- setting: The primary location(s) where the chapter takes place
- timeframe: When the chapter occurs in the story timeline
- summary: A 1-2 paragraph summary of the chapter events
- key_events: Array of important plot points or occurrences
- character_development: Notes on character growth or revelations
- themes: Thematic elements explored in the chapter
- tensions: Conflicts or tensions introduced or developed
- cliffhanger: Description of any chapter-ending hook (if applicable)
- approximate_length: Estimated length (short, medium, long)

Your JSON should be properly formatted with appropriate nesting and ready for direct parsing.
"""

# Template for refining an existing outline
OUTLINE_REFINEMENT_PROMPT = """
I need to refine the following book outline to address specific issues or incorporate feedback:

Current Outline:
{current_outline}

Feedback/Issues to Address:
{feedback}

Please revise the outline to address the feedback while maintaining the core concept and strengths of the original outline.

Provide your response as a JSON object with the same structure as the original outline, but with appropriate modifications to address the feedback.

Include a "changes" field at the top level that summarizes the key changes made to the outline.

Your JSON should be properly formatted with appropriate nesting and ready for direct parsing.
"""

# Template for generating plot twists or enhancements
PLOT_ENHANCEMENT_PROMPT = """
I need to enhance a book outline with compelling plot twists, unexpected developments, or deeper complexity:

Book Title: {title}
Genre: {genre}

Current Outline:
{current_outline}

Areas to Enhance:
{enhancement_areas}

Please suggest 3-5 significant plot enhancements that could make the story more engaging, surprising, or emotionally impactful while remaining true to the genre and overall concept.

Provide your response as a JSON object with an array of enhancement objects, each containing:
- enhancement_type: Type of enhancement (e.g., "plot_twist", "subplot", "character_secret", "red_herring")
- description: Detailed description of the enhancement
- placement: Where in the narrative this should be introduced/revealed
- setup_requirements: Any foreshadowing or setup needed earlier in the story
- impact: How this affects characters and the overall plot
- resolution: How this element is resolved or concluded

Your JSON should be properly formatted with appropriate nesting and ready for direct parsing.
"""
