from __future__ import annotations

"""Integrated image EXIF/GPS extraction helpers for MxA photos and mapping.
Derived from the user-provided extract_image_metadata.py and adapted for package use.
"""

import os
import sys
import csv
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
from pathlib import Path

def get_gps_coordinates(exif_data):
    """Extract GPS coordinates from EXIF data"""
    if not exif_data:
        return None
    
    gps_info = {}
    for tag, value in exif_data.items():
        tag_name = TAGS.get(tag, tag)
        if tag_name == 'GPSInfo':
            for gps_tag in value:
                gps_tag_name = GPSTAGS.get(gps_tag, gps_tag)
                gps_info[gps_tag_name] = value[gps_tag]
    
    if not gps_info:
        return None
    
    # Convert GPS coordinates to decimal degrees
    def convert_to_degrees(value):
        d, m, s = value
        return d + (m / 60.0) + (s / 3600.0)
    
    try:
        lat = convert_to_degrees(gps_info.get('GPSLatitude', [0, 0, 0]))
        lon = convert_to_degrees(gps_info.get('GPSLongitude', [0, 0, 0]))
        
        # Handle South and West directions
        if gps_info.get('GPSLatitudeRef') == 'S':
            lat = -lat
        if gps_info.get('GPSLongitudeRef') == 'W':
            lon = -lon
        
        return (lat, lon)
    except:
        return None

def extract_image_info(image_path):
    """Extract all available EXIF data from an image"""
    try:
        img = Image.open(image_path)
        info = {
            'filename': os.path.basename(image_path),
            'path': image_path,
            'format': img.format,
            'size': img.size,
            'mode': img.mode,
            'exif': {}
        }
        
        # Extract EXIF data (PNG files may not have EXIF)
        exif_data = None
        try:
            exif_data = img._getexif()
        except:
            pass
        
        if exif_data:
            for tag, value in exif_data.items():
                tag_name = TAGS.get(tag, tag)
                # Convert non-serializable values to strings
                if isinstance(value, bytes):
                    try:
                        value = value.decode('utf-8', errors='ignore')
                    except:
                        value = str(value)
                info['exif'][tag_name] = value
            
            # Extract GPS coordinates
            gps = get_gps_coordinates(exif_data)
            if gps:
                info['gps'] = {
                    'latitude': gps[0],
                    'longitude': gps[1],
                    'latitude_dms': gps_to_dms(gps[0], gps[1])[0],
                    'longitude_dms': gps_to_dms(gps[0], gps[1])[1],
                    'google_maps_url': f"https://www.google.com/maps?q={gps[0]},{gps[1]}"
                }
        
        return info
    except Exception as e:
        return {'filename': os.path.basename(image_path), 'error': str(e)}

def gps_to_dms(lat, lon):
    """Convert decimal degrees to degrees, minutes, seconds"""
    def decimal_to_dms(decimal):
        degrees = int(abs(decimal))
        minutes = int((abs(decimal) - degrees) * 60)
        seconds = (abs(decimal) - degrees - minutes/60) * 3600
        return f"{degrees}°{minutes:02d}'{seconds:.2f}\""
    
    lat_dir = 'N' if lat >= 0 else 'S'
    lon_dir = 'E' if lon >= 0 else 'W'
    
    return (f"{decimal_to_dms(lat)} {lat_dir}", 
            f"{decimal_to_dms(lon)} {lon_dir}")

def clean_string(value):
    """Clean string values for CSV export"""
    if value is None:
        return ''
    if isinstance(value, (int, float)):
        return str(value)
    # Convert to string and handle special characters
    value_str = str(value)
    # Replace newlines and carriage returns
    value_str = value_str.replace('\n', ' ').replace('\r', ' ')
    # Replace commas to avoid CSV issues (optional - CSV will quote them)
    return value_str

def scan_folder(folder_path, extensions=None):
    """Scan folder for image files"""
    if extensions is None:
        extensions = {'.jpg', '.jpeg', '.png', '.tiff', '.tif', '.bmp', '.gif', '.webp'}
    
    image_files = []
    folder = Path(folder_path)
    
    if not folder.exists():
        print(f"Error: Folder '{folder_path}' does not exist")
        return image_files
    
    for file in folder.iterdir():
        if file.is_file() and file.suffix.lower() in extensions:
            image_files.append(str(file))
    
    return sorted(image_files)

