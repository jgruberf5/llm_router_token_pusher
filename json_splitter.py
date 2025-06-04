#!/usr/bin/env python3
import json
import os
import sys
from typing import Dict, List, Any, Union

def get_file_size_mb(filepath: str) -> float:
    """Get file size in megabytes."""
    return os.path.getsize(filepath) / (1024 * 1024)

def estimate_json_size_mb(data: Any) -> float:
    """Estimate the size of JSON data in megabytes when serialized."""
    json_str = json.dumps(data, separators=(',', ':'))
    return len(json_str.encode('utf-8')) / (1024 * 1024)

def split_json_array(data: List[Any], target_size_mb: float = 50) -> List[List[Any]]:
    """Split a JSON array into chunks of approximately target_size_mb."""
    chunks = []
    current_chunk = []
    current_size = 0
    
    # Account for array brackets and commas in size estimation
    base_overhead = 0.000002  # ~2 bytes for []
    
    for item in data:
        item_size = estimate_json_size_mb(item)
        comma_overhead = 0.000001 if current_chunk else 0  # ~1 byte for comma
        
        # Check if adding this item would exceed the target size
        if current_chunk and (current_size + item_size + comma_overhead + base_overhead) > target_size_mb:
            chunks.append(current_chunk)
            current_chunk = [item]
            current_size = item_size
        else:
            current_chunk.append(item)
            current_size += item_size + comma_overhead
    
    # Add the last chunk if it has items
    if current_chunk:
        chunks.append(current_chunk)
    
    return chunks

def split_json_object(data: Dict[str, Any], target_size_mb: float = 50) -> List[Dict[str, Any]]:
    """Split a JSON object by distributing key-value pairs across chunks."""
    chunks = []
    current_chunk = {}
    current_size = 0
    
    # Account for object braces and commas
    base_overhead = 0.000002  # ~2 bytes for {}
    
    for key, value in data.items():
        # Estimate size of this key-value pair
        pair_size = estimate_json_size_mb({key: value})
        comma_overhead = 0.000001 if current_chunk else 0  # ~1 byte for comma
        
        # Check if adding this pair would exceed the target size
        if current_chunk and (current_size + pair_size + comma_overhead + base_overhead) > target_size_mb:
            chunks.append(current_chunk)
            current_chunk = {key: value}
            current_size = pair_size
        else:
            current_chunk[key] = value
            current_size += pair_size + comma_overhead
    
    # Add the last chunk if it has items
    if current_chunk:
        chunks.append(current_chunk)
    
    return chunks

def write_json_chunk(data: Any, output_path: str, indent: int = None) -> None:
    """Write a JSON chunk to file."""
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=indent)

def split_large_json(input_file: str, target_size_mb: float = 50, output_dir: str = None, indent: int = None) -> List[str]:
    """
    Split a large JSON file into smaller files of approximately target_size_mb.
    
    Args:
        input_file: Path to the input JSON file
        target_size_mb: Target size for each output file in megabytes (default: 50)
        output_dir: Directory to save output files (default: same as input file)
        indent: JSON indentation for output files (default: None for compact)
    
    Returns:
        List of output file paths
    """
    
    # Validate input file
    if not os.path.exists(input_file):
        raise FileNotFoundError(f"Input file not found: {input_file}")
    
    # Set up output directory
    if output_dir is None:
        output_dir = os.path.dirname(os.path.abspath(input_file))
    os.makedirs(output_dir, exist_ok=True)
    
    # Get base filename for output files
    base_name = os.path.splitext(os.path.basename(input_file))[0]
    
    print(f"Reading JSON file: {input_file}")
    print(f"Original file size: {get_file_size_mb(input_file):.2f} MB")
    
    # Load the JSON data
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON file: {e}")
    
    # Determine how to split based on data type
    if isinstance(data, list):
        print(f"Splitting JSON array with {len(data)} items...")
        chunks = split_json_array(data, target_size_mb)
    elif isinstance(data, dict):
        print(f"Splitting JSON object with {len(data)} keys...")
        chunks = split_json_object(data, target_size_mb)
    else:
        # For primitive types, just write as-is (won't be split)
        print("JSON contains primitive data type, creating single output file...")
        chunks = [data]
    
    # Write chunks to separate files
    output_files = []
    for i, chunk in enumerate(chunks, 1):
        output_file = os.path.join(output_dir, f"{base_name}_part_{i:03d}.json")
        write_json_chunk(chunk, output_file, indent)
        
        chunk_size = get_file_size_mb(output_file)
        print(f"Created: {output_file} ({chunk_size:.2f} MB)")
        output_files.append(output_file)
    
    print(f"\nSplit complete! Created {len(output_files)} files.")
    print(f"Total output size: {sum(get_file_size_mb(f) for f in output_files):.2f} MB")
    
    return output_files

def main():
    """Command line interface for the JSON splitter."""
    if len(sys.argv) < 2:
        print("Usage: python json_splitter.py <input_file> [target_size_mb] [output_dir]")
        print("Example: python json_splitter.py large_data.json 50 ./output")
        sys.exit(1)
    
    input_file = sys.argv[1]
    target_size_mb = float(sys.argv[2]) if len(sys.argv) > 2 else 50.0
    output_dir = sys.argv[3] if len(sys.argv) > 3 else None
    
    try:
        output_files = split_large_json(input_file, target_size_mb, output_dir, indent=2)
        print(f"\nOutput files:")
        for file in output_files:
            print(f"  - {file}")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()