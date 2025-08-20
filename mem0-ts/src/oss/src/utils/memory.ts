import { OpenAILLM } from "../llms/openai";
import { Message } from "../types";

const get_image_description = async (image_url: string) => {
  const llm = new OpenAILLM({
    apiKey: process.env.OPENAI_API_KEY,
  });
  const response = await llm.generateResponse([
    {
      role: "user",
      content:
        "Provide a description of the image and do not include any additional text.",
    },
    {
      role: "user",
      content: { type: "image_url", image_url: { url: image_url } },
    },
  ]);
  return response;
};

const get_document_description = async (document_url: string, doc_type: string) => {
  try {
    // For TypeScript client, we implement a simplified version
    // In a real implementation, you might want to call a backend API
    // or use a document processing library

    let content = "";

    // Check if it's a Base64 encoded data URL
    if (document_url.startsWith('data:')) {
      // Extract Base64 data from data URL
      if (document_url.includes(';base64,')) {
        const base64_data = document_url.split(';base64,')[1];
        try {
          // Decode base64 content
          const decoded = atob(base64_data);
          content = decoded;
        } catch (error) {
          throw new Error(`Failed to decode base64 content: ${error}`);
        }
      } else {
        throw new Error("Invalid data URL format - missing base64 encoding");
      }
    } else {
      // For URL downloads, we'll use fetch
      try {
        const response = await fetch(document_url, {
          method: 'GET',
          headers: {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
          },
        });

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        // Check content size (10MB limit)
        const contentLength = response.headers.get('content-length');
        const maxSize = 10 * 1024 * 1024; // 10MB

        if (contentLength && parseInt(contentLength) > maxSize) {
          throw new Error(`Document size (${contentLength} bytes) exceeds maximum allowed size (${maxSize} bytes)`);
        }

        if (doc_type.toLowerCase() === 'pdf') {
          // For PDF files, we return a placeholder message
          // In a real implementation, you would use a PDF parsing library
          content = "PDF content extraction not implemented in TypeScript client. Please use the Python backend for PDF processing.";
        } else {
          // For MDX/TXT files, get text content
          content = await response.text();
        }

      } catch (error) {
        throw new Error(`Failed to download document from ${document_url}: ${error}`);
      }
    }

    // Clean up and validate content
    content = content.trim();
    if (!content) {
      throw new Error("No content found in document");
    }

    return content;

  } catch (error) {
    console.error(`Error processing document ${document_url}:`, error);
    throw new Error(`Error while processing document ${document_url}: ${error}`);
  }
};

const parse_vision_messages = async (messages: Message[]) => {
  const parsed_messages = [];
  for (const message of messages) {
    let new_message = {
      role: message.role,
      content: "",
    };
    if (message.role !== "system") {
      if (typeof message.content === "object") {
        if (message.content.type === "image_url") {
          // Handle image content
          const description = await get_image_description(
            message.content.image_url.url,
          );
          new_message.content =
            typeof description === "string"
              ? description
              : JSON.stringify(description);
          parsed_messages.push(new_message);
        } else if (message.content.type === "mdx_url") {
          // Handle MDX/TXT document content
          try {
            const document_content = await get_document_description(
              message.content.mdx_url.url,
              "mdx"
            );
            new_message.content = document_content;
            parsed_messages.push(new_message);
          } catch (error) {
            throw new Error(`Error while processing document ${message.content.mdx_url.url}: ${error}`);
          }
        } else if (message.content.type === "pdf_url") {
          // Handle PDF document content
          try {
            const document_content = await get_document_description(
              message.content.pdf_url.url,
              "pdf"
            );
            new_message.content = document_content;
            parsed_messages.push(new_message);
          } catch (error) {
            throw new Error(`Error while processing PDF document ${message.content.pdf_url.url}: ${error}`);
          }
        } else {
          // Unknown multimodal type, pass through as-is
          parsed_messages.push(message);
        }
      } else {
        // Regular text content
        parsed_messages.push(message);
      }
    } else {
      // System messages pass through unchanged
      parsed_messages.push(message);
    }
  }
  return parsed_messages;
};

export { parse_vision_messages };
