from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
import os
import smtplib
import subprocess
from fastapi import FastAPI, Form, File, UploadFile, HTTPException
from email import encoders
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv, find_dotenv
import tempfile
import traceback
from fastapi import Body
from ebooklib import epub, ITEM_DOCUMENT,  ITEM_IMAGE
import base64
from bs4 import BeautifulSoup
import requests
import os
import openai
import pymupdf
import json
import fitz
import base64
from fastapi import Request
# START APP()
app = FastAPI()

# ENVIRONMENTS VARIABLES
load_dotenv()

email_address = os.getenv("EMAIL_ADDRESS")
email_password = os.getenv("EMAIL_PASSWORD")
openai_api_key = os.getenv("OPENAI_API_KEY")
openai.api_key = openai_api_key

print(f"OPENNNNN {openai.api_key}")

# GLOBAL VARIABLES
# converted_file_path = None
# temp_file = None
# received_file = None

# CORS
origins = [
    "https://tenesedu.github.io",
    "http://localhost",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ENDPOINTS
@app.post("/summarize")
async def summarize_file(request: Request):
    
    form = await request.form()
    print("Form data:", form)
    
    files = form.getlist("file")
    if not files:
        print("No files provided")
        raise HTTPException(status_code=422, detail="No files provided")
        
    temp_files = []
    summaries = []
    pdf_htmls = []

    try:
        print(f"Starting to process {len(files)} files")
        for file in files:
            if not file or not file.filename:
                raise HTTPException(status_code=422, detail="Invalid file provided")
                
            print(f"Processing file: {file.filename}")
            if not file.content_type or "pdf" not in file.content_type.lower():
                raise HTTPException(status_code=400, detail=f"File {file.filename} is not a PDF. Only PDF files are supported.")

            temp_file = save_pdf(file)
            temp_files.append(temp_file)

        # PDF to HTML
        pdf_htmls = pdf_to_html(temp_files)

        if len(pdf_htmls) == 0:
            raise ValueError("No HTML content found.")

        for temp_file in temp_files:
            pdf_document = pymupdf.open(temp_file)

            text = ""
            for page_num in range(min(3, pdf_document.page_count)):
                page = pdf_document[page_num]
                text += page.get_text()

            pdf_document.close()

            if not text.strip():
                raise ValueError("No text found in the PDF.")

            summary = summarize_text(text)
            summaries.append(summary)

        return JSONResponse(
            content={
                "summary": {"summary": summaries}, 
                "html": pdf_htmls
            },
            headers={"Content-Type": "application/json"}
        )

    except HTTPException as http_exc:
        print(f"HTTP Error: {http_exc.detail}")
        raise http_exc
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")
    finally:
        for temp_file in temp_files:
            if os.path.exists(temp_file):
                os.remove(temp_file)
                print(f"Temporary file {temp_file} deleted successfully.")

@app.post("/send")
def send_to_kindle(file: UploadFile, email: str = Form(...), metadata: str = Form(...)):
    """
    Envía el archivo ePub al correo Kindle del usuario usando Gmail.
    """
    converted_file_path = None
    temp_file = None
    metadata_dict = None
    try:
        # Guardar el archivo PDF físicamente
        temp_file = save_pdf(file)

        # Convertir metadata a diccionario
        metadata_dict = json.loads(metadata)
        print(metadata_dict)

        # Convertir el PDF a EPUB
        converted_file_path = convert_pdf_to_epub(temp_file, metadata_dict)

        if not converted_file_path:
            return JSONResponse({"error": "Error during conversion"}, status_code=500)
        

        # Crear el mensaje
        msg = MIMEMultipart()
        msg['From'] = email_address
        msg['To'] = email
        msg['Subject'] = 'Your book for Kindle'

        # Adjuntar el archivo ePub
        with open(converted_file_path, 'rb') as f:
            part = MIMEBase('application', 'epub+zip')
            part.set_payload(f.read())
            encoders.encode_base64(part)
            
            # Establecer el nombre del archivo adjunto
            filename = f"{metadata_dict.get('title', 'book')}.epub"
            part.add_header('Content-Disposition', f'attachment; filename="{filename}"')
            msg.attach(part)

        # Enviar el correo
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(email_address, email_password)
            server.sendmail(email_address, email, msg.as_string())
        
        print(f"Correo enviado correctamente a: {email}")
        return {"status": "Email sent successfully"}

    except smtplib.SMTPException as e:
        print(f"Error SMTP: {e}")
        raise HTTPException(status_code=500, detail="Error sending email")
    except Exception as e:
        print(f"Error al enviar el correo: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")
    finally:
        # Limpieza de archivos temporales
        if temp_file and os.path.exists(temp_file):
            os.remove(temp_file)
            print(f"Archivo temporal eliminado: {temp_file}")
        if converted_file_path and os.path.exists(converted_file_path):
            os.remove(converted_file_path)
            print(f"Archivo EPUB eliminado: {converted_file_path}")

# FUNCTIONS
def summarize_text(text: str) -> str:
    if len(text) > 1000:
        text = text[:1000]
    try:
        response = openai.ChatCompletion.create(
            messages=[{
                "role": "user",
                "content": f"Give me a summmary of this book: {text}",
            }],
            model="gpt-3.5-turbo",
        )
        print(response)

        summary = response["choices"][0]["message"]["content"]
        return ({"summary": summary})
    except Exception as e:
        return "An error occurred while summarizing the text."


def save_pdf(file: UploadFile) -> str:
    """
    Guarda el archivo PDF en un directorio temporal.
    """
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
            temp_file.write(file.file.read())
            print(f"Archivo guardado temporalmente en: {temp_file.name}")
            return temp_file.name
    except Exception as e:
        print(f"Error al guardar el PDF: {e}")
        raise


def convert_pdf_to_epub(pdf_path: str, metadata: dict) -> str:

    try:
        epub_path = pdf_path.replace(".pdf", ".epub")
        command = [
            "ebook-convert",
            pdf_path,
            epub_path,
            "--output-profile", "kindle",
            "--title", metadata["title"],
            "--authors", metadata["author"],
            "--language", metadata["language"], 
            "--tags", metadata["genre"],  
            "--no-default-epub-cover"  
        ]
        print(f"Ejecutando comando: {' '.join(command)}")

        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"Conversión exitosa: {epub_path}")
            return epub_path
        else:
            print(f"Error en la conversión: {result.stderr}")
            return None
    except Exception as e:
        print(f"Error al convertir PDF a EPUB: {e}")
        raise


