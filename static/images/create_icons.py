#!/usr/bin/env python3
"""
Simple script to create PWA icons for the Criminology Management System
This creates basic PNG icons that can be used for PWA functionality
"""

from PIL import Image, ImageDraw, ImageFont
import os

def create_icon(size, filename):
    """Create a simple icon with the specified size"""
    # Create image with transparent background
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Calculate dimensions
    margin = size // 8
    center_x, center_y = size // 2, size // 2
    
    # Background circle with gradient effect
    bg_color = (30, 60, 114)  # #1e3c72
    draw.ellipse([margin, margin, size-margin, size-margin], fill=bg_color, outline=(42, 82, 152, 255), width=size//32)
    
    # Draw shield shape
    shield_width = size // 3
    shield_height = size // 2
    shield_x = center_x - shield_width // 2
    shield_y = center_y - shield_height // 2
    
    # Shield points
    shield_points = [
        (shield_x, shield_y),
        (shield_x + shield_width, shield_y),
        (shield_x + shield_width, shield_y + shield_height - shield_height//4),
        (center_x, shield_y + shield_height),
        (shield_x, shield_y + shield_height - shield_height//4)
    ]
    
    # Draw shield
    shield_color = (255, 215, 0)  # Gold
    draw.polygon(shield_points, fill=shield_color, outline=(255, 255, 255, 255), width=max(1, size//64))
    
    # Draw scale of justice
    scale_size = size // 6
    scale_x = center_x
    scale_y = center_y + size // 8
    
    # Scale base
    draw.line([scale_x - scale_size, scale_y, scale_x + scale_size, scale_y], fill=(255, 255, 255, 255), width=max(1, size//32))
    draw.line([scale_x, scale_y, scale_x, scale_y + scale_size//2], fill=(255, 255, 255, 255), width=max(1, size//32))
    
    # Scale pans
    pan_size = scale_size // 3
    draw.ellipse([scale_x - scale_size//2 - pan_size//2, scale_y - pan_size//2, 
                  scale_x - scale_size//2 + pan_size//2, scale_y + pan_size//2], 
                 fill=(255, 255, 255, 200), outline=(255, 255, 255, 255), width=1)
    draw.ellipse([scale_x + scale_size//2 - pan_size//2, scale_y - pan_size//2, 
                  scale_x + scale_size//2 + pan_size//2, scale_y + pan_size//2], 
                 fill=(255, 255, 255, 200), outline=(255, 255, 255, 255), width=1)
    
    # Scale strings
    draw.line([scale_x - scale_size//2, scale_y - pan_size//2, scale_x - scale_size//2, scale_y], 
              fill=(255, 255, 255, 255), width=max(1, size//64))
    draw.line([scale_x + scale_size//2, scale_y - pan_size//2, scale_x + scale_size//2, scale_y], 
              fill=(255, 255, 255, 255), width=max(1, size//64))
    
    # Add text for larger icons
    if size >= 256:
        try:
            # Try to use a system font
            font_size = size // 16
            font = ImageFont.truetype("arial.ttf", font_size)
        except:
            # Fallback to default font
            font = ImageFont.load_default()
        
        text = "CRIM"
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        text_x = center_x - text_width // 2
        text_y = center_y + shield_height // 2 + size // 16
        
        draw.text((text_x, text_y), text, fill=(255, 255, 255, 255), font=font)
    
    # Save the image
    img.save(filename, 'PNG')
    print(f"Created icon: {filename} ({size}x{size})")

def main():
    """Create both required icon sizes"""
    # Ensure we're in the right directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    # Create 192x192 icon
    create_icon(192, 'icon-192x192.png')
    
    # Create 512x512 icon
    create_icon(512, 'icon-512x512.png')
    
    print("\nPWA icons created successfully!")
    print("You can now use these icons in your Progressive Web App.")

if __name__ == "__main__":
    main()
