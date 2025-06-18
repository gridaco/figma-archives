import click
import os
import json
import requests
import imghdr
import tempfile
from pathlib import Path
from typing import Dict, Optional
from tqdm import tqdm

def fetch_image_fills(file_key: str, token: str) -> Dict:
    """Fetch images from Figma API using file key and access token.
    
    Args:
        file_key: Figma file key
        token: Figma access token
        
    Returns:
        Dict containing the API response with image URLs
        
    Raises:
        requests.RequestException: If the API request fails
    """
    headers = {
        'X-Figma-Token': token
    }
    
    # Get images directly from the images endpoint
    images_url = f'https://api.figma.com/v1/files/{file_key}/images'
    response = requests.get(images_url, headers=headers)
    response.raise_for_status()
    
    return response.json()

def validate_source_params(ctx, param, value):
    if not any([ctx.params.get('response'), ctx.params.get('file_key')]):
        raise click.BadParameter('Either --response or --file-key must be provided')
    return value

@click.group()
def cli():
    """Main CLI group"""
    pass

@cli.group()
def archive():
    """Archive related commands"""
    pass

@archive.command()
@click.option('--output', '-o', type=click.Path(), help='Output directory for archived images')
@click.option('--response', type=click.Path(), help='Path to response.json containing Figma API response')
@click.option('--file-key', help='Figma file key')
@click.option('--token', 
    help='Figma access token (defaults to FIGMA_PERSONAL_ACCESS_TOKEN environment variable)',
    default=lambda: os.environ.get('FIGMA_PERSONAL_ACCESS_TOKEN'),
    callback=validate_source_params)
@click.option('--no-extension', is_flag=True, help='Save files without extensions')
def image(output, response, file_key, token, no_extension):
    """Archive an image file with optional Figma metadata. 
    Requires either --response or --file-key."""
    
    if not output:
        # Create a temporary directory
        output_dir = Path(tempfile.mkdtemp(prefix='figd_archive_'))
        click.echo(f"No output directory specified. Using temporary directory: {output_dir}")
    else:
        output_dir = Path(output)
    
    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if response:
        click.echo(f"Using Figma response data from {response}")
        try:
            with open(response, 'r') as f:
                response_data = json.load(f)
        except json.JSONDecodeError:
            click.echo("Invalid JSON in response file", err=True)
            return
        except IOError as e:
            click.echo(f"Error reading response file: {str(e)}", err=True)
            return
    elif file_key:
        click.echo(f"Fetching images from Figma file: {file_key}")
        try:
            response_data = fetch_image_fills(file_key, token)
        except requests.RequestException as e:
            click.echo(f"Error fetching images from Figma: {str(e)}", err=True)
            return
    
    if not response_data.get('error') and response_data.get('status') == 200:
        images = response_data.get('meta', {}).get('images', {})
        
        if not images:
            click.echo("No images found in the response")
            return
            
        click.echo(f"Found {len(images)} images to download")
        
        with tqdm(total=len(images), desc="Downloading images") as pbar:
            for image_id, image_url in images.items():
                try:
                    # Download the image
                    response = requests.get(image_url)
                    response.raise_for_status()
                    
                    # Detect image type from content
                    image_type = imghdr.what(None, response.content)
                    file_ext = '' if no_extension else (f'.{image_type}' if image_type else '.bin')
                    
                    # Save the image
                    output_path = output_dir / f"{image_id}{file_ext}"
                    with open(output_path, 'wb') as f:
                        f.write(response.content)
                    
                    pbar.update(1)
                    
                except requests.RequestException as e:
                    click.echo(f"\nError downloading image {image_id}: {str(e)}", err=True)
                except IOError as e:
                    click.echo(f"\nError saving image {image_id}: {str(e)}", err=True)
        
        click.echo(f"\nAll images have been saved to: {output_dir}")
    else:
        click.echo("Invalid response format or error in response", err=True)

if __name__ == '__main__':
    cli()
