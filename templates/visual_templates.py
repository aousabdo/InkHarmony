"""
Prompt templates for the Visual Design Coordinator Agent.
"""

# System prompt that defines the visual design coordinator agent's role and capabilities
VISUAL_SYSTEM_PROMPT = """
You are the Visual Design Coordinator Agent in the InkHarmony book generation system. Your role is to create visual elements for books, primarily focusing on cover art design.

Your responsibilities include:
1. Generating detailed cover art concepts based on book content
2. Creating effective visual prompts for image generation systems
3. Analyzing book themes, mood, and genre to inform visual design
4. Evaluating generated images for quality and appropriateness
5. Suggesting refinements to improve visual elements
6. Ensuring visual elements align with book content and target audience

Your expertise lies in visual storytelling, composition, color theory, typography, and understanding genre-specific visual conventions. You understand how to translate narrative themes and atmosphere into compelling visual designs.

When creating visual elements, consider:
- The genre and its visual conventions
- The book's themes, mood, and emotional tone
- Key characters, settings, or symbols from the story
- Target audience expectations and preferences
- Composition principles that draw the viewer's eye
- Color psychology and palette selection
- Typography and text placement for eventual cover design

Provide your visual concepts as detailed, clear descriptions that can be used with image generation systems. Be specific about composition, lighting, color, style, mood, and important elements to include.

For cover design specifically, focus on creating images that would entice readers to pick up the book while accurately representing its content and genre.
"""

# Template for generating cover art concept
COVER_CONCEPT_PROMPT = """
I need to create a cover art concept for a {genre} book titled "{book_title}".

Book Synopsis:
{book_synopsis}

Key Themes and Elements:
{key_themes}

Target Audience:
{target_audience}

Design Preferences:
{design_preferences}

Please develop a detailed cover art concept that effectively represents this book. Consider genre conventions, key visual elements from the story, color palette, mood, and composition.

Your response should include:
1. A high-level concept description (1-2 paragraphs)
2. Key visual elements to include
3. Suggestions for composition and focal points
4. Recommended color palette and lighting
5. Style recommendations (photorealistic, illustrated, abstract, etc.)
6. Mood and atmosphere considerations
7. Typography recommendations for the title and author name

The concept should balance being visually striking and marketable while accurately representing the book's content and appealing to the target audience.
"""

# Template for creating image generation prompts
IMAGE_PROMPT_TEMPLATE = """
I need to create effective prompts for generating the cover art for a {genre} book titled "{book_title}" using {generation_system}.

Cover Concept:
{cover_concept}

Key Visual Elements:
{key_elements}

Style Preference:
{style_preference}

Please create three distinct image generation prompts that will produce high-quality, commercially viable book cover art based on this concept.

Each prompt should:
1. Be optimized for {generation_system}'s capabilities
2. Include specific details about composition, lighting, color, style, and mood
3. Incorporate appropriate keywords that will guide the image generation
4. Specify what should be the focal point or center of attention
5. Include any necessary negative prompts (elements to avoid)

Format each prompt for direct use with the image generation system, ready to copy and paste.
"""

# Template for evaluating generated cover art
COVER_EVALUATION_PROMPT = """
I need to evaluate this generated cover art for a {genre} book titled "{book_title}".

Original Cover Concept:
{cover_concept}

Key Requirements:
{key_requirements}

[The image has been generated and is being evaluated]

Please analyze this cover art for its effectiveness and alignment with the book's content and marketing needs. Consider:

1. Visual Impact: How striking and attention-grabbing is the image?
2. Genre Alignment: How well does it signal the book's genre to potential readers?
3. Concept Fulfillment: How closely does it match the intended cover concept?
4. Marketability: How appealing would this be to the target audience?
5. Technical Quality: Assess composition, color harmony, focal point, etc.
6. Typography Potential: Are there good spaces for title and author name placement?
7. Uniqueness: Is it distinctive enough to stand out in the marketplace?

For each aspect, provide a rating from 1-5 and brief justification. Then give overall recommendations: accept as is, accept with minor modifications, or regenerate with specific changes.
"""

# Template for cover refinement recommendations
COVER_REFINEMENT_PROMPT = """
I need refinement recommendations for this cover art for a {genre} book titled "{book_title}".

Current Cover Description:
{current_cover}

Issues to Address:
{issues_to_address}

Target Audience:
{target_audience}

Please provide specific recommendations for refining this cover art to make it more effective. Consider:

1. Composition adjustments
2. Color and lighting modifications
3. Element additions or removals
4. Style adjustments
5. Mood enhancements
6. Typography and layout suggestions

For each recommendation, explain why it would improve the cover's effectiveness and appeal to the target audience. Prioritize the changes from most to least important.

Also provide a revised image generation prompt that incorporates these refinements, ready to use with the image generation system.
"""

# Template for typography recommendations
TYPOGRAPHY_RECOMMENDATIONS_PROMPT = """
I need typography recommendations for the cover of a {genre} book titled "{book_title}".

Cover Art Description:
{cover_description}

Book Themes:
{book_themes}

Target Audience:
{target_audience}

Please provide comprehensive typography recommendations for this book cover, including:

1. Title Typography:
   - Font style recommendations (specific fonts if possible, or font types)
   - Size and prominence considerations
   - Color options that work with the cover art
   - Placement recommendations on the cover
   - Special effects or treatments (if appropriate)

2. Author Name Typography:
   - Font style recommendations (usually complementary to title font)
   - Size and prominence relative to title
   - Color options
   - Placement recommendations

3. Any Additional Text Elements:
   - Series name (if applicable)
   - Tagline
   - Endorsements or review quotes

4. Overall Typography Guidance:
   - Contrast considerations to ensure readability
   - Hierarchy of text elements
   - Balance with visual elements
   - Genre-appropriate styling

Your recommendations should be specific, practical, and align with both the visual style of the cover and the genre expectations. Consider how the typography will enhance the marketability and professional appearance of the book.
"""

# Template for illustration style guide
ILLUSTRATION_STYLE_GUIDE_PROMPT = """
I need to create an illustration style guide for a {genre} book titled "{book_title}".

Book Description:
{book_description}

Visual Requirements:
{visual_requirements}

Target Audience:
{target_audience}

Please create a comprehensive illustration style guide that could be used for creating consistent visual elements for this book (cover art, chapter illustrations, marketing materials, etc.). The guide should include:

1. Visual Style Definition:
   - Overall artistic approach (e.g., realistic, stylized, minimalist)
   - Reference artists or existing works with similar desired style
   - Level of detail and complexity

2. Color Palette:
   - Primary colors (3-5 main colors)
   - Secondary/accent colors
   - Color meaning and usage guidance

3. Character Visualization (if applicable):
   - General approach to character depiction
   - Key physical attributes to maintain
   - Expression and posing guidelines

4. Environment/Setting Visualization:
   - Approach to backgrounds and settings
   - Level of detail in environmental elements
   - Key environmental features to include

5. Composition Principles:
   - Framing and layout preferences
   - Focal point guidance
   - Balance and white space considerations

6. Mood and Atmosphere:
   - Lighting guidance
   - Texture and surface treatment
   - Overall emotional tone to convey

The style guide should be cohesive, align with the book's themes and genre, and provide clear direction that would ensure visual consistency across different illustrations.
"""
