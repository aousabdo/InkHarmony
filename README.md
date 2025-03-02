# InkHarmony
# InkHarmony: AI-Powered Book Generation System

InkHarmony is an agentic AI system that creates complete books through collaborative work between specialized AI agents. The system leverages Claude and Stability AI to generate high-quality content including narrative text and cover art.

## Features

- **Multi-Agent Architecture**: Specialized AI agents work together to create cohesive books
- **End-to-End Generation**: From concept to final manuscript and cover
- **Web Interface**: Simple UI for book creation and management
- **Modular Design**: Easily extensible for new capabilities

## System Components

### AI Agents

- **Maestro Agent**: Orchestrates the book creation process
- **Outline Architect**: Creates detailed book outlines and structures
- **Narrative Writer**: Transforms outlines into engaging prose
- **Linguistic Polisher**: Improves language quality and consistency
- **Visual Design Coordinator**: Creates cover art concepts and images

### Technical Architecture

- **Messaging System**: Enables communication between agents
- **Workflow Manager**: Tracks book creation progress through phases
- **Storage System**: Manages book content and assets
- **Web Interface**: Provides user control over the generation process

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/inkharmony.git
cd inkharmony
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
export ANTHROPIC_API_KEY=your_claude_api_key
export STABILITY_API_KEY=your_stability_api_key
```

## Usage

### Starting the Web Interface

```bash
python web/app.py
```

This will start the web server at http://localhost:5000 where you can create and manage books.

### Command Line Usage

You can also use InkHarmony from the command line:

```bash
# Initialize the system
python inkharmony.py --initialize

# Create a new book
python inkharmony.py --create-book --title "My Amazing Book" --genre "fantasy" --description "An epic tale of adventure"

# List all books
python inkharmony.py --list-books

# Get book status
python inkharmony.py --book-id BOOK_ID --get-status

# Export a book
python inkharmony.py --book-id BOOK_ID --export
```

## Book Generation Process

1. **Initialization**: Set book metadata and parameters
2. **Outline Creation**: Generate plot, characters, and chapter structure
3. **Content Creation**: Write chapters based on the outline
4. **Review & Refinement**: Polish language and ensure consistency
5. **Production**: Create cover art and compile final book

## Extending InkHarmony

You can extend InkHarmony by:

1. Adding new agent types in the `agents/` directory
2. Implementing new models in the `models/` directory
3. Creating additional prompt templates in the `templates/` directory

## Requirements

- Python 3.8+
- Claude API access
- Stability AI API access
- Flask (for web interface)

## License

[MIT License](LICENSE)

## Acknowledgments

- Built using Anthropic's Claude
- Cover art generation by Stability AI