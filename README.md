# 🧠 JAI — Tu Estación de IA Personal

> Un AI Operating System personal que vive en tu Mac, funciona localmente y crece contigo.

![JAI en acción](https://img.shields.io/badge/status-en%20desarrollo-yellow) ![Python](https://img.shields.io/badge/python-3.9+-blue) ![Ollama](https://img.shields.io/badge/ollama-llama3.2-green)

---

## ¿Qué es JAI?

JAI es tu segundo cerebro. Un asistente personal que:
- 🏠 **Corre 100% local** — sin internet, sin suscripciones, sin límites
- 🧠 **Tiene memoria** — recuerda tus conversaciones día a día
- 🎙️ **Habla y escucha** — modo voz integrado
- ⚡ **Vive en tu terminal** — un comando y listo

---

## Instalación

### Requisitos
- macOS
- [Ollama](https://ollama.com) instalado
- Python 3.9+

### Pasos

```bash
# 1. Clona el repositorio
git clone https://github.com/jorgehold/AI.git
cd AI

# 2. Descarga el modelo recomendado
ollama pull llama3.2:3b

# 3. Crea el comando global
echo 'alias jai="python3 ~/AI/jai/jai.py --chat"' >> ~/.zshrc
source ~/.zshrc

# 4. Prueba
jai
```

---

## Comandos disponibles

| Comando | Descripción |
|--------|-------------|
| `jai` | Abre JAI en modo chat con memoria |
| `jai ask "pregunta"` | Pregunta rápida sin entrar al chat |
| `jai --voz` | Modo conversación por voz |
| `jai --memoria` | Ver historial de conversaciones guardadas |
| `jai --olvida` | Borrar toda la memoria |
| `jai sync` | Sincroniza todo con GitHub *(próximamente)* |
| `jai doctor` | Verifica que todo esté funcionando *(próximamente)* |
| `jai backup` | Hace copia de seguridad *(próximamente)* |

---

## Estructura del proyecto

```
~/AI/
├── jai/                  # CLI principal
│   ├── jai.py           # Núcleo de JAI
│   └── memoria/         # Conversaciones guardadas (auto-generado)
├── Knowledge/           # Tu base de conocimiento personal
├── Prompts/             # Prompts y plantillas
├── Models/              # Configuración de modelos
├── Projects/            # Proyectos y agentes
├── Scripts/             # Scripts de automatización
└── Skills/              # Habilidades y especialidades
```

---

## Roadmap

- [x] Chat local con memoria persistente
- [x] Modo voz (texto → voz con macOS)
- [ ] `jai sync` — Git en un comando
- [ ] `jai doctor` — diagnóstico del sistema
- [ ] `jai ask` — preguntas rápidas desde terminal
- [ ] `jai backup` — backup automático
- [ ] Agentes especializados: `jai trader`, `jai coder`, `jai writer`
- [ ] `install.sh` para instalación con un comando
- [ ] Soporte para múltiples modelos

---

## Filosofía

> No es una app. Es un sistema operativo de IA personal.

JAI está diseñado para crecer contigo durante años. Cada comando nuevo, cada agente, cada automatización se suma a una plataforma que tú controlas completamente.

---

## Autor

**Jorge** — [@jorgehold](https://github.com/jorgehold)

---

*Construido con Ollama + Python + tiempo y café ☕*
