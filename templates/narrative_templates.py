"""
Prompt templates for the Narrative Writer Agent.
"""

# System prompt that defines the narrative writer agent's role and capabilities
NARRATIVE_SYSTEM_PROMPT = """
You are the Narrative Writer Agent in the InkHarmony book generation system. Your role is to transform outline structures and plot points into engaging, well-crafted prose.

Your responsibilities include:
1. Converting chapter outlines into full-length chapters
2. Creating compelling dialogue between characters
3. Crafting vivid scene descriptions
4. Developing character voices and perspectives
5. Maintaining consistent tone and style throughout the narrative
6. Implementing literary techniques appropriate to the genre and style

Your expertise lies in creative writing, narrative flow, dialogue construction, and perspective management. You understand how to translate structural outlines into engaging prose that captures readers' attention.

When writing content, consider:
- The intended writing style and tone for the book
- Genre expectations and conventions
- Character personalities and relationships
- Setting details and atmosphere
- Pacing and tension appropriate to the scene
- Showing versus telling principles
- Narrative point of view and perspective

Provide your written content in clear, polished prose ready for direct inclusion in the book. Format dialogue, paragraphs, and scene transitions according to standard conventions.

Always maintain the plot points and character development specified in the outline while bringing them to life through compelling narrative.
"""

# Template for writing a complete chapter
CHAPTER_WRITING_PROMPT = """
I need you to write Chapter {chapter_number}: "{chapter_title}" for a {genre} book titled "{book_title}".

Chapter Outline:
{chapter_outline}

Character Information:
{character_info}

Previous Chapter Summary (for continuity):
{previous_chapter}

Writing Style Guidelines:
{style_guidelines}

Key elements to include:
{key_elements}

Please write a complete chapter that follows this outline while bringing it to life with vivid descriptions, engaging dialogue, and appropriate pacing. Maintain the established writing style and ensure character voices remain consistent.

The chapter should feel like a polished section of a published book in the {genre} genre, with appropriate scene transitions, dialogue formatting, and narrative flow.

Aim for approximately {target_word_count} words, with natural pacing and scene development.
"""

# Template for rewriting or revising a chapter
CHAPTER_REVISION_PROMPT = """
I need you to revise Chapter {chapter_number}: "{chapter_title}" of a {genre} book titled "{book_title}".

Original Chapter:
{original_chapter}

Revision Instructions:
{revision_instructions}

Character Information:
{character_info}

Writing Style Guidelines:
{style_guidelines}

Please revise this chapter according to the instructions while maintaining the core plot elements and character development. Improve the prose, dialogue, pacing, and descriptions as needed, while keeping the overall narrative direction intact.

The revised chapter should feel like a polished section of a published book in the {genre} genre, with improved clarity, engagement, and flow.
"""

# Template for writing a specific scene
SCENE_WRITING_PROMPT = """
I need you to write a specific scene for Chapter {chapter_number} of a {genre} book titled "{book_title}".

Scene Context:
{scene_context}

Characters Present:
{characters_present}

Setting Description:
{setting}

Key Events:
{key_events}

Emotional Tone:
{emotional_tone}

Writing Style Guidelines:
{style_guidelines}

Please write a complete scene that incorporates the key events while creating an engaging, vivid narrative experience. Use appropriate dialogue, description, and pacing for the emotional tone specified.

The scene should flow naturally, with a clear beginning, middle, and end, while advancing the plot and developing the characters involved.
"""

# Template for writing dialogue
DIALOGUE_WRITING_PROMPT = """
I need you to write dialogue for a scene in Chapter {chapter_number} of a {genre} book titled "{book_title}".

Scene Context:
{scene_context}

Characters in Conversation:
{characters}

Conversation Purpose:
{conversation_purpose}

Character Relationships:
{character_relationships}

Emotional Undercurrents:
{emotional_undercurrents}

Key Information to Reveal:
{key_reveals}

Writing Style Guidelines:
{style_guidelines}

Please write natural-sounding dialogue that reveals character personalities, advances the plot, and incorporates the key information specified. Include minimal dialogue tags and appropriate body language or action beats.

The conversation should feel authentic to each character's voice and background while serving the narrative purpose of the scene.
"""

# Template for writing a description
DESCRIPTION_WRITING_PROMPT = """
I need you to write a descriptive passage for Chapter {chapter_number} of a {genre} book titled "{book_title}".

Element to Describe:
{description_subject}

Relevance to Story:
{story_relevance}

Emotional Tone:
{emotional_tone}

Sensory Elements to Include:
{sensory_elements}

POV Character's Perspective:
{pov_perspective}

Writing Style Guidelines:
{style_guidelines}

Please write a vivid, engaging description that brings this element to life through sensory details, meaningful observations, and appropriate mood. The description should reflect the POV character's perspective and emotional state while fitting seamlessly into the overall narrative.

Avoid excessive adjectives or purple prose unless that fits the established writing style. Focus on details that have narrative significance or emotional impact.
"""

# Template for writing an opening hook
OPENING_HOOK_PROMPT = """
I need you to write a compelling opening for Chapter {chapter_number} of a {genre} book titled "{book_title}".

Chapter Context:
{chapter_context}

Purpose of this Chapter:
{chapter_purpose}

Emotional Tone:
{emotional_tone}

POV Character:
{pov_character}

Writing Style Guidelines:
{style_guidelines}

Please write an engaging opening paragraph or section (up to 300 words) that hooks the reader and establishes the tone for this chapter. The opening should create intrigue, set the scene, introduce conflict, or otherwise compel the reader to continue.

Consider techniques like in-media-res, provocative dialogue, intriguing questions, vivid description, or foreshadowing as appropriate to the genre and story context.
"""

# Template for writing a chapter ending
CHAPTER_ENDING_PROMPT = """
I need you to write a compelling ending for Chapter {chapter_number} of a {genre} book titled "{book_title}".

Chapter Summary:
{chapter_summary}

Next Chapter Preview:
{next_chapter_preview}

Emotional Impact Desired:
{emotional_impact}

Plot Threads to Address:
{plot_threads}

Writing Style Guidelines:
{style_guidelines}

Please write an effective chapter ending (approximately 250-500 words) that provides an appropriate sense of closure for this chapter while creating anticipation for what comes next. The ending should deliver the specified emotional impact and address the relevant plot threads.

Consider techniques like cliffhangers, emotional revelations, quiet reflections, or significant decisions as appropriate to the genre and narrative flow.
"""
