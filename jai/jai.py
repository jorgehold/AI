#!/usr/bin/env python3
import sys, os, subprocess, json, urllib.request, urllib.error, tempfile
from datetime import datetime
from pathlib import Path

MODELO = "llama3.2:3b"
OLLAMA_URL = "http://localhost:11434/api/generate"
MEMORIA_DIR = Path.home() / "AI" / "jai" / "memoria"
MEMORIA_DIR.mkdir(parents=True, exist_ok=True)
historial = []

AGENTES = {
    "coder": "Eres JAI en modo programador experto. Solo hablas de codigo, debug, arquitectura y buenas practicas. Eres directo, preciso y das ejemplos en codigo. Respondes en espanol.",
    "trader": "Eres JAI en modo trader experto. Analizas mercados, patrones, estrategias y gestion de riesgo. Respondes en espanol.",
    "writer": "Eres JAI en modo escritor experto. Ayudas con redaccion, estructura y estilo. Respondes en espanol.",
}

def archivo_hoy():
    return MEMORIA_DIR / f"{datetime.now().strftime('%Y-%m-%d')}.json"

def cargar_memoria():
    hoy = []
    if archivo_hoy().exists():
        with open(archivo_hoy()) as f: hoy = json.load(f)
    archivos = sorted(MEMORIA_DIR.glob("*.json"), reverse=True)
    resumen = []
    for a in archivos[:7]:
        if a.name == archivo_hoy().name: continue
        with open(a) as f: msgs = json.load(f)
        if msgs:
            resumen.append(f"[{a.stem}]")
            for m in msgs[-6:]: resumen.append(f"{'Jorge' if m['role']=='user' else 'JAI'}: {m['content'][:150]}")
    return hoy, "\n".join(resumen)

def guardar_memoria(h):
    with open(archivo_hoy(), "w") as f: json.dump(h, f, ensure_ascii=False, indent=2)

def llamar_modelo(prompt):
    payload = json.dumps({"model":MODELO,"prompt":prompt,"stream":False}).encode("utf-8")
    try:
        req = urllib.request.Request(OLLAMA_URL,data=payload,headers={"Content-Type":"application/json"})
        with urllib.request.urlopen(req,timeout=60) as r: data=json.loads(r.read())
        return data.get("response","").strip()
    except urllib.error.URLError: return "Error: Ollama no esta corriendo. Ejecuta: ollama serve"
    except Exception as e: return f"Error: {e}"

def preguntar(texto, resumen="", personalidad=None):
    if personalidad is None:
        personalidad = "Eres JAI, asistente personal de Jorge. Respondes en espanol, directo y util. Tienes memoria de conversaciones anteriores."
    historial.append({"role":"user","content":texto})
    guardar_memoria(historial)
    p = personalidad
    if resumen: p += f"\n[Contexto anterior:]\n{resumen}\n"
    p += "\n[Conversacion actual:]\n"
    for m in historial: p += f"{'Jorge' if m['role']=='user' else 'JAI'}: {m['content']}\n"
    p += "JAI:"
    resp = llamar_modelo(p)
    historial.append({"role":"assistant","content":resp})
    guardar_memoria(historial)
    return resp

def hablar(t): subprocess.run(["say","-v","Monica",t],check=False)

def modo_chat(personalidad=None):
    global historial
    historial, resumen = cargar_memoria()
    n = len([m for m in historial if m["role"]=="user"])
    print(f"\nJAI - Chat (escribe salir para terminar)")
    if n: print(f"Recuerdo {n} mensajes de hoy")
    print("-"*50+"\n")
    while True:
        try:
            e = input("Tu: ").strip()
            if not e: continue
            if e.lower() in ["salir","exit","quit","bye"]: print("JAI: Hasta luego!"); break
            print("\nPensando...",end="",flush=True)
            r = preguntar(e, resumen, personalidad)
            print(f"\rJAI: {r}\n")
        except KeyboardInterrupt: print("\nJAI: Hasta luego!"); break

def modo_texto(pregunta, personalidad=None):
    global historial
    historial, resumen = cargar_memoria()
    print("\nPensando...\n")
    print(f"JAI: {preguntar(pregunta, resumen, personalidad)}\n")

def modo_sync():
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M")
    print("Sincronizando con GitHub...")
    ai = str(Path.home()/"AI")
    for cmd in [["git","-C",ai,"add","."],["git","-C",ai,"commit","-m",f"sync: {fecha}"],["git","-C",ai,"push"]]:
        r = subprocess.run(cmd,capture_output=True,text=True)
        if r.returncode!=0 and "nothing to commit" not in r.stdout+r.stderr:
            print(f"Error: {r.stderr.strip()}"); return
    print("Todo sincronizado con GitHub")

def modo_doctor():
    print("\nJAI Doctor - Diagnostico\n"+"-"*40)
    r = subprocess.run(["ollama","list"],capture_output=True,text=True)
    print("OK Ollama: funcionando" if r.returncode==0 else "ERROR Ollama: no corre")
    if r.returncode==0: print("OK Modelo llama3.2:3b: instalado" if "llama3.2:3b" in r.stdout else "WARN Modelo no encontrado")
    archivos = list(MEMORIA_DIR.glob("*.json"))
    print(f"OK Memoria: {len(archivos)} dias guardados")
    r2 = subprocess.run(["git","-C",str(Path.home()/"AI"),"status"],capture_output=True,text=True)
    print("OK Git: configurado" if r2.returncode==0 else "ERROR Git: no configurado")
    print()

def modo_memoria():
    archivos = sorted(MEMORIA_DIR.glob("*.json"),reverse=True)
    if not archivos: print("No hay memoria guardada."); return
    print(f"\nMemoria: {len(archivos)} dias\n"+"-"*40)
    for a in archivos[:10]:
        with open(a) as f: m=json.load(f)
        print(f"{a.stem}: {len([x for x in m if x['role']=='user'])} mensajes")

def main():
    global historial
    args = sys.argv[1:]
    if not args: print("Uso: jai [chat|doctor|sync|coder|trader|writer|ask \"pregunta\"|--memoria]"); return
    if args[0] == "sync": modo_sync(); return
    if args[0] == "doctor": modo_doctor(); return
    if args[0] == "--memoria": modo_memoria(); return
    if args[0] == "ask" and len(args)>1: modo_texto(" ".join(args[1:])); return
    if args[0] in AGENTES:
        print(f"\nJAI {args[0].upper()} activado\n")
        modo_chat(personalidad=AGENTES[args[0]])
        return
    if args[0] in ["chat","--chat"]: modo_chat(); return
    modo_texto(" ".join(args))

if __name__ == "__main__": main()
