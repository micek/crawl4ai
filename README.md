# Crawl4AI Web Crawler with Chat UI

A local website crawler built with Crawl4AI featuring a beautiful chat-style user interface for crawling and scraping websites.

## Features

- 🚀 Fast web crawling using Crawl4AI
- 💬 Chat-style UI for easy interaction
- 📄 Extracts content in Markdown format
- 🔗 Discovers internal links
- 🖼️ Finds images and media
- 🎨 Beautiful gradient design
- ⚡ Real-time crawling with async support

## Installation

### Prerequisites
- Python 3.7 or higher
- pip (Python package installer)
- Internet connection (for crawling websites)

### Local Setup

1. **Clone the repository:**
   ```bash
   git clone <your-repo-url>
   cd crawl4ai
   ```

2. **Create a virtual environment (recommended):**
   ```bash
   # On macOS/Linux
   python -m venv venv
   source venv/bin/activate

   # On Windows
   python -m venv venv
   venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Setup Crawl4AI:**
   ```bash
   crawl4ai-setup
   ```

   If you encounter any issues, run the diagnostic tool:
   ```bash
   crawl4ai-doctor
   ```

5. **Install Playwright browsers (if needed):**
   ```bash
   playwright install
   ```

6. **Configure environment variables (optional):**
   ```bash
   cp .env.example .env
   # Edit .env to customize settings (port, debug mode, etc.)
   ```

## Configuration

The application can be configured using environment variables in a `.env` file. Default values work out of the box for local development.

Available settings:
- `FLASK_HOST`: Server host (default: `0.0.0.0`)
- `FLASK_PORT`: Server port (default: `5000`)
- `FLASK_DEBUG`: Debug mode (default: `True`)
- `CRAWLER_VERBOSE`: Verbose crawler output (default: `True`)
- `MAX_MARKDOWN_LENGTH`: Maximum markdown output length (default: `5000`)
- `MAX_HTML_LENGTH`: Maximum HTML output length (default: `2000`)
- `MAX_LINKS`: Maximum number of links to return (default: `10`)
- `MAX_MEDIA`: Maximum number of media items to return (default: `10`)

## Usage

1. **Start the server:**
   ```bash
   python app.py
   ```

2. **Open your browser:**
   Navigate to `http://localhost:5000` (or the port configured in your `.env`)

3. **Crawl websites:**
   - Enter any website URL in the input field
   - Press "Crawl" or hit Enter
   - View the extracted content, links, and media

## Quick Start (TL;DR)

```bash
# Clone and navigate to the project
git clone <your-repo-url>
cd crawl4ai

# Set up virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install and setup
pip install -r requirements.txt
crawl4ai-setup

# Run the application
python app.py

# Open http://localhost:5000 in your browser
```

## Project Structure

```
crawl4ai/
├── app.py              # Flask backend with Crawl4AI integration
├── requirements.txt    # Python dependencies
├── .env.example        # Environment variable template
├── .gitignore          # Git ignore patterns
├── static/
│   └── index.html     # Chat UI interface
└── README.md          # This file
```

## API Endpoints

### POST /api/crawl
Crawls a website and returns extracted content.

**Request:**
```json
{
  "url": "https://example.com"
}
```

**Response:**
```json
{
  "success": true,
  "url": "https://example.com",
  "markdown": "...",
  "html": "...",
  "links": [...],
  "media": [...]
}
```

### GET /api/health
Health check endpoint.

## Technologies Used

- **Backend:** Python, Flask, Crawl4AI
- **Frontend:** HTML, CSS, JavaScript
- **Crawler:** AsyncWebCrawler (headless browser)

## How It Works

1. User enters a URL in the chat interface
2. Frontend sends POST request to `/api/crawl`
3. Backend uses Crawl4AI's AsyncWebCrawler to fetch the page
4. Content is extracted and converted to Markdown
5. Results are displayed in a beautiful chat format

## Troubleshooting

### Common Issues

- **Playwright errors:** Run `playwright install` to install browser binaries
- **Setup issues:** Run `crawl4ai-doctor` for diagnostics
- **Port already in use:** Change `FLASK_PORT` in your `.env` file or set it directly
  ```bash
  # In .env file
  FLASK_PORT=8080

  # Or run with environment variable
  FLASK_PORT=8080 python app.py
  ```
- **Module not found errors:** Make sure your virtual environment is activated
  ```bash
  # On macOS/Linux
  source venv/bin/activate

  # On Windows
  venv\Scripts\activate
  ```
- **Permission errors:** Try running with a virtual environment instead of system Python

### Getting Help

If you encounter any issues:
1. Check that all dependencies are installed: `pip list`
2. Verify your Python version: `python --version` (should be 3.7+)
3. Run the diagnostic tool: `crawl4ai-doctor`
4. Check the console output for detailed error messages

## License

MIT

## Credits

Built with [Crawl4AI](https://github.com/unclecode/crawl4ai) - an open-source LLM-friendly web crawler.
