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

load_dotenv("/app/.env")

email_address = os.getenv("EMAIL_ADDRESS")
email_password = os.getenv("EMAIL_PASSWORD")
openai_api_key = os.getenv("OPENAI_API_KEY")
openai.api_key = openai_api_key

app = FastAPI()

origins = [
    "https://tenesedu.github.io",
    "http://localhost",
    "http://localhost:3000",
]
# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def summarize_text(text: str) -> str:
    print(f"Original text length: {len(text)}")

    # Limitar la longitud del texto
    if len(text) > 1000:
        text = text[:1000]
        print(f"Truncated text length: {len(text)}")

    try:
        
        # Llamada al modelo de OpenAI

        response = openai.ChatCompletion.create(
            messages=[{
                "role": "user",
                "content": f"Give me a summmary of this book: {text}",
            }],
            model="gpt-4o-mini",
        )

        summary = response["choices"][0]["message"]["content"]
        return ({"summary": summary})
    except Exception as e:
        # Manejar errores de la API
        print(f"Error: {e}")
        return "An error occurred while summarizing the text."


@app.post("/summarize")
async def summarize_file(file: UploadFile):
    print("hola")  # Esto confirma que la función inicia
    print(f"File name: {file.filename}")  # Verifica que se recibió el archivo
    print(f"Content type: {file.content_type}")  # Asegúrate de que el tipo sea correcto

    try:
        # Procesa texto plano
        if file.content_type == "text/plain":
            content = await file.read()
            text = content.decode("utf-8")
            print(f"Plain text extracted: {text[:100]}")  # Muestra los primeros 100 caracteres
        
        # Procesa PDF
        elif file.content_type == "application/pdf":
            from PyPDF2 import PdfReader
            pdf_reader = PdfReader(file.file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text()
            print(f"PDF text extracted: {text[:1000]}")  # Muestra un resumen del texto extraído

        # Genera el resumen
        summary = summarize_text(text)
        print(f"Summary generated: {summary}")  # Muestra el resumen generado

        return {"summary": summary}

    except Exception as e:
        print(f"Error: {str(e)}")  # Imprime el error para depurar
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

@app.post("/upload")
async def convert_and_send(file: UploadFile = File(...), email: str = Form(...)):
    pdf_path = None
    epub_path = None
    try:
        print(f"Recibido archivo: {file.filename}")
        print(f"Correo Kindle: {email}")

        # Guardar el archivo PDF físicamente
        pdf_path = save_pdf(file)
        print(f"PDF guardado en: {pdf_path}")

        # Convertir el PDF a EPUB
        epub_path = convert_pdf_to_epub(pdf_path)
        print(f"EPUB convertido en: {epub_path}")

        if not epub_path:
            print("Error: La conversión a EPUB falló")
            return JSONResponse({"error": "Error during conversion"}, status_code=500)

        # Enviar el archivo EPUB al correo del usuario
        if send_to_kindle(epub_path, email):
            print("Archivo enviado correctamente")
            return JSONResponse({"message": "Book successfully sent to Kindle!"}, status_code=200)
        else:
            print("Error: El archivo no se envió")
            return JSONResponse({"error": "Error sending file"}, status_code=500)

    except Exception as e:
        print(f"Error en /upload: {e}")
        print(traceback.format_exc())  # Registrar el stack trace completo
        return JSONResponse({"error": "Internal Server Error"}, status_code=500)

    finally:
        # Limpieza de archivos temporales
        if pdf_path and os.path.exists(pdf_path):
            os.unlink(pdf_path)
            print(f"Archivo temporal eliminado: {pdf_path}")
        if epub_path and os.path.exists(epub_path):
            os.unlink(epub_path)
            print(f"Archivo temporal eliminado: {epub_path}")


@app.post("/convert")
async def convert_pdf(file: UploadFile):

    pdf_path = None
    epub_path = None
    try:

        # Guardar el archivo PDF físicamente
        pdf_path = save_pdf(file)
        print(f"PDF guardado en: {pdf_path}")

        # Convertir el PDF a EPUB
        epub_path = convert_pdf_to_epub(pdf_path)
        print(f"EPUB convertido en: {epub_path}")

        if not epub_path:
            print("Error: La conversión a EPUB falló")
            return JSONResponse({"error": "Error during conversion"}, status_code=500)
        else:
            html_content = epub_to_html(epub_path)

            if html_content:
                html_content_cover_remove = remove_cover_svg(html_content)
                return {"html": html_content_cover_remove}

    except Exception as e:
        print(f"Error en /upload: {e}")
        print(traceback.format_exc())  # Registrar el stack trace completo
        return JSONResponse({"error": "Internal Server Error"}, status_code=500)


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

def save_pdf(file: UploadFile) -> str:
    """
    Guarda el archivo PDF en un directorio temporal.
    """
    try:
        print(f"Guardando archivo: {file.filename}")
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


def send_to_kindle(file_path: str, kindle_email: str) -> bool:
    """
    Envía el archivo ePub al correo Kindle del usuario usando Gmail.
    """
    try:
        print(f"Enviando archivo {file_path} a {kindle_email}")

        # Crear el mensaje
        msg = MIMEMultipart()
        msg['From'] = email_address
        msg['To'] = kindle_email
        msg['Subject'] = 'Your book for Kindle'

        # Adjuntar el archivo ePub
        with open(file_path, 'rb') as f:
            part = MIMEBase('application', 'epub+zip')
            part.set_payload(f.read())
            encoders.encode_base64(part)
            
            # Establecer el nombre del archivo adjunto
            filename = os.path.basename(file_path)
            part.add_header('Content-Disposition', f'attachment; filename="{filename}"')
            msg.attach(part)

        # Enviar el correo
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(email_address, email_password)
            server.sendmail(email_address, kindle_email, msg.as_string())
        
        print(f"Correo enviado correctamente a: {kindle_email}")
        return True

    except smtplib.SMTPException as e:
        print(f"Error SMTP: {e}")
        return False
    except Exception as e:
        print(f"Error al enviar el correo: {e}")
        return False
