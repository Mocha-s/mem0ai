# Mem0 Open Source Plugin for Dify

*For Chinese documentation, see [README_CN.md](README_CN.md)*

## 🚀 Overview

The **Mem0 Open Source Plugin** is a comprehensive memory management solution for Dify, providing advanced conversation storage and AI-powered memory extraction capabilities. This plugin enables intelligent memory management with support for multimodal content, semantic search, and sophisticated memory operations.

**Author:** mocha (Secondary Development & Optimization)
**Original Author:** yevanchen
**Version:** 0.3.0
**Type:** Advanced Memory Management Plugin

## 🙏 Acknowledgments

This plugin is based on the original work by **yevanchen**. We extend our sincere gratitude for the foundational implementation and innovative approach to memory management in Dify. This secondary development builds upon that excellent foundation to provide enhanced features and improved user experience.

**Original Contributions:**
- Basic memory add and search functionality
- Initial Mem0 API integration foundation
- Core plugin structure for Dify

**Secondary Development Enhancements:**
- **Custom Local Deployment Support**: Added configurable API URL for self-hosted Mem0 instances
- **Complete Tool Suite**: Expanded from basic add/search to 6 optimized tools (v0.3.0)
- **Advanced API Integration**: Full V1 and V2 API support with multimodal capabilities
- **Enhanced Visual Design**: Emoji icons and improved UI/UX organization
- **Complete Internationalization**: 4-language support (EN/CN/JP/PT)
- **Comprehensive Documentation**: Bilingual guides and developer documentation
- **Performance Optimization**: Enhanced error handling and response processing
- **Tool Architecture Optimization**: Streamlined 7-tool architecture with 100% feature coverage
- **Advanced Features Integration**: Custom categories, graph memory, async processing, and criteria-based retrieval


### ✨ Key Features

#### 📝 **Memory Creation & Management**
- **💾 Basic Memory Storage**: Store conversation memories with AI-powered inference
- **🎨 Multimodal Support**: Handle text, images, documents, and PDFs seamlessly
- **🧠 AI Inference**: Extract meaningful insights and context from conversations
- **🔗 Relationship Mapping**: Automatic discovery of memory relationships

#### 🔍 **Advanced Search & Retrieval**
- **🔍 Semantic Search**: Find memories using natural language queries
- **⚡ Advanced Filtering**: Similarity thresholds, metadata filters, and pagination
- **📋 Batch Operations**: Retrieve and manage multiple memories efficiently
- **🎯 Contextual Matching**: Intelligent memory matching based on conversation context
- **🧠 Graph Memory**: Relationship-based memory search and entity extraction
- **📊 Criteria-based Retrieval**: Score ranges, date filters, and category-based searches

#### ⚙️ **Memory Operations**
- **✏️ Memory Updates**: Modify and enhance existing memories
- **🗑️ Safe Deletion**: Remove unwanted or outdated memories
- **🔄 Memory Lifecycle**: Complete memory management from creation to deletion
- **⚡ Async Processing**: High-performance operations with asynchronous client support
- **🏷️ Custom Categories**: Organize memories with user-defined categorization systems

#### 🛡️ **Security & Privacy**
- **🔐 User Isolation**: Complete data separation between users
- **🔑 API Authentication**: Secure access with API key management
- **🌐 Flexible Deployment**: Support for both self-hosted and cloud solutions
- **📊 Audit Logging**: Comprehensive activity tracking

### 🛠️ Installation

1. **Download** the plugin package from the releases
2. **Upload** to your Dify instance via the plugin management interface
3. **Configure** your Mem0 API credentials:
   - **API Key**: Your Mem0 authentication key
   - **API URL**: Mem0 server endpoint (default: `http://localhost:8000`)
4. **Activate** the plugin and start using memory management tools

### 🔧 Configuration

#### Required Settings
- **Mem0 API Key**: Authentication key for Mem0 service
- **Mem0 API URL**: Server endpoint (self-hosted or cloud)

#### Optional Settings
- **Default Inference Mode**: Enable/disable AI inference by default
- **Memory Retention Policy**: Configure automatic cleanup rules
- **Search Preferences**: Set default similarity thresholds

### 📚 Available Tools (v0.3.0 Optimized Architecture)

Our streamlined 6-tool architecture provides 100% coverage of Mem0's advanced features:

| Tool | Description | Advanced Features | Use Case |
|------|-------------|-------------------|----------|
| 💾 **Add Memory** | Store conversation memories with AI inference | Custom categories, selective memory, async processing | Basic memory creation |
| 🎨 **Add Multimodal Memory** | Process images, documents, and PDFs | Multimodal support, custom instructions, contextual processing | Rich content storage |
| 🔍 **Search Memories** | Advanced semantic search with filtering | Graph memory, criteria-based retrieval, relationship filters | Precise memory finding |
| 📋 **List Memories** | Batch retrieval with sorting and pagination | Selective memory, async client, advanced filtering | Memory management |
| ✏️ **Update Memory** | Modify existing memory content | Timestamp control, metadata updates, version tracking | Memory maintenance |
| 🗑️ **Delete Memory** | Remove specific memories by ID | Async processing, batch operations support | Memory cleanup |

