#!/usr/bin/env python3
"""Analyze image and extract text using OCR"""
import os
import base64

img_path = "/root/.hermes/image_cache/img_ae658514bf81.jpg"
print(f"File exists: {os.path.exists(img_path)}")
print(f"File size: {os.path.getsize(img_path)} bytes")

# Check image dimensions using PIL if available
try:
    from PIL import Image
    img = Image.open(img_path)
    print(f"Image format: {img.format}")
    print(f"Image size: {img.size}")
    print(f"Image mode: {img.mode}")
except ImportError:
    print("PIL not available")
except Exception as e:
    print(f"PIL error: {e}")

# Check if tesseract is available
import subprocess
try:
    result = subprocess.run(['tesseract', '--version'], capture_output=True, text=True)
    print(f"\nTesseract available: {result.stdout.strip()}")
except FileNotFoundError:
    print("\nTesseract not available")

# Check if pytesseract is available
try:
    import pytesseract
    print("pytesseract available")
except ImportError:
    print("pytesseract not available")

# Try OCR with available tools
try:
    import pytesseract
    from PIL import Image
    img = Image.open(img_path)
    
    # Try Chinese + English
    text = pytesseract.image_to_string(img, lang='chi_sim+eng')
    print("\n=== OCR Result (Chinese + English) ===")
    print(text)
    
    # Also try with detailed data
    data = pytesseract.image_to_data(img, lang='chi_sim+eng', output_type=pytesseract.Output.DICT)
    print("\n=== OCR Detailed Data ===")
    for i in range(len(data['text'])):
        if data['text'][i].strip():
            print(f"  [{data['block_num'][i]}-{data['par_num'][i]}-{data['line_num'][i]}-{data['word_num'][i]}] "
                  f"text='{data['text'][i]}' conf={data['conf'][i]} "
                  f"bbox=({data['left'][i]},{data['top'][i]},{data['width'][i]},{data['height'][i]})")
except Exception as e:
    print(f"OCR error: {e}")
