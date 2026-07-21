#!/usr/bin/env python3
"""
JAI - Tu asistente personal local
Uso: python jai.py "tu pregunta"
      python jai.py --voz     (habla con JAI)
      python jai.py --chat    (modo conversación continua)
"""

import sys
import os
import subprocess
import json
import urllib.request
import urllib.error
import tempfile

# ─────────────────────────────────────────────
# CONFIGURACIÓN - Cambia esto si quieres
# ─────────────────────────────────────────────
MODELO = "llama3.2:3b"          # Modelo recomendado para 8GB RAM
OLLAMA_URL = "http://localhost:11434/api/generate"
PERSONALIDAD = """Eres JAI, el asistente personal y segundo cerebro de tu usuario.
Respondes en español, de forma clara, directa y útil.
Eres inteligente, eficiente y vas al punto. No eres genérico ni repetitivo.
Recuerdas el contexto de la conversación actual."""

historial = []  # Memoria de la conversación actual


# ─────────────────────────────────────────────
# NÚCLEO: Hablar con el modelo local
# ─────────────────────────────────────────────
def preguntar(texto):
    """Envía un mensaje a Ollama y devuelve la respuesta."""
    historial.append({"role": "user", "content": texto})

    # Construir prompt con historial
    prompt_completo = PERSONALIDAD + "\n\n"
    for msg in historial:
        if msg["role"] == "user":
            prompt_completo += f"Usuario: {msg['content']}\n"
        else:
            prompt_completo += f"JAI: {msg['content']}\n"
    prompt_completo += "JAI:"

    payload = json.dumps({
        "model": MODELO,
        "prompt": prompt_completo,
        "stream": False
    }).encode("utf-8")

    try:
        req = urllib.request.Request(
            OLLAMA_URL,
            data=payload,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read())
            respuesta = data.get("response", "").strip()
            historial.append({"role": "assistant", "content": respuesta})
            return respuesta
    except urllib.error.URLError:
        return "❌ Error: Ollama no está corriendo. Ejecuta: ollama serve"
    except Exception as e:
        return f"❌ Error inesperado: {e}"


# ─────────────────────────────────────────────
# VOZ: Escuchar (Whisper) y Hablar (macOS say)
# ─────────────────────────────────────────────
def hablar(texto):
    """Convierte texto a voz usando el sistema de macOS."""
    # Usa la voz en español de macOS (sin instalar nada)
    subprocess.run(["say", "-v", "Monica", texto], check=False)


def escuchar():
    """Graba audio del micrófono y lo transcribe con Whisper."""
    try:
        import whisper
    except ImportError:
        print("📦 Instalando Whisper (solo la primera vez)...")
        subprocess.run([sys.executable, "-m", "pip", "install", "openai-whisper", "-q"], check=True)
        import whisper

    print("🎤 Escuchando... (habla ahora, 5 segundos)")

    # Grabar audio con sox (viene en macOS o instalar: brew install sox)
    archivo_audio = tempfile.mktemp(suffix=".wav")
    try:
        subprocess.run(
            ["rec", "-r", "16000", "-c", "1", archivo_audio, "trim", "0", "5"],
            check=True, capture_output=True
        )
    except FileNotFoundError:
        print("❌ Necesitas sox para grabar: brew install sox")
        return None
    except subprocess.CalledProcessError:
        print("❌ Error al grabar audio.")
        return None

    print("🔄 Transcribiendo...")
    modelo_whisper = whisper.load_model("tiny")  # 'tiny' es rápido y liviano
    resultado = modelo_whisper.transcribe(archivo_audio, language="es")
    os.unlink(archivo_audio)

    texto = resultado["text"].strip()
    print(f"🗣️  Tú dijiste: {texto}")
    return texto


# ─────────────────────────────────────────────
# MODOS DE USO
# ─────────────────────────────────────────────
def modo_texto(pregunta):
    """Responde una pregunta en texto."""
    print(f"\n💭 JAI está pensando...\n")
    respuesta = preguntar(pregunta)
    print(f"🤖 JAI: {respuesta}\n")


def modo_chat():
    """Conversación continua en terminal."""
    print("\n🧠 JAI - Modo Chat (escribe 'salir' para terminar)\n")
    print("─" * 50)
    while True:
        try:
            entrada = input("Tú: ").strip()
            if not entrada:
                continue
            if entrada.lower() in ["salir", "exit", "quit", "bye"]:
                print("JAI: ¡Hasta luego! 👋")
                break
            print("\n💭 Pensando...", end="", flush=True)
            respuesta = preguntar(entrada)
            print(f"\r🤖 JAI: {respuesta}\n")
        except KeyboardInterrupt:
            print("\n\nJAI: ¡Hasta luego! 👋")
            break


def modo_voz():
    """Conversación por voz."""
    print("\n🎙️  JAI - Modo Voz (Ctrl+C para salir)\n")
    hablar("Hola, soy JAI. ¿En qué te puedo ayudar?")
    while True:
        try:
            texto = escuchar()
            if not texto:
                continue
            if any(p in texto.lower() for p in ["adiós", "hasta luego", "salir", "bye"]):
                hablar("¡Hasta luego!")
                break
            respuesta = preguntar(texto)
            print(f"🤖 JAI: {respuesta}\n")
            hablar(respuesta)
        except KeyboardInterrupt:
            print("\nJAI: ¡Hasta luego! 👋")
            break


# ─────────────────────────────────────────────
# SETUP: Instalar modelo si no existe
# ─────────────────────────────────────────────
def verificar_modelo():
    """Descarga el modelo si no está instalado."""
    print(f"🔍 Verificando modelo {MODELO}...")
    result = subprocess.run(["ollama", "list"], capture_output=True, text=True)
    if MODELO not in result.stdout:
        print(f"📥 Descargando {MODELO} (solo la primera vez, ~2GB)...")
        subprocess.run(["ollama", "pull", MODELO], check=True)
        print(f"✅ {MODELO} listo!")
    else:
        print(f"✅ {MODELO} ya instalado.")


# ─────────────────────────────────────────────
# PUNTO DE ENTRADA
# ─────────────────────────────────────────────
def main():
    args = sys.argv[1:]

    if not args:
        print(__doc__)
        print("\nEjemplos:")
        print('  python jai.py "¿Cuál es la capital de Japón?"')
        print("  python jai.py --chat")
        print("  python jai.py --voz")
        print("  python jai.py --setup")
        return

    if "--setup" in args:
        verificar_modelo()
        return

    if "--voz" in args:
        modo_voz()
        return

    if "--chat" in args:
        modo_chat()
        return

    # Pregunta directa
    pregunta = " ".join(args)
    modo_texto(pregunta)


if __name__ == "__main__":
    main()
