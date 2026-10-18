# Guía de Despliegue con Docker en Oracle Cloud Infrastructure (OCI)

> `docs/02-Instalacion/` · [Volver al README](../../README.md)

Esta guía explica paso a paso cómo desplegar la plataforma **NuevaMente** (Frontend Angular + Backend FastAPI con LangGraph y OCI Object Storage) utilizando **Docker** y **Docker Compose** en una instancia virtual (VM Compute) de Oracle Cloud (Always Free).

---

## 1. Prerrequisitos en la VM de Oracle Cloud

Conéctate a tu máquina virtual de Oracle Cloud por SSH:

```bash
ssh -i /ruta/a/tu/clave.key ubuntu@<IP_PUBLICA_ORACLE_VM>
```

### 1.1 Instalar Docker y Docker Compose en la VM
Ejecuta los siguientes comandos en Ubuntu:

```bash
# Actualizar repositorios e instalar Docker
sudo apt update
sudo apt install -y docker.io docker-compose-v2 git

# Permitir ejecutar docker sin sudo
sudo usermod -aG docker $USER
newgrp docker
```

Verifica la instalación:
```bash
docker --version
docker compose version
```

---

## 2. Apertura de Puertos (Reglas de Entrada en OCI)

Para que tu aplicación sea accesible desde internet, debes abrir el **puerto 80** (HTTP) y opcionalmente el **8000** (API / Swagger):

### 2.1 En la Consola Web de Oracle Cloud:
1. Ve a **Networking** $\rightarrow$ **Virtual Cloud Networks (VCN)**.
2. Selecciona tu VCN $\rightarrow$ **Security Lists** $\rightarrow$ **Default Security List**.
3. Haz clic en **Add Ingress Rules**:
   - **Source Type:** CIDR
   - **Source CIDR:** `0.0.0.0/0`
   - **IP Protocol:** TCP
   - **Destination Port Range:** `80, 8000`
   - **Description:** `Permitir tráfico web NuevaMente (HTTP y API)`

### 2.2 En el Firewall interno de la VM (iptables de Oracle Linux/Ubuntu):
Las imágenes de Ubuntu en Oracle Cloud traen reglas de iptables restrictivas por defecto. Desbloquea los puertos ejecutando:

```bash
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 8000 -j ACCEPT

# Persistir las reglas
sudo apt install -y iptables-persistent
sudo netfilter-persistent save
```

---

## 3. Clonar y Configurar el Repositorio

Clona la rama `devbackend`:

```bash
# Si es la primera vez:
git clone -b devbackend https://github.com/No-Country-simulation/G10-LATAM-Equipo-18-NuevaMente.git
cd G10-LATAM-Equipo-18-NuevaMente

# Si ya habías clonado el repositorio:
git fetch origin devbackend
git checkout devbackend
git pull origin devbackend
```

### 3.1 Configurar Variables de Entorno (.env)
Copia la plantilla y edita tus claves de API:

```bash
cp backend/.env.example backend/.env
nano backend/.env
```

Asegúrate de configurar al menos:
```env
APP_ENV=production
ALLOW_LOCAL_STORAGE=false
STORAGE_METHOD=oci

# Claves LLM
GEMINI_API_KEY=tu_clave_real_de_gemini
GROQ_API_KEY=tu_clave_real_de_groq_opcional
COHERE_API_KEY=tu_clave_real_de_cohere_opcional

# OCI Object Storage Always Free (Región mx-monterrey-1)
OCI_ENABLED=true
OCI_AUTH_MODE=instance_principal
OCI_REGION=mx-monterrey-1
OCI_NAMESPACE=tu_namespace_de_oracle
OCI_BUCKET_SOURCES=nuevamente-documentos-fuente
OCI_BUCKET_CONTENT=nuevamente-contenidos-educativos
```
*(Guarda los cambios con `Ctrl + O` y sal con `Ctrl + X`).*

---

## 4. Construcción y Ejecución con Docker Compose

Para construir las imágenes de Angular (Nginx) y FastAPI y ponerlas en marcha en segundo plano:

```bash
docker compose up -d --build
```

### 4.1 Verificar Estado de los Contenedores:
```bash
docker compose ps
```
Deberías ver ambos contenedores activos (`Up`):
- `nuevamente-backend` (puerto 8000)
- `nuevamente-frontend` (puerto 80)

### 4.2 Ver Logs en Tiempo Real:
```bash
docker compose logs -f
```

---

## 5. Acceso a la Plataforma

Abre tu navegador web e ingresa:

- **Frontend Angular:** `http://<IP_PUBLICA_ORACLE_VM>/`
- **Documentación Interactiva Swagger:** `http://<IP_PUBLICA_ORACLE_VM>/docs` (o `http://<IP_PUBLICA_ORACLE_VM>:8000/docs`)
- **Chequeo de Salud del Sistema:** `http://<IP_PUBLICA_ORACLE_VM>/api/v1/health`

---

## 6. Comandos Útiles de Mantenimiento

- **Detener los servicios:**
  ```bash
  docker compose down
  ```
- **Reiniciar servicios:**
  ```bash
  docker compose restart
  ```
- **Actualizar a la última versión del repositorio:**
  ```bash
  git pull origin main
  docker compose up -d --build
  ```

---

<div align="right">

[Volver al README](../../README.md)

</div>
