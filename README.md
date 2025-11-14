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

## Quick Start

### Option 1: Using the start script (Easiest)
```bash
./start.sh
```

### Option 2: Manual setup

1. **Install dependencies:**
   ```bash
   pip install --break-system-packages -r requirements.txt
   ```

2. **Setup Crawl4AI:**
   ```bash
   crawl4ai-setup
   python3 -m playwright install chromium
   ```

3. **Start the server:**
   ```bash
   python app.py
   ```

## Usage

1. **Start the server** (if not already running):
   ```bash
   python app.py
   ```

   You should see:
   ```
   Starting Crawl4AI Web Crawler Server...
   Server running at http://localhost:5000
   * Running on http://127.0.0.1:5000
   ```

2. **Open your browser:**
   Navigate to `http://localhost:5000`

3. **Crawl websites:**
   - Enter any website URL in the input field
   - Press "Crawl" or hit Enter
   - View the extracted content, links, and media

## Project Structure

```
crawl4ai/
├── app.py              # Flask backend with Crawl4AI integration
├── requirements.txt    # Python dependencies
├── start.sh            # Quick start script
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

### "ModuleNotFoundError: No module named 'flask'"
Install dependencies first:
```bash
pip install --break-system-packages -r requirements.txt
```

### "Cannot uninstall cryptography" error
This is a system package conflict. Remove old version and reinstall:
```bash
rm -rf /usr/lib/python3/dist-packages/cryptography*
pip install --break-system-packages -r requirements.txt
```

### Playwright browser installation fails
Manually install Chromium:
```bash
python3 -m playwright install chromium
```

### Other issues
- **Setup issues:** Run `crawl4ai-doctor` for diagnostics
- **Port already in use:** Change port in `app.py` (line 59)
- **Playwright errors:** Run `playwright install --with-deps`

## License

MIT

## Credits

Built with [Crawl4AI](https://github.com/unclecode/crawl4ai) - an open-source LLM-friendly web crawler.
