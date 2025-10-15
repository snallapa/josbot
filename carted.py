import requests
from bs4 import BeautifulSoup
import json
import re

def scrape_product(url):
    """
    Scrape product information from a given URL.
    Returns a dictionary with image_url, price, and brand.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        product_info = {
            'image_url': None,
            'price': None,
            'brand': None
        }
        
        # Extract brand from JSON-LD or fallback methods
        json_ld = soup.find('script', type='application/ld+json')
        if json_ld:
            try:
                data = json.loads(json_ld.string)
                if isinstance(data, list):
                    data = data[0]
                if 'brand' in data:
                    product_info['brand'] = data['brand'].get('name', data['brand']) if isinstance(data['brand'], dict) else data['brand']
            except (json.JSONDecodeError, KeyError, IndexError):
                pass
        
        # Fallback: Try common brand selectors
        if not product_info['brand']:
            brand_selectors = [
                '[itemprop="brand"]',
                '.product-brand',
                '[data-testid="product-brand"]',
                'meta[property="og:brand"]'
            ]
            for selector in brand_selectors:
                brand_elem = soup.select_one(selector)
                if brand_elem:
                    if brand_elem.name == 'meta':
                        product_info['brand'] = brand_elem.get('content')
                    else:
                        product_info['brand'] = brand_elem.get_text(strip=True)
                    break
            
            # Try to extract brand from URL as last resort
            if not product_info['brand']:
                domain_match = re.search(r'https?://(?:www\.)?([^./]+)', url)
                if domain_match:
                    product_info['brand'] = domain_match.group(1).split('.')[0].title()
        
        # Find price by searching all text for currency patterns
        price_pattern = re.compile(r'[\$£€]\s*\d+[.,]\d{2}')
        all_text_elements = soup.find_all(string=price_pattern)
        
        price_element = None
        if all_text_elements:
            # Get the first occurrence
            price_element = all_text_elements[0].parent
            price_text = all_text_elements[0]
            price_match = price_pattern.search(price_text)
            if price_match:
                product_info['price'] = price_match.group()
        
        # Find image closest to the price element
        if price_element:
            # Search upward in the DOM tree to find a common container
            current = price_element
            max_depth = 10
            depth = 0
            
            while current and depth < max_depth:
                # Look for images within this container
                images = current.find_all('img')
                if images:
                    # Filter out small images (likely icons)
                    valid_images = [
                        img for img in images 
                        if img.get('src') and not any(x in img.get('src', '') for x in ['icon', 'logo', 'sprite'])
                    ]
                    if valid_images:
                        # Get the first valid image
                        img = valid_images[0]
                        product_info['image_url'] = img.get('src') or img.get('data-src') or img.get('data-original')
                        break
                
                current = current.parent
                depth += 1
        
        # Fallback: if no image found near price, get the largest image on page
        if not product_info['image_url']:
            all_images = soup.find_all('img')
            for img in all_images:
                src = img.get('src') or img.get('data-src') or img.get('data-original')
                if src and not any(x in src for x in ['icon', 'logo', 'sprite', 'thumb']):
                    product_info['image_url'] = src
                    break
        
        return product_info
    
    except requests.RequestException as e:
        print(f"Error fetching the URL: {e}")
        return None
    except Exception as e:
        print(f"Error parsing the page: {e}")
        return None

# Example usage
if __name__ == "__main__":
    url = input("Enter product URL: ")
    result = scrape_product(url)
    
    if result:
        print("\n=== Product Information ===")
        print(f"Brand: {result['brand']}")
        print(f"Price: {result['price']}")
        print(f"Image URL: {result['image_url']}")
    else:
        print("Failed to scrape product information.")
