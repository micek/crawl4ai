import asyncio
from flask import Flask, request, jsonify
from flask_cors import CORS
from crawl4ai import AsyncWebCrawler
import sys
import xml.etree.ElementTree as ET
from urllib.parse import urlparse, urljoin
import re
import requests

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

        # Return full markdown content (no truncation)
        markdown = result.markdown if result.markdown else ''

        return {
            'markdown': markdown,
            'markdown_full': markdown,  # Same as markdown (full content)
            'html': result.html if result.html else '',
            'links': result.links['internal'][:10] if hasattr(result, 'links') and result.links else [],
            'media': result.media['images'][:10] if hasattr(result, 'media') and result.media else []
        }

def fetch_sitemap_urls(base_url):
    """Fetch and parse sitemap to get all URLs using requests for XML"""
    print(f"\n=== Starting sitemap fetch for: {base_url} ===")

    # Common sitemap locations
    possible_sitemaps = [
        urljoin(base_url, '/sitemap.xml'),
        urljoin(base_url, '/sitemap_index.xml'),
        urljoin(base_url, '/sitemap-index.xml'),
        urljoin(base_url, '/wp-sitemap.xml'),  # WordPress
        urljoin(base_url, '/sitemap-index.xml'),
        urljoin(base_url, '/robots.txt')
    ]

    # Try to find sitemap
    for sitemap_url in possible_sitemaps:
        try:
            print(f"Trying: {sitemap_url}")

            if sitemap_url.endswith('robots.txt'):
                # Parse robots.txt for sitemap location
                response = requests.get(sitemap_url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
                if response.status_code == 200:
                    print(f"✓ Found robots.txt")
                    for line in response.text.split('\n'):
                        if line.lower().startswith('sitemap:'):
                            sitemap_location = line.split(':', 1)[1].strip()
                            print(f"Found sitemap in robots.txt: {sitemap_location}")
                            urls = parse_sitemap_recursive(sitemap_location)
                            if urls:
                                print(f"✓ Successfully found {len(urls)} URLs from robots.txt sitemap")
                                return urls
            else:
                # Try to fetch XML sitemap
                response = requests.get(sitemap_url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
                if response.status_code == 200 and ('xml' in response.headers.get('Content-Type', '').lower() or sitemap_url.endswith('.xml')):
                    print(f"✓ Found sitemap at: {sitemap_url}")
                    urls = parse_sitemap_recursive(sitemap_url, xml_content=response.text)
                    if urls:
                        print(f"✓ Successfully found {len(urls)} URLs")
                        return urls
        except Exception as e:
            print(f"✗ Error fetching {sitemap_url}: {e}")
            continue

    print(f"✗ No sitemap found for {base_url}")
    return []

def parse_sitemap_recursive(sitemap_url, xml_content=None):
    """Recursively parse sitemap and all sub-sitemaps to get all page URLs"""
    all_urls = []

    try:
        print(f"Parsing sitemap: {sitemap_url}")

        # Fetch XML content if not provided
        if xml_content is None:
            response = requests.get(sitemap_url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
            if response.status_code != 200:
                print(f"Failed to fetch {sitemap_url}: HTTP {response.status_code}")
                return all_urls
            xml_content = response.text

        # Remove namespaces for easier parsing
        xml_content = re.sub(r'xmlns="[^"]+"', '', xml_content)
        xml_content = re.sub(r'xmlns:[^=]+="[^"]+"', '', xml_content)

        root = ET.fromstring(xml_content)

        # Check if it's a sitemap index (contains other sitemaps)
        sitemap_refs = root.findall('.//sitemap/loc')
        if sitemap_refs:
            print(f"✓ Found sitemap index with {len(sitemap_refs)} sub-sitemaps")
            # This is a sitemap index - recursively fetch all sub-sitemaps
            for sitemap_loc in sitemap_refs:
                if sitemap_loc.text:
                    print(f"  Fetching sub-sitemap: {sitemap_loc.text}")
                    sub_urls = parse_sitemap_recursive(sitemap_loc.text)
                    all_urls.extend(sub_urls)
                    print(f"  Got {len(sub_urls)} URLs from sub-sitemap")

        # Get actual page URLs from this sitemap
        url_locs = root.findall('.//url/loc')
        if url_locs:
            page_urls = [loc.text for loc in url_locs if loc.text]
            print(f"✓ Found {len(page_urls)} page URLs in this sitemap")
            all_urls.extend(page_urls)

        # Also check for simple URL lists (some sitemaps use this format)
        if not sitemap_refs and not url_locs:
            loc_tags = root.findall('.//loc')
            if loc_tags:
                page_urls = [loc.text for loc in loc_tags if loc.text]
                print(f"✓ Found {len(page_urls)} URLs (simple format)")
                all_urls.extend(page_urls)

    except ET.ParseError as e:
        print(f"✗ XML Parse Error for {sitemap_url}: {e}")
    except Exception as e:
        print(f"✗ Error parsing sitemap {sitemap_url}: {e}")

    return all_urls

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

        # Fetch sitemap URLs (synchronous)
        sitemap_urls = fetch_sitemap_urls(url)

        if not sitemap_urls:
            return jsonify({
                'success': False,
                'error': 'No sitemap found or sitemap is empty. Please check the server logs for details.'
            }), 404

        print(f"\n=== Found {len(sitemap_urls)} total URLs to crawl ===\n")

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
    total = len(urls)

    print(f"Starting to crawl {total} URLs...")

    async with AsyncWebCrawler(verbose=True) as crawler:
        for index, url in enumerate(urls, 1):  # Crawl ALL URLs from sitemap (no limit)
            try:
                print(f"\n[{index}/{total}] Crawling: {url}")
                result = await crawler.arun(url=url)

                markdown = result.markdown if result.markdown else ''
                print(f"✓ Success! Got {len(markdown)} characters of markdown")

                results.append({
                    'url': url,
                    'markdown': markdown,  # Full content (no truncation)
                    'markdown_full': markdown,  # Full content
                    'filename': generate_filename_from_url(url),
                    'success': True
                })
            except Exception as e:
                print(f"✗ Failed: {e}")
                results.append({
                    'url': url,
                    'error': str(e),
                    'success': False,
                    'filename': generate_filename_from_url(url)
                })

    successful = len([r for r in results if r.get('success')])
    print(f"\n=== Crawling complete: {successful}/{total} successful ===\n")

    return results

@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    print("Starting Crawl4AI Web Crawler Server...")
    print("Server running at http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)