**⚡ Key Optimizations:**
- **Eliminated Redundancy**: Removed overlapping functionality between tools
- **Enhanced Coverage**: 100% integration of Mem0's 10 advanced server-side features
- **Performance Focus**: Async processing and optimized API calls
- **Unified Architecture**: Consistent parameter patterns across all tools

### 🎯 Use Cases

#### **Personal AI Assistant**
- Remember user preferences and past conversations
- Provide contextual responses based on memory
- Learn and adapt to user behavior over time

#### **Customer Support**
- Maintain customer interaction history
- Track issue resolution and follow-ups
- Provide personalized support experiences

#### **Knowledge Management**
- Store and organize important information
- Create searchable knowledge bases
- Maintain institutional memory

#### **Content Creation**
- Remember writing styles and preferences
- Track project progress and ideas
- Maintain creative context across sessions

### 🔗 API Integration & Advanced Features

The plugin provides comprehensive integration with Mem0's enterprise-grade capabilities:

#### **Core API Support:**
- **V1 API**: Basic memory operations and search
- **V2 API**: Advanced features with filtering and pagination
- **Multimodal API**: Support for various content types (images, PDFs, documents)

#### **🚀 Advanced Server-side Features (100% Coverage):**
1. **🔍 Advanced Retrieval**: Enhanced search algorithms with semantic ranking
2. **🏷️ Custom Categories**: User-defined memory organization and classification
3. **🎨 Multimodal Support**: Text, image, document, and PDF processing
4. **📊 Criteria-based Retrieval**: Score ranges, date filters, and precision controls
5. **🧠 Contextual Add**: Context-aware memory creation with relationship mapping
6. **🎯 Selective Memory**: Priority-based memory management and filtering
7. **📝 Custom Instructions**: Personalized extraction prompts and processing rules
8. **⚡ Async Client**: High-performance asynchronous processing
9. **🔗 Graph Memory**: Entity relationship extraction and network-based search
10. **⏰ Timestamp Control**: Precise temporal memory management

#### **🏗️ Architecture Benefits:**
- **Middleware Design**: Tools coordinate rather than implement features directly
- **Parameter Consistency**: Unified interface across all 22 advanced parameters
- **Error Handling**: Comprehensive validation and user feedback
- **Performance Optimization**: Intelligent caching and async processing

### 🌐 Multi-language Support

- **English**: Complete interface and documentation
- **中文 (Chinese)**: Full localization for Chinese users
- **日本語 (Japanese)**: Japanese language support
- **Português (Portuguese)**: Portuguese localization

### 📖 Documentation

- **Installation Guide**: Step-by-step setup instructions
- **API Reference**: Complete tool documentation
- **Best Practices**: Optimization tips and recommendations
- **Troubleshooting**: Common issues and solutions

### 🤝 Support

- **GitHub Issues**: Report bugs and request features
- **Documentation**: Comprehensive guides and examples
- **Community**: Join discussions and share experiences

## � Secondary Development

This plugin represents a secondary development effort to enhance the original Mem0 plugin with:

### **Enhanced Features**
- **Visual Design**: Added emoji icons and improved UI/UX
- **Internationalization**: Complete 4-language support (EN/CN/JP/PT)
- **Documentation**: Comprehensive bilingual documentation
- **Tool Organization**: Logical categorization and improved workflow
- **Error Handling**: Enhanced error messages and user feedback
- **Performance**: Optimized API calls and response handling

### **Development Approach**
- **Respectful Enhancement**: Building upon the original architecture
- **Backward Compatibility**: Maintaining compatibility with existing workflows
- **Community Focus**: Open-source development with community contributions
- **Quality Assurance**: Comprehensive testing and validation

### **Contributing**
We welcome contributions to further enhance this plugin:
- **Bug Reports**: Submit issues via GitHub
- **Feature Requests**: Propose new functionality
- **Code Contributions**: Submit pull requests with improvements
- **Documentation**: Help improve guides and examples

### 📄 License

This plugin is open source and available under the MIT License.

---

**Version**: 0.3.0
**Author**: mocha (Secondary Development & Optimization)
**Original Author**: yevanchen
**Last Updated**: 2025-08-03

**🚀 v0.3.0 Changelog:**
- Streamlined architecture from 8 to 6 optimized tools
- 100% integration of Mem0's 10 advanced server-side features
- Enhanced parameter consistency across all tools
- Improved performance with async processing support
- Eliminated redundant functionality and simplified tool organization


