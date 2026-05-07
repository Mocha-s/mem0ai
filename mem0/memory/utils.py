import hashlib
import logging
import re
from typing import Any, Dict, List

from mem0.configs.prompts import (
    AGENT_MEMORY_EXTRACTION_PROMPT,
    FACT_RETRIEVAL_PROMPT,
    USER_MEMORY_EXTRACTION_PROMPT,
)

logger = logging.getLogger(__name__)


def get_fact_retrieval_messages(message, is_agent_memory=False):
    """Get fact retrieval messages based on the memory type.
    
    Args:
        message: The message content to extract facts from
        is_agent_memory: If True, use agent memory extraction prompt, else use user memory extraction prompt
        
    Returns:
        tuple: (system_prompt, user_prompt)
    """
    if is_agent_memory:
        return AGENT_MEMORY_EXTRACTION_PROMPT, f"Input:\n{message}"
    else:
        return USER_MEMORY_EXTRACTION_PROMPT, f"Input:\n{message}"


def get_fact_retrieval_messages_legacy(message):
    """Legacy function for backward compatibility."""
    return FACT_RETRIEVAL_PROMPT, f"Input:\n{message}"


def ensure_json_instruction(system_prompt, user_prompt):
    """Ensure the word 'json' appears in the prompts when using json_object response format.

    OpenAI's API requires the word 'json' to appear in the messages when
    response_format is set to {"type": "json_object"}. When users provide a
    custom_instructions that doesn't include 'json', this causes a
    400 error. This function appends a JSON format instruction to the system
    prompt if 'json' is not already present in either prompt.

    Args:
        system_prompt: The system prompt string
        user_prompt: The user prompt string

    Returns:
        tuple: (system_prompt, user_prompt) with JSON instruction added if needed
    """
    combined = (system_prompt + user_prompt).lower()
    if "json" not in combined:
        system_prompt += (
            "\n\nYou must return your response in valid JSON format "
            "with a 'facts' key containing an array of strings."
        )
    return system_prompt, user_prompt


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

def normalize_facts(raw_facts):
    """Normalize LLM-extracted facts to a list of strings.

    Smaller LLMs (e.g. llama3.1:8b) sometimes return facts as objects
    like {"fact": "..."} or {"text": "..."} instead of plain strings.
    This mirrors the TypeScript FactRetrievalSchema validation.
    """
    if not raw_facts:
        return []
    normalized = []
    for item in raw_facts:
        if isinstance(item, str):
            fact = item
        elif isinstance(item, dict):
            fact = item.get("fact") or item.get("text")
            if fact is None:
                logger.warning("Unexpected fact shape from LLM, skipping: %s", item)
                continue
        else:
            fact = str(item)
        if fact:
            normalized.append(fact)
    return normalized


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
    match_res=match.group(1).strip() if match else content.strip()
    return re.sub(r"<think>.*?</think>", "", match_res, flags=re.DOTALL).strip()



def extract_json(text):
    """
    Extracts JSON content from a string, removing enclosing triple backticks and optional 'json' tag if present.
    If no code block is found, attempts to locate JSON by finding the first '{' and last '}'.
    If that also fails, returns the text as-is.
    """
    text = text.strip()
    match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    if match:
        json_str = match.group(1)
    else:
        start_idx = text.find("{")
        end_idx = text.rfind("}")
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            json_str = text[start_idx : end_idx + 1]
        else:
            json_str = text
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


def _fetch_url_text(url: str, max_bytes: int = 5 * 1024 * 1024) -> str:
    """Fetch a remote text resource (mdx/txt) and decode it.

    Caps download at ``max_bytes`` to bound memory cost. Per
    docs/platform/features/multimodal-support.mdx, ``mdx_url`` carries
    either an http(s) URL or a raw base64 string.
    """
    import base64
    import binascii
    from urllib.parse import urlparse
    from urllib.request import Request, urlopen

    if url.startswith("http://") or url.startswith("https://"):
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            raise ValueError(f"Unsupported URL scheme for mdx_url: {parsed.scheme}")
        req = Request(url, headers={"User-Agent": "mem0-multimodal/1.0"})
        with urlopen(req, timeout=30) as resp:
            data = resp.read(max_bytes + 1)
        if len(data) > max_bytes:
            raise ValueError(f"Document at {url} exceeds {max_bytes} bytes")
        return data.decode("utf-8", errors="replace")

    payload = url.split(",", 1)[-1] if url.startswith("data:") else url
    try:
        decoded = base64.b64decode(payload, validate=False)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("mdx_url must be an http(s) URL or base64 string") from exc
    if len(decoded) > max_bytes:
        raise ValueError(f"Decoded document exceeds {max_bytes} bytes")
    return decoded.decode("utf-8", errors="replace")


def _extract_pdf_text(url: str, max_bytes: int = 25 * 1024 * 1024) -> str:
    """Fetch and extract text from a PDF URL.

    Requires the optional ``pypdf`` dependency; raises a ``RuntimeError``
    with installation instructions when missing.
    """
    import io
    from urllib.parse import urlparse
    from urllib.request import Request, urlopen

    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError(
            "PDF extraction requires the optional 'pypdf' dependency. "
            "Install with: pip install pypdf"
        ) from exc

    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Unsupported URL scheme for pdf_url: {parsed.scheme}")
    req = Request(url, headers={"User-Agent": "mem0-multimodal/1.0"})
    with urlopen(req, timeout=60) as resp:
        data = resp.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise ValueError(f"PDF at {url} exceeds {max_bytes} bytes")

    reader = PdfReader(io.BytesIO(data))
    pages = []
    for page in reader.pages:
        try:
            pages.append(page.extract_text() or "")
        except Exception:
            continue
    return "\n\n".join(p for p in pages if p.strip())


