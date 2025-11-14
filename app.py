import asyncio
from flask import Flask, request, jsonify
from flask_cors import CORS
from crawl4ai import AsyncWebCrawler
import sys
import xml.etree.ElementTree as ET
from urllib.parse import urlparse, urljoin
import re

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
            'markdown_full': result['markdown_full'],
            'html': result['html'],
            'links': result['links'],
            'media': result['media'],
            'filename': generate_filename_from_url(url)
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

async def crawl_url(url, full_content=False):
    """Async function to crawl a URL using Crawl4AI"""
    async with AsyncWebCrawler(verbose=True) as crawler:
        result = await crawler.arun(url=url)

        # Return full content for download, or truncated for preview
        markdown = result.markdown if result.markdown else ''
        html = result.html if result.html else ''

        if not full_content:
            markdown = markdown[:5000]  # Limit to first 5000 chars for preview
            html = html[:2000]  # First 2000 chars of HTML for preview

        return {
            'markdown': markdown,
            'markdown_full': result.markdown if result.markdown else '',  # Always include full for download
            'html': html,
            'links': result.links['internal'][:10] if hasattr(result, 'links') and result.links else [],
            'media': result.media['images'][:10] if hasattr(result, 'media') and result.media else []
        }

async def fetch_sitemap_urls(base_url):
    """Fetch and parse sitemap to get all URLs"""
    sitemap_urls = []

    # Common sitemap locations
    possible_sitemaps = [
        urljoin(base_url, '/sitemap.xml'),
        urljoin(base_url, '/sitemap_index.xml'),
        urljoin(base_url, '/sitemap-index.xml'),
        urljoin(base_url, '/robots.txt')
    ]

    async with AsyncWebCrawler(verbose=False) as crawler:
        # Try to find sitemap
        for sitemap_url in possible_sitemaps:
            try:
                result = await crawler.arun(url=sitemap_url)

                if sitemap_url.endswith('robots.txt'):
                    # Parse robots.txt for sitemap location
                    if result.html:
                        for line in result.html.split('\n'):
                            if line.lower().startswith('sitemap:'):
                                sitemap_location = line.split(':', 1)[1].strip()
                                sitemap_result = await crawler.arun(url=sitemap_location)
                                urls = parse_sitemap_xml(sitemap_result.html)
                                if urls:
                                    return urls
                else:
                    # Parse XML sitemap
                    urls = parse_sitemap_xml(result.html)
                    if urls:
                        return urls
            except Exception as e:
                continue

    return sitemap_urls

def parse_sitemap_xml(xml_content):
    """Parse sitemap XML and extract URLs"""
    urls = []

    if not xml_content:
        return urls

    try:
        # Remove namespace for easier parsing
        xml_content = re.sub(r'xmlns="[^"]+"', '', xml_content)
        root = ET.fromstring(xml_content)

        # Check if it's a sitemap index
        for sitemap in root.findall('.//sitemap'):
            loc = sitemap.find('loc')
            if loc is not None and loc.text:
                urls.append(loc.text)

        # Check for regular URLs
        for url in root.findall('.//url'):
            loc = url.find('loc')
            if loc is not None and loc.text:
                urls.append(loc.text)

    except Exception as e:
        print(f"Error parsing sitemap XML: {e}")

    return urls

def generate_filename_from_url(url):
    """Generate a safe filename from URL"""
    parsed = urlparse(url)
    path = parsed.path.strip('/')

    if not path:
        return 'homepage.md'

    # Replace slashes with underscores and remove special characters
    filename = path.replace('/', '_').replace('\\', '_')
    filename = re.sub(r'[^\w\-_.]', '_', filename)

    # Add .md extension if not present
    if not filename.endswith('.md'):
        filename += '.md'

    return filename

@app.route('/api/crawl-sitemap', methods=['POST'])
def crawl_sitemap():
    """Endpoint to crawl all pages in a sitemap"""
    try:
        data = request.get_json()
        url = data.get('url')

        if not url:
            return jsonify({'error': 'URL is required'}), 400

        # Validate URL format
        if not url.startswith('http://') and not url.startswith('https://'):
            url = 'https://' + url

        # Fetch sitemap URLs
        sitemap_urls = asyncio.run(fetch_sitemap_urls(url))

        if not sitemap_urls:
            return jsonify({
                'success': False,
                'error': 'No sitemap found or sitemap is empty'
            }), 404

        # Crawl all URLs from sitemap
        results = asyncio.run(crawl_multiple_urls(sitemap_urls))

        return jsonify({
            'success': True,
            'base_url': url,
            'total_pages': len(results),
            'pages': results
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

async def crawl_multiple_urls(urls):
    """Crawl multiple URLs concurrently"""
    results = []

    async with AsyncWebCrawler(verbose=True) as crawler:
        for url in urls[:50]:  # Limit to first 50 URLs to avoid overload
            try:
                result = await crawler.arun(url=url)

                results.append({
                    'url': url,
                    'markdown': result.markdown[:5000] if result.markdown else '',  # Preview
                    'markdown_full': result.markdown if result.markdown else '',  # Full content
                    'filename': generate_filename_from_url(url),
                    'success': True
                })
            except Exception as e:
                results.append({
                    'url': url,
                    'error': str(e),
                    'success': False,
                    'filename': generate_filename_from_url(url)
                })

    return results

@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    print("Starting Crawl4AI Web Crawler Server...")
    print("Server running at http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)
