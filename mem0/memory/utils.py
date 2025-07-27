import hashlib
import re
import base64
import requests
import tempfile
import os
import logging

from mem0.configs.prompts import FACT_RETRIEVAL_PROMPT


def get_fact_retrieval_messages(message, includes=None, excludes=None):
    """
    Generate fact retrieval messages with optional selective memory filtering.

    Args:
        message (str): The input message to process
        includes (str, optional): Include only specific types of memories
        excludes (str, optional): Exclude specific types of memories

    Returns:
        tuple: (system_prompt, user_prompt) for LLM fact extraction
    """
    base_prompt = FACT_RETRIEVAL_PROMPT

    # Add selective memory instructions if provided
    selective_instructions = []

    # Excludes have higher priority than includes
    if excludes:
        selective_instructions.append(f"IMPORTANT: Do NOT extract or store any information related to: {excludes}")

    if includes:
        selective_instructions.append(f"FOCUS: Only extract and store information specifically related to: {includes}")

    # Append selective instructions to the base prompt if any exist
    if selective_instructions:
        base_prompt += "\n\n" + "\n".join(selective_instructions)

    return base_prompt, f"Input:\n{message}"


def parse_messages(messages):
    response = ""
    for msg in messages:
        if msg["role"] == "system":
            response += f"system: {msg['content']}\n"
        if msg["role"] == "user":
            response += f"user: {msg['content']}\n"
        if msg["role"] == "assistant":
            response += f"assistant: {msg['content']}\n"
    return response


def format_entities(entities):
    if not entities:
        return ""

    formatted_lines = []
    for entity in entities:
        simplified = f"{entity['source']} -- {entity['relationship']} -- {entity['destination']}"
        formatted_lines.append(simplified)

    return "\n".join(formatted_lines)


def remove_code_blocks(content: str) -> str:
    """
    Removes enclosing code block markers ```[language] and ``` from a given string.

    Remarks:
    - The function uses a regex pattern to match code blocks that may start with ``` followed by an optional language tag (letters or numbers) and end with ```.
    - If a code block is detected, it returns only the inner content, stripping out the markers.
    - If no code block markers are found, the original content is returned as-is.
    """
    pattern = r"^```[a-zA-Z0-9]*\n([\s\S]*?)\n```$"
    match = re.match(pattern, content.strip())
    return match.group(1).strip() if match else content.strip()


def extract_json(text):
    """
    Extracts JSON content from a string, removing enclosing triple backticks and optional 'json' tag if present.
    If no code block is found, returns the text as-is.
    """
    text = text.strip()
    match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    if match:
        json_str = match.group(1)
    else:
        json_str = text  # assume it's raw JSON
    return json_str


def get_image_description(image_obj, llm, vision_details):
    """
    Get the description of the image
    """

    if isinstance(image_obj, str):
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "A user is providing an image. Provide a high level description of the image and do not include any additional text.",
                    },
                    {"type": "image_url", "image_url": {"url": image_obj, "detail": vision_details}},
                ],
            },
        ]
    else:
        messages = [image_obj]

    response = llm.generate_response(messages=messages)
    return response


def get_document_content(url, doc_type):
    """
    Get the content of a document from URL or Base64 encoded data

    Args:
        url (str): URL or Base64 encoded document data
        doc_type (str): Type of document ('mdx', 'txt', 'pdf')

    Returns:
        str: Extracted text content from the document
    """
    try:
        # Check if it's a Base64 encoded data URL or direct base64 string
        if url.startswith('data:') or not url.startswith(('http://', 'https://')):
            content = decode_base64_content(url)
        else:
            # Download from URL
            content = download_from_url(url)

        # Process content based on document type
        if doc_type.lower() == 'pdf':
            return extract_pdf_text(content)
        else:
            # For MDX/TXT files, extract text content
            return extract_text_content(content)

    except Exception as e:
        logging.error(f"Error processing document {url}: {str(e)}")
        raise Exception(f"Error while processing document {url}: {str(e)}")


def extract_pdf_text(content):
    """
    Extract text content from PDF bytes using PyPDFLoader approach

    Args:
        content (bytes): PDF file content

    Returns:
        str: Extracted text content
    """
    try:
        # Save content to temporary file for PyPDFLoader
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            temp_file.write(content)
            temp_file_path = temp_file.name

        try:
            # Use langchain's PyPDFLoader (similar to embedchain implementation)
            from langchain_community.document_loaders import PyPDFLoader
            loader = PyPDFLoader(temp_file_path)
            pages = loader.load_and_split()

            if not pages:
                raise ValueError("No content found in PDF")

            # Extract text from all pages
            all_text = []
            for page in pages:
                page_content = page.page_content.strip()
                if page_content:
                    all_text.append(page_content)

            return "\n\n".join(all_text)

        finally:
            # Clean up temporary file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)

    except ImportError:
        # Fallback if langchain_community is not available
        logging.warning("langchain_community not available, using basic PDF text extraction")
        return "PDF content extraction requires langchain_community package"
    except Exception as e:
        logging.error(f"Error extracting PDF text: {str(e)}")
        raise Exception(f"Error extracting PDF text: {str(e)}")