def print_info(info):
    """Print image information in a readable format"""
    if 'error' in info:
        print(f"\n❌ {info['filename']}: Error - {info['error']}")
        return
    
    print(f"\n{'='*60}")
    print(f"📷 {info['filename']}")
    print(f"{'='*60}")
    print(f"  Format: {info['format']}")
    print(f"  Dimensions: {info['size'][0]} x {info['size'][1]} pixels")
    print(f"  Mode: {info['mode']}")
    
    if info.get('exif'):
        print(f"\n  📋 EXIF Data:")
        # Print selected EXIF fields
        important_fields = [
            'DateTime', 'DateTimeOriginal', 'DateTimeDigitized',
            'Make', 'Model', 'Software', 'ExposureTime',
            'FNumber', 'ISOSpeedRatings', 'FocalLength'
        ]
        for field in important_fields:
            if field in info['exif']:
                print(f"    {field}: {info['exif'][field]}")
    
    if info.get('gps'):
        print(f"\n  🌍 GPS Coordinates:")
        print(f"    Latitude: {info['gps']['latitude']}°")
        print(f"    Longitude: {info['gps']['longitude']}°")
        print(f"    DMS: {info['gps']['latitude_dms']}, {info['gps']['longitude_dms']}")
        print(f"    Google Maps: {info['gps']['google_maps_url']}")
    
    if info.get('exif') and not info.get('gps'):
        print(f"\n  ℹ️  No GPS coordinates found in EXIF data")

def export_to_csv(images_info, output_file):
    """Export extracted information to CSV file with proper escaping"""
    try:
        # Open file with utf-8 encoding and proper CSV dialect
        with open(output_file, 'w', newline='', encoding='utf-8-sig') as csvfile:
            # Use quoting to handle special characters
            writer = csv.DictWriter(
                csvfile, 
                fieldnames=['filename', 'format', 'width', 'height', 'mode', 
                           'latitude', 'longitude', 'google_maps_url', 
                           'datetime_original', 'camera_make', 'camera_model'],
                quoting=csv.QUOTE_ALL,  # Quote all fields to avoid escaping issues
                escapechar='\\',  # Set escape character
                doublequote=True  # Use double quotes for escaping
            )
            writer.writeheader()
            
            for info in images_info:
                if 'error' in info:
                    continue
                
                # Clean and prepare each field
                row = {
                    'filename': clean_string(info['filename']),
                    'format': clean_string(info['format']),
                    'width': info['size'][0] if info.get('size') else '',
                    'height': info['size'][1] if info.get('size') else '',
                    'mode': clean_string(info.get('mode', '')),
                    'latitude': clean_string(info.get('gps', {}).get('latitude', '')),
                    'longitude': clean_string(info.get('gps', {}).get('longitude', '')),
                    'google_maps_url': clean_string(info.get('gps', {}).get('google_maps_url', '')),
                    'datetime_original': clean_string(info.get('exif', {}).get('DateTimeOriginal', '')),
                    'camera_make': clean_string(info.get('exif', {}).get('Make', '')),
                    'camera_model': clean_string(info.get('exif', {}).get('Model', ''))
                }
                
                try:
                    writer.writerow(row)
                except Exception as e:
                    print(f"  Warning: Could not write row for {info['filename']}: {e}")
                    continue
        
        print(f"\n📊 Exported data to: {output_file}")
        
    except Exception as e:
        print(f"\n❌ Error exporting to CSV: {e}")
        # Fallback: try without CSV module
        try:
            fallback_file = output_file.replace('.csv', '_fallback.txt')
            with open(fallback_file, 'w', encoding='utf-8') as f:
                f.write("filename|format|width|height|mode|latitude|longitude|google_maps_url|datetime_original|camera_make|camera_model\n")
                for info in images_info:
                    if 'error' in info:
                        continue
                    row = f"{info['filename']}|{info['format']}|{info['size'][0]}|{info['size'][1]}|{info.get('mode', '')}|"
                    row += f"{info.get('gps', {}).get('latitude', '')}|{info.get('gps', {}).get('longitude', '')}|"
                    row += f"{info.get('gps', {}).get('google_maps_url', '')}|"
                    row += f"{info.get('exif', {}).get('DateTimeOriginal', '')}|"
                    row += f"{info.get('exif', {}).get('Make', '')}|{info.get('exif', {}).get('Model', '')}\n"
                    f.write(row)
            print(f"  Created pipe-delimited fallback file: {fallback_file}")
        except:
            print("  Could not create fallback file")

def main():
    """Main function"""
    # Get folder path from command line or use current directory
    if len(sys.argv) > 1:
        folder_path = sys.argv[1]
    else:
        folder_path = input("Enter folder path (or press Enter for current directory): ").strip()
        if not folder_path:
            folder_path = "."
    
    # Ask if user wants to export to CSV
    export_choice = input("Export to CSV? (y/n): ").strip().lower()
    export_csv = export_choice == 'y'
    
    print(f"\n📁 Scanning folder: {folder_path}")
    
    # Scan folder for images
    image_files = scan_folder(folder_path)
    
    if not image_files:
        print("No image files found in the specified folder.")
        return
    
    print(f"Found {len(image_files)} image(s)\n")
    
    # Extract information from each image
    all_info = []
    for i, image_path in enumerate(image_files, 1):
        print(f"Processing ({i}/{len(image_files)}): {os.path.basename(image_path)}")
        info = extract_image_info(image_path)
        all_info.append(info)
        print_info(info)
    
    # Export to CSV if requested
    if export_csv and all_info:
        output_file = os.path.join(folder_path, "image_metadata_export.csv")
        export_to_csv(all_info, output_file)
    
    print(f"\n✅ Done! Processed {len(image_files)} image(s)")

if __name__ == "__main__":
    main()