def pdf_to_html(pdf_paths: list[str]) -> str:
    try:
        # Only process the first PDF file
        pdf_path = pdf_paths[0]
        doc = fitz.open(pdf_path)

        html_content = '<?xml version="1.0" encoding="utf-8"?>\n'
        html_content += '<!DOCTYPE html>\n'

        for page_num in range(doc.page_count):
            page = doc.load_page(page_num)
            html = page.get_text("html")

            # Remove all inline styles
            html = html.replace('style="', '')

            # Limit image sizes
            html = html.replace('<img ', '<img style="max-width: 100%; height: auto;" ')

            # Add page content to HTML
            html_content += html

        html_content += "</html>"

        return html_content

    except Exception as e:
        print(f"Error al convertir PDF a HTML: {e}")
        raise



def convert_pdf_to_epub_no_metadata(pdf_path: str) -> str:

    try:
        epub_path = pdf_path.replace(".pdf", ".epub")
        command = [
            "ebook-convert",
            pdf_path,
            epub_path,
            "--output-profile", "kindle", 
        ]

        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode == 0:
            return epub_path
        else:
            return None
    except Exception as e:
        raise


def remove_cover_svg(html_content: str) -> str:
    soup = BeautifulSoup(html_content, "html.parser")
    # Encuentra todos los elementos <svg> con una referencia a "cover_image.jpg"
    for svg in soup.find_all("svg"):
        if svg.find("image", {"xlink:href": "cover_image.jpg"}):
            svg.decompose()  # Elimina el elemento <svg>
    return str(soup)
