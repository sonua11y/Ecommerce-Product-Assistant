import csv
import time
import re
import os
from bs4 import BeautifulSoup
import undetected_chromedriver as uc  # used locally; server uses system Chromium with Selenium
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import InvalidSessionIdException, WebDriverException
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService

class FlipkartScraper:
    def __init__(self, output_dir="data"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def _create_driver(self):
        """Create a Chrome driver.
        - Always use system Chrome on server environments (Render, Streamlit Cloud)
        - Use undetected-chromedriver only for local development
        """
        # Check if we're on a server environment
        is_server = os.getenv("RENDER") or os.getenv("STREAMLIT_SHARING") or os.getenv("CHROME_PATH")
        
        if is_server:
            # Use system Chrome for server environments
            options = ChromeOptions()
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-gpu")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_argument("--headless=new")
            options.add_argument("--disable-extensions")
            options.add_argument("--disable-plugins")
            options.add_argument("--disable-images")
            
            # Try different Chrome paths
            chrome_paths = [
                os.getenv("CHROME_PATH"),
                os.getenv("GOOGLE_CHROME_BIN"),
                "/usr/bin/chromium-browser",
                "/usr/bin/chromium",
                "/usr/bin/google-chrome",
                "/usr/bin/google-chrome-stable"
            ]
            
            chrome_path = None
            for path in chrome_paths:
                if path and os.path.exists(path):
                    chrome_path = path
                    break
            
            if chrome_path:
                options.binary_location = chrome_path
            
            chromedriver_paths = [
                os.getenv("CHROMEDRIVER_PATH"),
                "/usr/bin/chromedriver",
                "/usr/local/bin/chromedriver"
            ]
            
            chromedriver_path = None
            for path in chromedriver_paths:
                if path and os.path.exists(path):
                    chromedriver_path = path
                    break
            
            if chromedriver_path:
                service = ChromeService(executable_path=chromedriver_path)
            else:
                service = ChromeService()  # Let Selenium find it
            
            from selenium import webdriver
            return webdriver.Chrome(service=service, options=options)
        else:
            # Local development - use undetected-chromedriver
            try:
                options = uc.ChromeOptions()
                options.add_argument("--no-sandbox")
                options.add_argument("--disable-gpu")
                options.add_argument("--disable-dev-shm-usage")
                options.add_argument("--disable-blink-features=AutomationControlled")
                options.add_argument("--start-maximized")
                return uc.Chrome(options=options, use_subprocess=True)
            except Exception:
                # Fallback to regular Selenium if UC fails
                options = ChromeOptions()
                options.add_argument("--no-sandbox")
                options.add_argument("--disable-gpu")
                options.add_argument("--disable-dev-shm-usage")
                options.add_argument("--disable-blink-features=AutomationControlled")
                from selenium import webdriver
                return webdriver.Chrome(options=options)

    def get_top_reviews(self,product_url,count=2):
        """Get the top reviews for a product.
        """
        driver = self._create_driver()

        if not product_url.startswith("http"):
            driver.quit()
            return "No reviews found"

        try:
            driver.get(product_url)
            time.sleep(4)
            try:
                driver.find_element(By.XPATH, "//button[contains(text(), '✕')]").click()
                time.sleep(1)
            except Exception as e:
                print(f"Error occurred while closing popup: {e}")

            for _ in range(4):
                ActionChains(driver).send_keys(Keys.END).perform()
                time.sleep(1.5)

            soup = BeautifulSoup(driver.page_source, "html.parser")
            review_blocks = soup.select("div._27M-vq, div.col.EPCmJX, div._6K-7Co")
            seen = set()
            reviews = []

            for block in review_blocks:
                text = block.get_text(separator=" ", strip=True)
                if text and text not in seen:
                    reviews.append(text)
                    seen.add(text)
                if len(reviews) >= count:
                    break
        except Exception:
            reviews = []

        driver.quit()
        return " || ".join(reviews) if reviews else "No reviews found"
    
    def scrape_flipkart_products(self, query, max_products=1, review_count=2):
        """Scrape Flipkart products based on a search query.
        """
        def _run_once():
            driver = self._create_driver()
            try:
                search_url = f"https://www.flipkart.com/search?q={query.replace(' ', '+')}"
                driver.get(search_url)
                time.sleep(4)

                try:
                    driver.find_element(By.XPATH, "//button[contains(text(), '✕')]").click()
                except Exception as e:
                    print(f"Error occurred while closing popup: {e}")

                time.sleep(2)
                products = []

                items = driver.find_elements(By.CSS_SELECTOR, "div[data-id]")[:max_products]
                for item in items:
                    try:
                        # Title selectors fallback
                        title = ""
                        for sel in ["div.KzDlHZ", "a.IRpwTa", "a.s1Q9rs", "div._4rR01T"]:
                            try:
                                title = item.find_element(By.CSS_SELECTOR, sel).text.strip()
                                if title:
                                    break
                            except Exception:
                                pass

                        # Price selectors fallback
                        price = ""
                        for sel in ["div.Nx9bqj", "div._30jeq3", "div._25b18c > div._30jeq3"]:
                            try:
                                price = item.find_element(By.CSS_SELECTOR, sel).text.strip()
                                if price:
                                    break
                            except Exception:
                                pass

                        # Rating selectors fallback
                        rating = ""
                        for sel in ["div.XQDdHH", "div._3LWZlK", "span._1lRcqv"]:
                            try:
                                rating = item.find_element(By.CSS_SELECTOR, sel).text.strip()
                                if rating:
                                    break
                            except Exception:
                                pass

                        # Reviews count fallback
                        reviews_text = ""
                        for sel in ["span.Wphh3N", "span._2_R_DZ", "span._2_R_DZ > span span"]:
                            try:
                                reviews_text = item.find_element(By.CSS_SELECTOR, sel).text.strip()
                                if reviews_text:
                                    break
                            except Exception:
                                pass
                        match = re.search(r"\d+(,\d+)?(?=\s+Reviews)", reviews_text)
                        total_reviews = match.group(0) if match else "N/A"

                        link_el = item.find_element(By.CSS_SELECTOR, "a[href*='/p/']")
                        href = link_el.get_attribute("href")
                        product_link = href if href.startswith("http") else "https://www.flipkart.com" + href
                        match = re.findall(r"/p/(itm[0-9A-Za-z]+)", href)
                        product_id = match[0] if match else "N/A"
                    except Exception as e:
                        print(f"Error occurred while processing item: {e}")
                        continue

                    top_reviews = self.get_top_reviews(product_link, count=review_count) if "flipkart.com" in product_link else "Invalid product URL"
                    products.append([product_id, title, rating, total_reviews, price, top_reviews])

                return products
            finally:
                try:
                    driver.quit()
                except Exception:
                    pass

        # Retry once on session drop
        try:
            return _run_once()
        except (InvalidSessionIdException, WebDriverException):
            time.sleep(2)
            return _run_once()
    
    def save_to_csv(self, data, filename="product_reviews.csv"):
        """Save the scraped product reviews to a CSV file."""
        if os.path.isabs(filename):
            path = filename
        elif os.path.dirname(filename):  # filename includes subfolder like 'data/product_reviews.csv'
            path = filename
            os.makedirs(os.path.dirname(path), exist_ok=True)
        else:
            # plain filename like 'output.csv'
            path = os.path.join(self.output_dir, filename)

        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["product_id", "product_title", "rating", "total_reviews", "price", "top_reviews"])
            writer.writerows(data)
        