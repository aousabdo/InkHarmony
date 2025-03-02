"""
Stability AI integration for InkHarmony.
Handles communication with Stability AI for image generation.
"""
import os
import logging
import time
import base64
import io
import json
import sys
from typing import Dict, List, Any, Optional, Union, BinaryIO
from dataclasses import dataclass

# Add the project root directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
from config import STABILITY_API_KEY, STABILITY_MODEL, STABILITY_IMAGE_FORMAT

# Set up logging
logger = logging.getLogger(__name__)

class StabilityAPIError(Exception):
    """Exception raised for Stability AI API errors."""
    pass


@dataclass
class ImageGenerationOptions:
    """Options for Stability AI image generation."""
    model: str = STABILITY_MODEL
    prompt: str = ""
    negative_prompt: str = ""
    width: int = 1024
    height: int = 1024
    steps: int = 30
    cfg_scale: float = 7.0
    samples: int = 1
    seed: Optional[int] = None
    style_preset: Optional[str] = None
    output_format: str = STABILITY_IMAGE_FORMAT


class StabilityAPI:
    """Interface to Stability AI's API."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Stability AI client.
        
        Args:
            api_key: Stability AI API key (default: from config)
        """
        self.api_key = api_key or STABILITY_API_KEY
        if not self.api_key:
            raise ValueError("Stability AI API key is required")
            
        self.api_host = "https://api.stability.ai"
    
    def generate_image(self, options: ImageGenerationOptions) -> bytes:
        """
        Generate an image using Stability AI.
        
        Args:
            options: Image generation options
            
        Returns:
            Generated image as bytes
        
        Raises:
            StabilityAPIError: If the API call fails
        """
        endpoint = f"{self.api_host}/v1/generation/{options.model}/text-to-image"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        payload = {
            "text_prompts": [
                {
                    "text": options.prompt,
                    "weight": 1.0
                }
            ],
            "cfg_scale": options.cfg_scale,
            "height": options.height,
            "width": options.width,
            "steps": options.steps,
            "samples": options.samples
        }
        
        # Add optional parameters if provided
        if options.negative_prompt:
            payload["text_prompts"].append({
                "text": options.negative_prompt,
                "weight": -1.0
            })
            
        if options.seed is not None:
            payload["seed"] = options.seed
            
        if options.style_preset:
            payload["style_preset"] = options.style_preset
        
        try:
            response = requests.post(
                endpoint,
                headers=headers,
                json=payload
            )
            
            if response.status_code != 200:
                error_detail = response.text
                try:
                    error_json = response.json()
                    if "message" in error_json:
                        error_detail = error_json["message"]
                except Exception:
                    pass
                    
                raise StabilityAPIError(f"API returned {response.status_code}: {error_detail}")
                
            response_json = response.json()
            
            # Extract the generated image
            if not response_json.get("artifacts"):
                raise StabilityAPIError("No artifacts found in response")
                
            image_data_b64 = response_json["artifacts"][0]["base64"]
            image_bytes = base64.b64decode(image_data_b64)
            
            return image_bytes
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {str(e)}")
            raise StabilityAPIError(f"Request error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            raise StabilityAPIError(f"Unexpected error: {str(e)}")
    
    def generate_cover_image(self, prompt: str, book_genre: str, 
                           portrait: bool = True) -> bytes:
        """
        Generate a book cover image.
        
        Args:
            prompt: Description of the cover
            book_genre: Genre of the book
            portrait: Whether to use portrait orientation
            
        Returns:
            Generated cover image as bytes
        """
        # Enhance the prompt for better cover generation
        enhanced_prompt = f"Book cover for {book_genre} book. {prompt}. Professional book cover, high quality, photorealistic, trending on Artstation, award winning, dramatic lighting."
        negative_prompt = "blurry, text, watermark, logo, title, signature, deformed, low quality, distorted, amateur"
        
        # Set dimensions for a typical book cover
        if portrait:
            width, height = 1200, 1800  # 2:3 aspect ratio
        else:
            width, height = 1800, 1200  # 3:2 aspect ratio
        
        options = ImageGenerationOptions(
            prompt=enhanced_prompt,
            negative_prompt=negative_prompt,
            width=width,
            height=height,
            steps=40,  # More steps for higher quality
            cfg_scale=8.0,  # Higher cfg_scale for more prompt adherence
            style_preset="photographic"
        )
        
        return self.generate_image(options)
    
    def generate_with_retry(self, options: ImageGenerationOptions, 
                          max_retries: int = 3, retry_delay: float = 2.0) -> bytes:
        """
        Generate an image with retry logic.
        
        Args:
            options: Image generation options
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries (with exponential backoff)
            
        Returns:
            Generated image as bytes
        
        Raises:
            StabilityAPIError: If all retry attempts fail
        """
        for attempt in range(max_retries):
            try:
                return self.generate_image(options)
            except StabilityAPIError as e:
                logger.warning(f"Retry {attempt + 1}/{max_retries}: {str(e)}")
                
                if attempt < max_retries - 1:
                    # Exponential backoff
                    sleep_time = retry_delay * (2 ** attempt)
                    time.sleep(sleep_time)
                else:
                    # Last attempt failed
                    raise
    
    def save_image(self, image_data: bytes, file_path: str) -> str:
        """
        Save an image to file.
        
        Args:
            image_data: Binary image data
            file_path: Path to save the image
            
        Returns:
            Absolute path to the saved image
        """
        # Ensure directory exists
        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
        
        # Save the image
        with open(file_path, "wb") as f:
            f.write(image_data)
            
        return os.path.abspath(file_path)
    
    def create_variation(self, image_path: str, prompt: str, 
                       options: Optional[ImageGenerationOptions] = None) -> bytes:
        """
        Create a variation of an existing image.
        
        Args:
            image_path: Path to the source image
            prompt: Text prompt to guide the variation
            options: Optional generation options
            
        Returns:
            Generated variation image as bytes
        
        Raises:
            StabilityAPIError: If the API call fails
        """
        if options is None:
            options = ImageGenerationOptions(prompt=prompt)
        else:
            options.prompt = prompt
            
        endpoint = f"{self.api_host}/v1/generation/{options.model}/image-to-image"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json"
        }
        
        # Prepare image
        with open(image_path, "rb") as f:
            image_data = f.read()
            
        # Prepare form data
        form = {
            "init_image": ("image.png", image_data, "image/png"),
            "text_prompts[0][text]": options.prompt,
            "text_prompts[0][weight]": "1.0",
            "cfg_scale": str(options.cfg_scale),
            "steps": str(options.steps),
            "samples": str(options.samples)
        }
        
        # Add negative prompt if provided
        if options.negative_prompt:
            form["text_prompts[1][text]"] = options.negative_prompt
            form["text_prompts[1][weight]"] = "-1.0"
            
        try:
            response = requests.post(
                endpoint,
                headers=headers,
                files=form
            )
            
            if response.status_code != 200:
                error_detail = response.text
                try:
                    error_json = response.json()
                    if "message" in error_json:
                        error_detail = error_json["message"]
                except Exception:
                    pass
                    
                raise StabilityAPIError(f"API returned {response.status_code}: {error_detail}")
                
            response_json = response.json()
            
            # Extract the generated image
            if not response_json.get("artifacts"):
                raise StabilityAPIError("No artifacts found in response")
                
            image_data_b64 = response_json["artifacts"][0]["base64"]
            image_bytes = base64.b64decode(image_data_b64)
            
            return image_bytes
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {str(e)}")
            raise StabilityAPIError(f"Request error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            raise StabilityAPIError(f"Unexpected error: {str(e)}")


# Global Stability API instance - initialize lazily when needed
def get_stability_api():
    """Get or create a StabilityAPI instance only when needed and if the API key is available."""
    if not STABILITY_API_KEY:
        logger.warning("No Stability API key available. Image generation will not work.")
        return None
        
    try:
        return StabilityAPI()
    except ValueError as e:
        logger.warning(f"Failed to initialize StabilityAPI: {str(e)}")
        return None
        
# Replace direct global instance with a function
stability_api = None  # Remove immediate instantiation