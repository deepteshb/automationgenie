"""
Web Screenshot Task

This task allows taking screenshots of web pages using Selenium WebDriver.
Supports various browsers and can wait for elements to load before taking screenshots.
"""

import os
import time
from pathlib import Path
from typing import Dict, Any, Optional

from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.edge.options import Options as EdgeOptions
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager
from webdriver_manager.microsoft import EdgeChromiumDriverManager
from PIL import Image

from .base import Task, TaskExecutionError


class WebScreenshotTask(Task):
    """
    Task for taking screenshots of web pages.
    
    Configuration parameters:
    - url: The URL to visit and screenshot
    - output_path: Where to save the screenshot (optional, defaults to screenshots/)
    - browser: Browser to use (chrome, firefox, edge) - defaults to chrome
    - headless: Whether to run browser in headless mode (default: True)
    - wait_for_element: CSS selector to wait for before taking screenshot (optional)
    - wait_timeout: Timeout for waiting for element (default: 30 seconds)
    - window_size: Browser window size as "widthxheight" (default: "1920x1080")
    - delay: Additional delay before taking screenshot (default: 2 seconds)
    - full_page: Whether to take full page screenshot (default: True)
    """
    
    task_type = "web_screenshot"
    description = "Take screenshots of web pages using Selenium WebDriver"
    
    def __init__(self):
        super().__init__()
        self.driver = None
    
    def validate_config(self, config: Dict[str, Any]) -> None:
        """Validate the task configuration."""
        required_params = ['url']
        for param in required_params:
            if param not in config:
                raise TaskExecutionError(f"Missing required parameter: {param}")
        
        if not config['url'].startswith(('http://', 'https://')):
            raise TaskExecutionError("URL must start with http:// or https://")
    
    def execute(self, config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the web screenshot task."""
        try:
            url = config['url']
            output_path = config.get('output_path', 'screenshots')
            browser = config.get('browser', 'chrome').lower()
            headless = config.get('headless', True)
            wait_for_element = config.get('wait_for_element')
            wait_timeout = config.get('wait_timeout', 30)
            window_size = config.get('window_size', '1920x1080')
            delay = config.get('delay', 2)
            full_page = config.get('full_page', True)
            pre_screenshot_script = config.get('pre_screenshot_script')
            
            # Create output directory
            Path(output_path).mkdir(parents=True, exist_ok=True)
            
            # Initialize WebDriver
            self.driver = self._create_driver(browser, headless, window_size)
            
            # Navigate to URL
            self.logger.info(f"Navigating to URL: {url}")
            self.driver.get(url)
            
            # Wait for element if specified
            if wait_for_element:
                self.logger.info(f"Waiting for element: {wait_for_element}")
                WebDriverWait(self.driver, wait_timeout).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, wait_for_element))
                )
            
            # Execute custom JavaScript if provided
            if pre_screenshot_script:
                self.logger.info("Executing pre-screenshot JavaScript")
                # Replace environment variables in the script
                script = pre_screenshot_script
                for key, value in os.environ.items():
                    script = script.replace(f'${{{key}}}', value)
                
                try:
                    self.driver.execute_script(script)
                    # Wait a bit after script execution
                    time.sleep(2)
                except Exception as e:
                    self.logger.warning(f"JavaScript execution failed: {e}")
            
            # Additional delay
            if delay > 0:
                self.logger.info(f"Waiting {delay} seconds before taking screenshot")
                time.sleep(delay)
            
            # Take screenshot
            timestamp = int(time.time())
            filename = f"screenshot_{timestamp}.png"
            filepath = os.path.join(output_path, filename)
            
            if full_page:
                self._take_full_page_screenshot(filepath)
            else:
                self.driver.save_screenshot(filepath)
            
            self.logger.info(f"Screenshot saved to: {filepath}")
            
            # Get page info
            page_info = {
                'title': self.driver.title,
                'url': self.driver.current_url,
                'screenshot_path': filepath
            }
            
            return {
                'success': True,
                'screenshot_path': filepath,
                'page_info': page_info
            }
            
        except Exception as e:
            raise TaskExecutionError(f"Failed to take web screenshot: {str(e)}")
        finally:
            if self.driver:
                self.driver.quit()
    
    def _create_driver(self, browser: str, headless: bool, window_size: str) -> webdriver.Remote:
        """Create and configure WebDriver instance."""
        width, height = map(int, window_size.split('x'))
        
        if browser == 'chrome':
            options = ChromeOptions()
            if headless:
                options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument(f'--window-size={width},{height}')
            
            service = ChromeService(ChromeDriverManager().install())
            return webdriver.Chrome(service=service, options=options)
            
        elif browser == 'firefox':
            options = FirefoxOptions()
            if headless:
                options.add_argument('--headless')
            options.add_argument(f'--width={width}')
            options.add_argument(f'--height={height}')
            
            service = FirefoxService(GeckoDriverManager().install())
            return webdriver.Firefox(service=service, options=options)
            
        elif browser == 'edge':
            options = EdgeOptions()
            if headless:
                options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument(f'--window-size={width},{height}')
            
            service = EdgeService(EdgeChromiumDriverManager().install())
            return webdriver.Edge(service=service, options=options)
            
        else:
            raise TaskExecutionError(f"Unsupported browser: {browser}")
    
    def _take_full_page_screenshot(self, filepath: str) -> None:
        """Take a full page screenshot by scrolling and stitching."""
        # Get page dimensions
        total_height = self.driver.execute_script("return document.body.scrollHeight")
        viewport_height = self.driver.execute_script("return window.innerHeight")
        viewport_width = self.driver.execute_script("return window.innerWidth")
        
        # Create a canvas for the full page
        full_screenshot = Image.new('RGB', (viewport_width, total_height))
        
        # Scroll and capture each viewport
        offset = 0
        while offset < total_height:
            # Scroll to position
            self.driver.execute_script(f"window.scrollTo(0, {offset});")
            time.sleep(0.5)  # Wait for scroll to complete
            
            # Take screenshot of current viewport
            temp_screenshot = f"temp_screenshot_{offset}.png"
            self.driver.save_screenshot(temp_screenshot)
            
            # Open and crop to viewport
            with Image.open(temp_screenshot) as img:
                # Crop to viewport size
                viewport_img = img.crop((0, 0, viewport_width, min(viewport_height, total_height - offset)))
                # Paste onto full screenshot
                full_screenshot.paste(viewport_img, (0, offset))
            
            # Clean up temp file
            os.remove(temp_screenshot)
            
            offset += viewport_height
        
        # Save full screenshot
        full_screenshot.save(filepath)
        full_screenshot.close()
