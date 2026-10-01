#!/bin/sh
# pre-commit hook para verificar secretos con gitleaks (si está instalado)
if command -v gitleaks >/dev/null 2>&1; then
    gitleaks detect --staged --verbose
    if [ $? -ne 0 ]; then
        echo "Gitleaks ha detectado un posible secreto en los archivos a commitear."
        echo "Por favor remueve el secreto antes de hacer commit."
        exit 1
    fi
else
    echo "[INFO] gitleaks no está instalado localmente. Omitiendo escaneo de pre-commit."
fi