def parse_vision_messages(messages, llm=None, vision_details="auto"):
    """
    Parse the vision messages from the messages
    """
    returned_messages = []
    for msg in messages:
        if msg["role"] == "system":
            returned_messages.append(msg)
            continue

        # Handle message content
        if isinstance(msg["content"], list):
            # Multiple image URLs in content
            description = get_image_description(msg, llm, vision_details)
            returned_messages.append({"role": msg["role"], "content": description})
        elif isinstance(msg["content"], dict) and msg["content"].get("type") == "image_url":
            # Single image content
            image_url = msg["content"]["image_url"]["url"]
            try:
                description = get_image_description(image_url, llm, vision_details)
                returned_messages.append({"role": msg["role"], "content": description})
            except Exception as e:
                logging.error(f"Error processing image {image_url}: {str(e)}")
                raise Exception(f"Error while processing image {image_url}: {str(e)}")
        elif isinstance(msg["content"], dict) and msg["content"].get("type") == "mdx_url":
            # MDX/TXT document content
            document_url = msg["content"]["mdx_url"]["url"]
            try:
                document_content = get_document_content(document_url, "mdx")
                returned_messages.append({"role": msg["role"], "content": document_content})
            except Exception as e:
                logging.error(f"Error processing document {document_url}: {str(e)}")
                raise Exception(f"Error while processing document {document_url}: {str(e)}")
        elif isinstance(msg["content"], dict) and msg["content"].get("type") == "pdf_url":
            # PDF document content
            document_url = msg["content"]["pdf_url"]["url"]
            try:
                document_content = get_document_content(document_url, "pdf")
                returned_messages.append({"role": msg["role"], "content": document_content})
            except Exception as e:
                logging.error(f"Error processing PDF document {document_url}: {str(e)}")
                raise Exception(f"Error while processing PDF document {document_url}: {str(e)}")
        else:
            # Regular text content
            returned_messages.append(msg)

    return returned_messages


def process_telemetry_filters(filters):
    """
    Process the telemetry filters
    """
    if filters is None:
        return {}

    encoded_ids = {}
    if "user_id" in filters:
        encoded_ids["user_id"] = hashlib.md5(filters["user_id"].encode()).hexdigest()
    if "agent_id" in filters:
        encoded_ids["agent_id"] = hashlib.md5(filters["agent_id"].encode()).hexdigest()
    if "run_id" in filters:
        encoded_ids["run_id"] = hashlib.md5(filters["run_id"].encode()).hexdigest()

    return list(filters.keys()), encoded_ids


def download_from_url(url, max_size=10*1024*1024):
    """
    Download content from URL with size and timeout controls

    Args:
        url (str): URL to download from
        max_size (int): Maximum file size in bytes (default: 10MB)

    Returns:
        bytes: Downloaded content
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36",
    }

    try:
        response = requests.get(url, headers=headers, timeout=30, stream=True)
        response.raise_for_status()

        # Check content length
        content_length = response.headers.get('content-length')
        if content_length and int(content_length) > max_size:
            raise ValueError(f"File size ({int(content_length)} bytes) exceeds maximum allowed size ({max_size} bytes)")

        # Download with size checking
        content = b''
        for chunk in response.iter_content(chunk_size=8192):
            content += chunk
            if len(content) > max_size:
                raise ValueError(f"File size exceeds maximum allowed size ({max_size} bytes)")

        if not content:
            raise ValueError("Empty file content")

        return content

    except requests.exceptions.RequestException as e:
        logging.error(f"Network error downloading {url}: {str(e)}")
        raise Exception(f"Failed to download from {url}: {str(e)}")
    except Exception as e:
        logging.error(f"Error downloading {url}: {str(e)}")
        raise


def decode_base64_content(base64_str):
    """
    Decode Base64 encoded content with error handling

    Args:
        base64_str (str): Base64 encoded string or data URL

    Returns:
        bytes: Decoded content
    """
    try:
        # Handle data URLs
        if base64_str.startswith('data:'):
            if ';base64,' in base64_str:
                base64_data = base64_str.split(';base64,')[1]
            else:
                raise ValueError("Invalid data URL format - missing base64 encoding")
        else:
            base64_data = base64_str

        # Decode base64
        content = base64.b64decode(base64_data)

        if not content:
            raise ValueError("Empty content after base64 decoding")

        return content

    except Exception as e:
        logging.error(f"Error decoding base64 content: {str(e)}")
        raise Exception(f"Failed to decode base64 content: {str(e)}")


def extract_text_content(content):
    """
    Extract text content from bytes with encoding detection

    Args:
        content (bytes): Raw file content

    Returns:
        str: Extracted text content
    """
    try:
        # Try UTF-8 first
        try:
            text_content = content.decode('utf-8')
        except UnicodeDecodeError:
            # Fallback to UTF-8 with error handling
            text_content = content.decode('utf-8', errors='ignore')
            logging.warning("Used UTF-8 with error handling due to encoding issues")

        # Clean up the text
        text_content = text_content.strip()

        if not text_content:
            raise ValueError("No text content found in document")

        return text_content

    except Exception as e:
        logging.error(f"Error extracting text content: {str(e)}")
        raise Exception(f"Failed to extract text content: {str(e)}")
