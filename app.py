import asyncio
from flask import Flask, request, jsonify
from flask_cors import CORS
from crawl4ai import AsyncWebCrawler, AsyncUrlSeeder, SeedingConfig, CrawlerRunConfig
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy
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

    # Browser-like headers to avoid blocking
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }

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
                response = requests.get(sitemap_url, timeout=10, headers=headers)
                if response.status_code == 200:
                    print(f"✓ Found robots.txt")
                    for line in response.text.split('\n'):
                        if line.lower().startswith('sitemap:'):
                            sitemap_location = line.split(':', 1)[1].strip()
                            print(f"Found sitemap in robots.txt: {sitemap_location}")
                            urls = parse_sitemap_recursive(sitemap_location, headers=headers)
                            if urls:
                                print(f"✓ Successfully found {len(urls)} URLs from robots.txt sitemap")
                                return urls
            else:
                # Try to fetch XML sitemap
                response = requests.get(sitemap_url, timeout=10, headers=headers)
                content_type = response.headers.get('Content-Type', '')
                print(f"  Status: {response.status_code}, Content-Type: {content_type}")

                xml_content = None
                if response.status_code == 200 and ('xml' in content_type.lower() or sitemap_url.endswith('.xml')):
                    xml_content = response.text
                elif response.status_code == 403 and sitemap_url.endswith('.xml'):
                    # Try with browser-based crawler for 403 errors
                    print(f"  Trying browser-based fetch for {sitemap_url}...")
                    xml_content = asyncio.run(fetch_xml_with_browser(sitemap_url))

                if xml_content:
                    print(f"✓ Found sitemap at: {sitemap_url}")
                    urls = parse_sitemap_recursive(sitemap_url, xml_content=xml_content, headers=headers)
                    if urls:
                        print(f"✓ Successfully found {len(urls)} URLs")
                        return urls
                    else:
                        print(f"  No URLs extracted from {sitemap_url}")
        except Exception as e:
            print(f"✗ Error fetching {sitemap_url}: {e}")
            continue

    print(f"✗ No sitemap found for {base_url}")
    return []

async def fetch_xml_with_browser(url):
    """Fetch XML content using AsyncWebCrawler to bypass protections"""
    try:
        async with AsyncWebCrawler(verbose=False) as crawler:
            result = await crawler.arun(url=url)
            return result.html if result.html else None
    except Exception as e:
        print(f"Failed to fetch {url} with browser: {e}")
        return None

def parse_sitemap_recursive(sitemap_url, xml_content=None, headers=None):
    """Recursively parse sitemap and all sub-sitemaps to get all page URLs"""
    all_urls = []

    # Default headers if not provided
    if headers is None:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }

    try:
        print(f"Parsing sitemap: {sitemap_url}")

        # Fetch XML content if not provided
        if xml_content is None:
            # First try with requests (faster)
            response = requests.get(sitemap_url, timeout=10, headers=headers)
            if response.status_code == 200:
                xml_content = response.text
            else:
                # If requests fails, try with browser-based crawler
                print(f"  Requests failed ({response.status_code}), trying browser-based fetch...")
                xml_content = asyncio.run(fetch_xml_with_browser(sitemap_url))
                if not xml_content:
                    print(f"Failed to fetch {sitemap_url}")
                    return all_urls

        # Remove namespaces and namespace prefixes for easier parsing
        # First remove namespace declarations
        xml_content = re.sub(r'xmlns="[^"]+"', '', xml_content)
        xml_content = re.sub(r'xmlns:[^=]+="[^"]+"', '', xml_content)
        # Then remove namespace prefixes from element names (e.g., <image:image> becomes <image>)
        xml_content = re.sub(r'<([a-zA-Z0-9_-]+):([a-zA-Z0-9_-]+)', r'<\2', xml_content)
        xml_content = re.sub(r'</([a-zA-Z0-9_-]+):([a-zA-Z0-9_-]+)', r'</\2', xml_content)

        root = ET.fromstring(xml_content)

        # Check if it's a sitemap index (contains other sitemaps)
        sitemap_refs = root.findall('.//sitemap/loc')
        if sitemap_refs:
            print(f"✓ Found sitemap index with {len(sitemap_refs)} sub-sitemaps")
            # This is a sitemap index - recursively fetch all sub-sitemaps
            for sitemap_loc in sitemap_refs:
                if sitemap_loc.text:
                    print(f"  Fetching sub-sitemap: {sitemap_loc.text}")
                    sub_urls = parse_sitemap_recursive(sitemap_loc.text, headers=headers)
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

