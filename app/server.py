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
async def summarize_file(file: UploadFile):

    try:
        if file.content_type != "application/pdf":
            raise HTTPException(status_code=400, detail="Only PDF files are supported.")

        temp_file = save_pdf(file)

        pdf_document = pymupdf.open(temp_file)

        text = ""
        for page_num in range(min(3, pdf_document.page_count)): 
            page = pdf_document[page_num]
            text += page.get_text()

        pdf_document.close()

        if not text.strip():
            raise ValueError("No text found in the PDF.")

        summary = summarize_text(text)
        print(f"Summary: {summary}")

        return JSONResponse(
            content={"summary": summary},
            headers={"Content-Type": "application/json"}
        )

    except HTTPException as http_exc:
        print(f"HTTP Error: {http_exc.detail}")
        raise http_exc
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")
    finally:
        # Limpiar el archivo temporal
        if 'temp_file' in locals() and os.path.exists(temp_file):
            os.remove(temp_file)
            print(f"Archivo temporal eliminado: {temp_file}")

@app.post("/convert")
async def convert_pdf(file: UploadFile):

    converted_file_path = None  
    temp_file = None
    try:
        # Guardar el archivo PDF físicamente
        temp_file = save_pdf(file)

        # Convertir el PDF a EPUB
        converted_file_path = convert_pdf_to_epub(temp_file)

        if not converted_file_path:
            return JSONResponse({"error": "Error during conversion"}, status_code=500)
        else:
            html_content = epub_to_html(converted_file_path)

            if html_content:
                html_content_cover_remove = remove_cover_svg(html_content)
                return {"html": html_content_cover_remove}

    except Exception as e:
        print(f"Error en /upload: {e}")
        print(traceback.format_exc())  # Registrar el stack trace completo
        return JSONResponse({"error": "Internal Server Error"}, status_code=500)

    finally:
        # Limpieza del archivo PDF original
        if temp_file and os.path.exists(temp_file):
            os.remove(temp_file)
            print(f"Archivo temporal eliminado: {temp_file}")


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

        # Convertir el PDF a EPUB
        converted_file_path = convert_pdf_to_epub(temp_file)

        if not converted_file_path:
            return JSONResponse({"error": "Error during conversion"}, status_code=500)
        
        # Convertir metadata a diccionario
        metadata_dict = json.loads(metadata)
        print(f"Metadatos recibidos: {metadata_dict}")

        # Agregar los metadatos al archivo EPUB
    

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


def convert_pdf_to_epub(pdf_path: str) -> str:
    """
    Convierte un archivo PDF a EPUB usando Calibre.

    Args:
        pdf_path (str): Ruta del archivo PDF.

    Returns:
        str: Ruta del archivo EPUB generado si la conversión es exitosa; None si falla.
    """
    try:
        epub_path = pdf_path.replace(".pdf", ".epub")
        command = ["ebook-convert", pdf_path, epub_path, "--output-profile", "kindle"]
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


def epub_to_html(epub_path: str) -> str:
    book = epub.read_epub(epub_path)
    html_content = ""

    for item in book.items:
        if item.get_type() == ITEM_DOCUMENT:
            # Agregar contenido del capítulo al HTML
            html_content += item.get_content().decode("utf-8")
        elif item.get_type() == ITEM_IMAGE:
            # Convertir imágenes a base64
            image_name = item.get_name()
            if image_name == "cover_image.png":
                continue 
            image_data = item.get_content()
            image_base64 = base64.b64encode(image_data).decode("utf-8")

            # Reemplazar la referencia de la imagen en el HTML
            html_content = html_content.replace(
                f'src="{image_name}"',
                f'src="data:image/png;base64,{image_base64}"'
            )

    return html_content


def remove_cover_svg(html_content: str) -> str:
    soup = BeautifulSoup(html_content, "html.parser")
    # Encuentra todos los elementos <svg> con una referencia a "cover_image.jpg"
    for svg in soup.find_all("svg"):
        if svg.find("image", {"xlink:href": "cover_image.jpg"}):
            svg.decompose()  # Elimina el elemento <svg>
    return str(soup)

def add_metadata_to_epub(epub_path: str, metadata: dict):
    """
    Agrega metadatos a un archivo EPUB existente.
    Args:
        epub_path (str): Ruta del archivo EPUB.
        metadata (dict): Diccionario con los metadatos (título, autor, género, lenguaje).
    """
    try:
        book = epub.read_epub(epub_path)

        # Agregar metadatos
        if 'title' in metadata:
            book.set_title(metadata['title'])
        if 'author' in metadata:
            book.add_author(metadata['author'])
        if 'language' in metadata:
            book.set_language(metadata['language'])
        if 'genre' in metadata:
            book.add_metadata('DC', 'subject', metadata['genre'])

        # Guardar el archivo EPUB con los nuevos metadatos
        epub.write_epub(epub_path, book)
        print(f"Metadatos agregados al archivo EPUB: {epub_path}")
    except Exception as e:
        print(f"Error al agregar metadatos al EPUB: {e}")
        raise

