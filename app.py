import asyncio
from flask import Flask, request, jsonify
from flask_cors import CORS
from crawl4ai import AsyncWebCrawler
import sys

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
    async with AsyncWebCrawler(verbose=True) as crawler:
        result = await crawler.arun(url=url)

        return {
            'markdown': result.markdown[:5000] if result.markdown else '',  # Limit to first 5000 chars
            'html': result.html[:2000] if result.html else '',  # First 2000 chars of HTML
            'links': result.links['internal'][:10] if hasattr(result, 'links') and result.links else [],
            'media': result.media['images'][:10] if hasattr(result, 'media') and result.media else []
        }

@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    print("Starting Crawl4AI Web Crawler Server...")
    print("Server running at http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)
