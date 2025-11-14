import asyncio
import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from crawl4ai import AsyncWebCrawler
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configuration from environment variables with sensible defaults
FLASK_HOST = os.getenv('FLASK_HOST', '0.0.0.0')
FLASK_PORT = int(os.getenv('FLASK_PORT', 5000))
FLASK_DEBUG = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
CRAWLER_VERBOSE = os.getenv('CRAWLER_VERBOSE', 'True').lower() == 'true'
MAX_MARKDOWN_LENGTH = int(os.getenv('MAX_MARKDOWN_LENGTH', 5000))
MAX_HTML_LENGTH = int(os.getenv('MAX_HTML_LENGTH', 2000))
MAX_LINKS = int(os.getenv('MAX_LINKS', 10))
MAX_MEDIA = int(os.getenv('MAX_MEDIA', 10))

app = Flask(__name__)
CORS(app)

@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/api/crawl', methods=['POST'])
def crawl():
    """Endpoint to crawl a website URL"""
    try:
        data = request.get_json()
        url = data.get('url')

        if not url:
            return jsonify({'error': 'URL is required'}), 400

        # Validate URL format
        if not url.startswith('http://') and not url.startswith('https://'):
            url = 'https://' + url

        # Run the async crawler
        result = asyncio.run(crawl_url(url))

        return jsonify({
            'success': True,
            'url': url,
            'markdown': result['markdown'],
            'html': result['html'],
            'links': result['links'],
            'media': result['media']
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

async def crawl_url(url):
    """Async function to crawl a URL using Crawl4AI"""
    async with AsyncWebCrawler(verbose=CRAWLER_VERBOSE) as crawler:
        result = await crawler.arun(url=url)

        return {
            'markdown': result.markdown[:MAX_MARKDOWN_LENGTH] if result.markdown else '',
            'html': result.html[:MAX_HTML_LENGTH] if result.html else '',
            'links': result.links['internal'][:MAX_LINKS] if hasattr(result, 'links') and result.links else [],
            'media': result.media['images'][:MAX_MEDIA] if hasattr(result, 'media') and result.media else []
        }

@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    print("Starting Crawl4AI Web Crawler Server...")
    print(f"Server running at http://localhost:{FLASK_PORT}")
    app.run(debug=FLASK_DEBUG, host=FLASK_HOST, port=FLASK_PORT)
