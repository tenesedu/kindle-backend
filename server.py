from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
import os
import smtplib
import subprocess
from fastapi import FastAPI, Form, File, UploadFile
from email import encoders
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import tempfile
import traceback

# Carga las variables del archivo .env
load_dotenv()

email_address = os.getenv("EMAIL_ADDRESS")
email_password = os.getenv("EMAIL_PASSWORD")

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