def parse_vision_messages(messages, llm=None, vision_details="auto"):
    """Parse multimodal messages into plain-text content.

    Per docs/platform/features/multimodal-support.mdx, message ``content`` may
    be a dict whose ``type`` field selects the multimodal handler:

    - ``image_url`` — needs vision-capable ``llm``. When ``llm`` is None we
      fall back to a placeholder string instead of raising, so non-vision
      OSS callers don't crash.
    - ``mdx_url`` — fetched (http/https) or base64-decoded as text.
    - ``pdf_url`` — fetched and PDF-decoded (requires optional ``pypdf``).

    Plain text content passes through unchanged.
    """
    returned_messages = []
    for msg in messages:
        if msg["role"] == "system":
            returned_messages.append(msg)
            continue

        content = msg["content"]

        if isinstance(content, list):
            description = get_image_description(msg, llm, vision_details)
            returned_messages.append({"role": msg["role"], "content": description})
            continue

        if isinstance(content, dict):
            ctype = content.get("type")
            if ctype == "image_url":
                image_url = content["image_url"]["url"]
                if llm is None:
                    returned_messages.append(
                        {"role": msg["role"], "content": f"[image: {image_url}]"}
                    )
                    continue
                try:
                    description = get_image_description(image_url, llm, vision_details)
                except Exception as e:
                    raise Exception(f"Error while processing image {image_url}: {e}")
                returned_messages.append({"role": msg["role"], "content": description})
                continue
            if ctype == "mdx_url":
                doc_url = content["mdx_url"]["url"]
                returned_messages.append({"role": msg["role"], "content": _fetch_url_text(doc_url)})
                continue
            if ctype == "pdf_url":
                pdf_url = content["pdf_url"]["url"]
                returned_messages.append({"role": msg["role"], "content": _extract_pdf_text(pdf_url)})
                continue
            returned_messages.append(msg)
            continue

        returned_messages.append(msg)

    return returned_messages


def process_telemetry_filters(filters):
    """
    Process the telemetry filters.

    Hashes scalar entity-id values for telemetry. Non-string values (operator
    dicts like ``{"in": [...]}``, lists, or wildcards interpreted later) are
    skipped — telemetry only records concrete identifiers.
    """
    if filters is None:
        return {}

    encoded_ids = {}
    for key in ("user_id", "agent_id", "run_id", "app_id"):
        value = filters.get(key)
        if isinstance(value, str):
            encoded_ids[key] = hashlib.md5(value.encode()).hexdigest()

    return list(filters.keys()), encoded_ids


def sanitize_relationship_for_cypher(relationship) -> str:
    """Sanitize relationship text for Cypher queries by replacing problematic characters."""
    char_map = {
        "...": "_ellipsis_",
        "…": "_ellipsis_",
        "。": "_period_",
        "，": "_comma_",
        "；": "_semicolon_",
        "：": "_colon_",
        "！": "_exclamation_",
        "？": "_question_",
        "（": "_lparen_",
        "）": "_rparen_",
        "【": "_lbracket_",
        "】": "_rbracket_",
        "《": "_langle_",
        "》": "_rangle_",
        "'": "_apostrophe_",
        '"': "_quote_",
        "\\": "_backslash_",
        "/": "_slash_",
        "|": "_pipe_",
        "&": "_ampersand_",
        "=": "_equals_",
        "+": "_plus_",
        "*": "_asterisk_",
        "^": "_caret_",
        "%": "_percent_",
        "$": "_dollar_",
        "#": "_hash_",
        "@": "_at_",
        "!": "_bang_",
        "?": "_question_",
        "(": "_lparen_",
        ")": "_rparen_",
        "[": "_lbracket_",
        "]": "_rbracket_",
        "{": "_lbrace_",
        "}": "_rbrace_",
        "<": "_langle_",
        ">": "_rangle_",
        "-": "_",
    }

    # Apply replacements and clean up
    sanitized = relationship
    for old, new in char_map.items():
        sanitized = sanitized.replace(old, new)

    return re.sub(r"_+", "_", sanitized).strip("_")


def remove_spaces_from_entities(
    entity_list: List[Any],
    *,
    sanitize_relationship: bool = True,
) -> List[Dict[str, Any]]:
    """
    Normalize entity relation dicts from LLM/tool output: lowercase, spaces to underscores.

    Skips entries that are not non-empty dicts or that lack any of
    ``source``, ``relationship``, or ``destination`` (avoids KeyError on ``[{}]``
    or partial dicts).
    """
    required = ("source", "relationship", "destination")
    cleaned: List[Dict[str, Any]] = []
    for item in entity_list:
        if not isinstance(item, dict) or not item:
            continue
        if not all(key in item for key in required):
            continue
        item["source"] = item["source"].lower().replace(" ", "_")
        rel = item["relationship"].lower().replace(" ", "_")
        item["relationship"] = sanitize_relationship_for_cypher(rel) if sanitize_relationship else rel
        item["destination"] = item["destination"].lower().replace(" ", "_")
        cleaned.append(item)
    return cleaned

