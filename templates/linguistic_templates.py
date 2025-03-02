"""
Prompt templates for the Linguistic Polisher Agent.
"""

# System prompt that defines the linguistic polisher agent's role and capabilities
LINGUISTIC_SYSTEM_PROMPT = """
You are the Linguistic Polisher Agent in the InkHarmony book generation system. Your role is to refine and enhance the language, grammar, style, and readability of book content.

Your responsibilities include:
1. Correcting grammatical and punctuation errors
2. Improving sentence structure and flow
3. Eliminating awkward phrasing and redundancies
4. Enhancing vocabulary and word choice
5. Ensuring consistent tense, voice, and perspective
6. Adjusting pacing through sentence and paragraph structure
7. Maintaining the intended style and tone

Your expertise lies in linguistic precision, stylistic refinement, and narrative clarity. You understand the nuances of language that make writing engaging, clear, and professional.

When polishing content, consider:
- The genre and its conventional language patterns
- The established writing style of the book
- The narrative voice and perspective
- The emotional tone of the content
- The pacing and flow of the narrative
- The balance between dialogue, action, and description
- The appropriate level of formality and complexity

Provide your polished content in a clean, ready-to-use format that maintains the original narrative intention while enhancing its linguistic quality.

For analytical feedback, structure your observations clearly with specific examples and suggested improvements.
"""

# Template for polishing a chapter
CHAPTER_POLISH_PROMPT = """
I need you to polish Chapter {chapter_number}: "{chapter_title}" of a {genre} book titled "{book_title}".

Original Chapter:
{original_content}

Writing Style Guidelines:
{style_guidelines}

Focus areas for polish:
{focus_areas}

The text should maintain the same narrative events, character development, and overall meaning, but with improved language, flow, and readability. Correct any grammatical errors, awkward phrasing, or inconsistencies in tense or perspective.

Please provide the polished content as a complete replacement for the original chapter. The chapter should feel like a professionally edited section of a published book in the {genre} genre, without changing the core content or creative direction.
"""

# Template for detailed language analysis
LANGUAGE_ANALYSIS_PROMPT = """
I need a detailed linguistic analysis of the following text from a {genre} book titled "{book_title}":

Text for Analysis:
{text_content}

Writing Style Guidelines:
{style_guidelines}

Please provide an in-depth analysis of this text's linguistic characteristics, including:
1. Grammar and punctuation assessment
2. Sentence structure patterns and variety
3. Word choice and vocabulary level
4. Narrative voice consistency
5. Tense and perspective consistency
6. Paragraph structure and flow
7. Dialogue conventions and effectiveness
8. Pacing indicators (sentence length, paragraph breaks, etc.)
9. Style consistency with genre expectations
10. Notable strengths and areas for improvement

Format your analysis as a structured report with specific examples from the text and actionable suggestions for improvement. This analysis will be used to guide future writing and editing efforts.
"""

# Template for style consistency check
STYLE_CONSISTENCY_PROMPT = """
I need to check the style consistency of the following text from a {genre} book titled "{book_title}":

Text for Style Check:
{text_content}

Established Style Guidelines:
{style_guidelines}

Reference Text (example of desired style):
{reference_text}

Please analyze how well the text adheres to the established style guidelines and reference text. Focus on:
1. Voice consistency (first person, third person, etc.)
2. Tense consistency
3. Tone and formality level
4. Sentence structure patterns
5. Vocabulary choices and language complexity
6. Paragraph length and structure
7. Dialogue formatting and style
8. Description density and approach

Provide your analysis as a structured report with specific examples from the text and clear recommendations for improving style consistency. Include both strengths and areas that need adjustment.
"""

# Template for readability enhancement
READABILITY_ENHANCEMENT_PROMPT = """
I need to enhance the readability of the following text from a {genre} book titled "{book_title}":

Original Text:
{original_content}

Target Audience:
{target_audience}

Current Readability Issues:
{readability_issues}

Writing Style Guidelines:
{style_guidelines}

Please revise this text to improve its readability while maintaining its core content and intended style. Focus on:
1. Sentence length and complexity
2. Paragraph structure and length
3. Transitional phrases and flow
4. Clarity and precision of language
5. Removal of unnecessary jargon or overly complex vocabulary
6. Appropriate pacing for the target audience
7. Logical progression of ideas
8. Effective use of active voice where appropriate

Provide the enhanced text as a complete replacement for the original, optimized for the specified target audience without sacrificing the quality or meaning of the content.
"""

# Template for dialogue polish
DIALOGUE_POLISH_PROMPT = """
I need to polish the dialogue in the following text from a {genre} book titled "{book_title}":

Original Text:
{original_content}

Character Voice Guidelines:
{character_voices}

Dialogue Focus Areas:
{dialogue_focus}

Writing Style Guidelines:
{style_guidelines}

Please revise the dialogue to make it more natural, character-specific, and effective. Focus on:
1. Making each character's voice distinct and consistent
2. Removing stilted or unrealistic phrasing
3. Balancing dialogue with action and dialogue tags
4. Improving the flow of conversation
5. Ensuring appropriate dialect or speech patterns
6. Making dialogue serve both character and plot
7. Creating more authentic emotional resonance
8. Proper formatting and punctuation

Provide the polished text as a complete replacement for the original, with all dialogue enhanced while maintaining the same narrative events and overall direction.
"""

# Template for continuity check
CONTINUITY_CHECK_PROMPT = """
I need to check linguistic continuity in the following text from a {genre} book titled "{book_title}":

Current Text:
{current_text}

Previous Text:
{previous_text}

Writing Style Guidelines:
{style_guidelines}

Please analyze the linguistic continuity between the previous text and the current text. Focus on:
1. Consistency in character names, descriptions, and voices
2. Consistency in location names and descriptions
3. Temporal markers and timeline consistency
4. Tense consistency across sections
5. Narrative voice and perspective consistency
6. Tone and style consistency
7. Reference consistency (how characters/places/objects are referred to)
8. Repetition of key phrases or motifs (intentional vs. unintentional)

Provide your analysis as a structured report with specific examples and clear recommendations for improving continuity. Where appropriate, suggest specific language corrections to enhance continuity.
"""
