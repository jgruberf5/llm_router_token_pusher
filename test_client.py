#!/usr/bin/env python3
import argparse
import os
import sys
import uuid

import socket
import json

def send_request(host, port, apikey, content):
    path = '/v1/chat/completions'    
    payload = {
        "model": "",
        "messages": [
            {"role": "user", "content": content}
        ]
    }
    body = json.dumps(payload)
    request = (
        f"POST {path} HTTP/1.1\r\n"
        f"Host: {host}:{port}\r\n"
        f"Authorization: Bearer {apikey}\r\n"
        f"Content-Type: application/json\r\n"
        f"Content-Length: {len(body)}\r\n"
        f"Connection: close\r\n"
        f"\r\n"
        f"{body}"
    )

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    # sock.bind((local_ip, local_port))
    sock.connect((host, port))
    sock.sendall(request.encode())
    response = b''
    while True:
        data = sock.recv(4096)
        if not data:
            break
        response += data

    sock.close()
    return response.decode(errors='replace')


def read_after_first_empty_line(text: str, strip_result: bool = True) -> str:
    """
    Read a string and return only the content after the first empty line.
    
    Args:
        text (str): The input string to process
        strip_result (bool): Whether to strip leading/trailing whitespace from result
    
    Returns:
        str: The content after the first empty line, or empty string if no empty line found
    
    Examples:
        >>> text = "Header line\\nAnother header\\n\\nThis is the content\\nMore content"
        >>> read_after_first_empty_line(text)
        'This is the content\\nMore content'
        
        >>> text = "No empty line here\\nJust normal lines"
        >>> read_after_first_empty_line(text)
        ''
    """
    lines = text.split('\n')
    
    # Find the first empty line
    for i, line in enumerate(lines):
        if line.strip() == '':  # Empty line (may contain whitespace)
            # Return everything after this empty line
            remaining_lines = lines[i + 1:]
            result = '\n'.join(remaining_lines)
            return result.strip() if strip_result else result
    
    # No empty line found
    return ''


def read_request_data(file_name, count, offset):
    try:
        queries = []
        with(open(file_name, 'r', encoding='utf-8')) as data_file:
            data = json.load(data_file)
            read_index = 0
            while len(queries) < (count - 1):
                datem = data[read_index]
                read_index += 1
                query = ""
                for conversation in datem['conversations']:
                    if conversation['from'] == 'human':
                        query = conversation['value'].replace('\n','\\n')
                        if len(query) > 2:
                            break
                if len(query) > 2:
                    queries.append(query)
        return queries
    except Exception as e:
        print(f"✗ Error: {e}")
        return []


def main():
    # Create argument parser
    parser = argparse.ArgumentParser(description='Process a file with various options')
    
    # Add optional arguments
    parser.add_argument('--host', type=str, help='ingress Gateway VIP', default='192.0.2.133')
    parser.add_argument('--port', type=int, help='ingress Gateway VIP port', default=8000)
    parser.add_argument('--apikey', type=str, help='API key for authentication', default=uuid.uuid4())
    parser.add_argument('--number-of-requests', type=int, default=1, 
                       help='Number of requests to make (default: 1)')
    parser.add_argument('--show-tokens', action='store_true', 
                       help='Show token information')
    parser.add_argument('--show-output', action='store_true', 
                       help='Show output information')
    
    # Add required positional argument for filename
    parser.add_argument('filename', help='Path to the input file')
    
    # Parse arguments
    args = parser.parse_args()
    
    # Check if file exists
    if not os.path.exists(args.filename):
        print(f"Error: File '{args.filename}' does not exist.", file=sys.stderr)
        sys.exit(1)
    
    if not os.path.isfile(args.filename):
        print(f"Error: '{args.filename}' is not a regular file.", file=sys.stderr)
        sys.exit(1)
    
    f = os.path.basename(args.filename)
    offset_file_name = f".request_offsets_{f}"
    offset = 0
    if not os.path.isfile(offset_file_name):
        with(open(offset_file_name, 'w', encoding='utf-8')) as offset_file:
            offset_file.write(str(args.number_of_requests))
    else:
        with(open(offset_file_name, 'r', encoding='utf-8')) as offset_file:
            offset = int(offset_file.read())
        with(open(offset_file_name, 'w+', encoding='utf-8')) as offset_file:
            new_offset = offset+args.number_of_requests
            offset_file.write(str(new_offset))

    queries = read_request_data(args.filename, args.number_of_requests, offset)
    
    print("\n\n")
    print(f"+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
    print(f"+ starting token tester for {args.apikey}")
    print(f"+ testing {len(queries) + 1} prompts")
    print(f"+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
    print("\n\n")

    for index, query in enumerate(queries):
        response = send_request(args.host, args.port, args.apikey, query)
        if args.show_output:
            print(f"+++++++++++++ start response {index+1} of {args.number_of_requests} +++++++++++++")
            print(response)
            print(f"+++++++++++++ end response {index+1} of {args.number_of_requests} +++++++++++++")
        elif args.show_tokens:
            try:
                data = json.loads(read_after_first_empty_line(response))
                msg = f" request {index+1} of {args.number_of_requests}"
                standard_message = False
                if data['object'] == 'error':
                    msg = f" {msg} query: {query} error: {data['message']}"
                else:
                    if 'model' in data:
                        standard_message = True
                        msg = f" {msg} used model: {data['model']}"
                    if 'usage' in data:
                        standard_message = True
                        msg = f"{msg} input tokens: {data['usage']['prompt_tokens']} output tokens: {data['usage']['completion_tokens']}"
                    if not standard_message:
                        msg = f"{msg} data: {data}"
                print(msg)
            except Exception as e:
                print(f"error in response {index+1} of {args.number_of_requests} - Error: {response}")
                if 'Access to LLM is blocked' in response:
                    sys.exit(1)


if __name__ == "__main__":
    main()
