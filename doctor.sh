#!/bin/bash

echo "========================================="
echo "        AI WORKSTATION DOCTOR"
echo "========================================="
echo ""

check_command() {
    if command -v "$1" >/dev/null 2>&1; then
        VERSION=$($1 --version 2>/dev/null | head -n 1)
        echo "✅ $1 instalado"
        [ -n "$VERSION" ] && echo "   $VERSION"
    else
        echo "❌ $1 NO instalado"
    fi
    echo ""
}

check_command git
check_command node
check_command npm
check_command python3

echo "Comprobando Ollama..."
if command -v ollama >/dev/null 2>&1; then
    echo "✅ Ollama instalado"
    ollama list
else
    echo "❌ Ollama NO instalado"
fi

echo ""
echo "Comprobando Claude Code..."
if command -v claude >/dev/null 2>&1; then
    echo "✅ Claude Code instalado"
    claude --version
else
    echo "❌ Claude Code NO instalado"
fi

echo ""
echo "========================================="
echo "Diagnóstico finalizado."
echo "========================================="
