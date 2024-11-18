from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
import os
import smtplib
import subprocess
from fastapi import FastAPI, Form, File, Path, UploadFile
from email import encoders
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

# Carga las variables del archivo .env
load_dotenv()

email_address = os.getenv("EMAIL_ADDRESS")
email_password = os.getenv("EMAIL_PASSWORD")

app = FastAPI()

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://tenesedu.github.io/kindlezap-frontend/"],  # Cambia por el dominio de tu frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/upload")
async def convert_and_send(file: UploadFile = File(...), email: str = Form(...)):
    try:
        # Guardar el archivo PDF físicamente
        pdf_path = save_pdf(file)
        
        # Convertir el PDF a EPUB
        epub_path = convert_pdf_to_epub(pdf_path)
        print(epub_path)
        if not epub_path:
            return JSONResponse({"error": "Error during conversion"}, status_code=500)

        # Enviar el archivo EPUB al correo del usuario
        if send_to_kindle(epub_path, email):
            return JSONResponse({"message": "Book successfully sent to Kindle!"}, status_code=200)
        else:
            return JSONResponse({"error": "Error sending file"}, status_code=500)

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

    finally:
        # Limpieza de archivos temporales
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
        if os.path.exists(epub_path):
            os.remove(epub_path)


def save_pdf(file: UploadFile) -> str:
    """
    Guarda el archivo PDF recibido en disco.

    Args:
        file (UploadFile): Archivo PDF subido.

    Returns:
        str: Ruta del archivo PDF guardado.
    """
    pdf_path = f"./{file.filename}"
    with open(pdf_path, "wb") as f:
        f.write(file.file.read())
    return pdf_path


def convert_pdf_to_epub(pdf_path: str) -> str:
    """
    Convierte un archivo PDF a EPUB usando Calibre.

    Args:
        pdf_path (str): Ruta del archivo PDF.

    Returns:
        str: Ruta del archivo EPUB generado si la conversión es exitosa; None si falla.
    """
    epub_path = pdf_path.replace(".pdf", ".epub")
    command = ["ebook-convert", pdf_path, epub_path, "--output-profile", "kindle"]

    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode == 0:
        return epub_path
    else:
        print(f"Error in conversion: {result.stderr}")
        return None


def send_to_kindle(file_path: str, kindle_email: str) -> bool:
    """
    Envía el archivo ePub al correo Kindle del usuario usando Gmail.
    
    Args:
        file_path (str): Ruta del archivo ePub.
        kindle_email (str): Dirección de correo de Kindle del usuario.
        
    Returns:
        bool: True si se envía correctamente; False en caso de error.
    """
    try:
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
        
        print("Correo enviado correctamente a:", kindle_email)
        return True

    except smtplib.SMTPException as e:
        print(f"SMTP error: {e}")
        return False
    except Exception as e:
        print(f"Error al enviar el correo: {e}")
        return False