async def discover_urls_with_seeder(base_url, max_urls=100):
    """
    Discover URLs using AsyncUrlSeeder with automatic fallback.
    Tries: sitemap → Common Crawl → deep crawling
    """
    discovered_urls = []
    method_used = "unknown"

    try:
        print(f"\n=== Starting URL discovery for: {base_url} ===")

        # Method 1: Try sitemap + Common Crawl (recommended approach)
        print("Attempting URL discovery with sitemap+cc (sitemap with Common Crawl fallback)...")
        try:
            config = SeedingConfig(
                source="sitemap+cc",  # Try sitemap first, fall back to Common Crawl
                max_urls=max_urls,
                verbose=True
            )
            seeder = AsyncUrlSeeder()

            # urls() is async and returns List[Dict[str, Any]] where each dict has 'url' key
            url_dicts = await seeder.urls(base_url, config=config)

            # Extract just the URL strings
            for url_dict in url_dicts[:max_urls]:
                if isinstance(url_dict, dict) and 'url' in url_dict:
                    discovered_urls.append(url_dict['url'])
                elif isinstance(url_dict, str):
                    discovered_urls.append(url_dict)

            if discovered_urls:
                method_used = "sitemap+cc"
                print(f"✓ Found {len(discovered_urls)} URLs using sitemap+cc")
                return discovered_urls, method_used
        except Exception as e:
            print(f"sitemap+cc discovery failed: {e}")
            import traceback
            traceback.print_exc()

        # Method 2: Try Common Crawl only
        if not discovered_urls:
            print("\nAttempting URL discovery with Common Crawl only...")
            try:
                config = SeedingConfig(
                    source="cc",  # Common Crawl only
                    max_urls=max_urls,
                    verbose=True
                )
                seeder = AsyncUrlSeeder()

                url_dicts = await seeder.urls(base_url, config=config)

                for url_dict in url_dicts[:max_urls]:
                    if isinstance(url_dict, dict) and 'url' in url_dict:
                        discovered_urls.append(url_dict['url'])
                    elif isinstance(url_dict, str):
                        discovered_urls.append(url_dict)

                if discovered_urls:
                    method_used = "common_crawl"
                    print(f"✓ Found {len(discovered_urls)} URLs using Common Crawl")
                    return discovered_urls, method_used
            except Exception as e:
                print(f"Common Crawl discovery failed: {e}")
                import traceback
                traceback.print_exc()

        # Method 3: Fall back to deep crawling (link-based discovery)
        if not discovered_urls:
            print("\nNo sitemap or Common Crawl data found. Using deep crawl strategy...")
            try:
                async with AsyncWebCrawler(verbose=True) as crawler:
                    config = CrawlerRunConfig(
                        deep_crawl_strategy=BFSDeepCrawlStrategy(
                            max_depth=2,              # Crawl up to 2 levels deep
                            max_pages=max_urls,       # Limit total pages
                            include_external=False    # Stay within domain
                        )
                    )

                    result = await crawler.arun(url=base_url, config=config)

                    # The deep crawl will discover URLs through links
                    # We'll get them from the crawler's discovered URLs
                    if hasattr(result, 'discovered_urls'):
                        discovered_urls = list(result.discovered_urls)[:max_urls]
                    else:
                        # If no discovered_urls attribute, at least include the base URL
                        discovered_urls = [base_url]

                    method_used = "deep_crawl"
                    print(f"✓ Found {len(discovered_urls)} URLs using deep crawl")
                    return discovered_urls, method_used
            except Exception as e:
                print(f"Deep crawl discovery failed: {e}")

        # If all methods fail, return at least the base URL
        if not discovered_urls:
            print("⚠ All URL discovery methods failed. Falling back to base URL only.")
            discovered_urls = [base_url]
            method_used = "fallback"

        return discovered_urls, method_used

    except Exception as e:
        print(f"✗ URL discovery error: {e}")
        # Return at least the base URL so user can crawl something
        return [base_url], "error_fallback"

@app.route('/api/crawl-sitemap', methods=['POST'])
def crawl_sitemap():
    """Endpoint to crawl all pages discovered via sitemap, Common Crawl, or deep crawl"""
    try:
        data = request.get_json()
        url = data.get('url')
        max_urls = data.get('max_urls', 100)  # Allow user to specify max URLs

        if not url:
            return jsonify({'error': 'URL is required'}), 400

        # Validate URL format
        if not url.startswith('http://') and not url.startswith('https://'):
            url = 'https://' + url

        # Discover URLs using AsyncUrlSeeder with automatic fallback
        discovered_urls, method_used = asyncio.run(discover_urls_with_seeder(url, max_urls))

        if not discovered_urls:
            return jsonify({
                'success': False,
                'error': 'Could not discover any URLs. Please check the server logs for details.'
            }), 404

        print(f"\n=== Found {len(discovered_urls)} URLs using '{method_used}' method ===\n")

        # Crawl all discovered URLs
        results = asyncio.run(crawl_multiple_urls(discovered_urls))

        return jsonify({
            'success': True,
            'base_url': url,
            'discovery_method': method_used,
            'total_pages': len(results),
            'pages': results
        })

    except Exception as e:
        print(f"Error in crawl_sitemap: {e}")
        import traceback
        traceback.print_exc()
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
