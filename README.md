KindleZap Backend 📚

Backend service for KindleZap, handling PDF processing, conversion, and email delivery for the KindleZap application.

## ⚠️ Educational Purposes Disclaimer

**IMPORTANT: This project is strictly for educational and learning purposes only.**

This application was developed as:
- A learning exercise to demonstrate modern web development techniques
- A portfolio project to showcase full-stack development skills
- A practical implementation of file processing and API integration concepts

**Please Note:**
- This is NOT intended for commercial use
- This project should NOT be used to process copyrighted materials without proper authorization
- I assume NO responsibility for any misuse of this application
- If you're interested in converting documents for actual use, please use official Amazon services or other authorized platforms

By using or implementing this project, you acknowledge that you're doing so solely for educational purposes and accept full responsibility for compliance with all relevant laws and regulations.

## ✨ Features

- **PDF Processing**: Convert PDF files to Kindle-compatible formats
- **Metadata Management**: Handle book metadata (title, author, genre, language)
- **Email Integration**: Send converted files directly to Kindle devices
- **Content Summarization**: Generate summaries using OpenAI's GPT-3.5
- **HTML Preview**: Convert PDFs to HTML for preview functionality
- **Batch Processing**: Handle multiple files simultaneously

## 🚀 Getting Started

### Prerequisites

- Python 3.11 or higher
- Calibre (for ebook conversion)
- OpenAI API key
- Gmail account (for sending emails)
- Docker (optional)

### Environment Variables

Create a `.env` file with:

EMAIL_ADDRESS=your-email@gmail.com
EMAIL_PASSWORD=your-app-specific-password
OPENAI_API_KEY=your-openai-api-key

### Installation

#### Using Docker

1. Build the Docker image:
   ```bash
   docker build -t kindlezap-backend .
   ```

2. Run the container:
   ```bash
   docker run -p 8000:8000 --env-file .env kindlezap-backend
   ```

#### Manual Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/kindle-backend.git
   ```

2. Install system dependencies:
   ```bash
   sudo apt-get update
   sudo apt-get install -y calibre
   ```

3. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Start the server:
   ```bash
   uvicorn server:app --host 0.0.0.0 --port 8000
   ```

### Requirements

- **System Dependencies**:
  - Calibre: Used for converting PDFs to EPUB format

- **Python Packages** (as listed in `requirements.txt`):
  - `fastapi`: Web framework for building APIs
  - `uvicorn`: ASGI server for running FastAPI applications
  - `python-dotenv`: For loading environment variables
  - `pymupdf`: For PDF processing
  - `ebooklib`: For handling EPUB files
  - `beautifulsoup4`: For HTML parsing
  - `requests`: For making HTTP requests
  - `openai`: For interacting with OpenAI's API

## 🛠️ Tech Stack

- **Framework**: FastAPI
- **PDF Processing**: PyMuPDF (fitz)
- **Ebook Conversion**: Calibre
- **AI Integration**: OpenAI GPT-3.5
- **Email**: SMTP with Gmail
- **Container**: Docker

## 📡 API Endpoints

### POST /summarize
- Processes PDF files and generates summaries
- Returns HTML preview and content summaries

### POST /send
- Converts PDFs to EPUB format
- Adds metadata to converted files
- Sends files to specified Kindle email

## 📧 Contact

Eduardo Tenés - tenes.trillo.eduardo@gmail.com LinkedIn - (https://www.linkedin.com/in/eduardoten%C3%A9st/)
Project Link: [https://github.com/tenesedu/kindle-backend](https://github.com/yourusername/kindle-backend)
