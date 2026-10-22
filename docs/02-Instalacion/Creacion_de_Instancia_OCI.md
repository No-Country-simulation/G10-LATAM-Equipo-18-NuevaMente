# Guía: Creación de una instancia en Oracle Cloud Infrastructure (OCI)

> `docs/02-Instalacion/` · [Volver al README](../../README.md)

Guía paso a paso para crear una instancia en OCI, con foco en la **capa gratuita (Always Free)**. Sigue los pasos en orden para evitar errores comunes.

---

## Paso 1 — Nombre y dominio de la instancia

![Paso 1 - Colocar un nombre a la instancia y seleccionar el dominio](../imagenes/Creacion%20de%20Instancia%2001.png)

Coloca un **nombre descriptivo** para la instancia (por ejemplo, `servidor-nuevamente` o `nuevamente`). Evita nombres genéricos como `instance-20240101-1234`.

Al seleccionar el **dominio de disponibilidad**, revisa los **warnings** que muestra la consola: indican qué imágenes y formas (shapes) están disponibles o agotadas en ese dominio. Si aparece un aviso de falta de capacidad, prueba con otro dominio de disponibilidad (AD-1, AD-2 o AD-3).

> **Nota:** El nombre y el dominio se pueden cambiar después, pero es más cómodo definirlos bien desde el inicio.

---

## Paso 2 — Capacity Type

![Paso 2 - Seleccionar On-demand para capa gratuita](../imagenes/Creacion%20de%20Instancia%2002.png)

Selecciona **On-demand** si estás usando la **capa gratuita**. Esta opción te permite crear la instancia según la disponibilidad del momento, sin reservar capacidad por adelantado.

> **Importante:** Las opciones de *Capacity Reservation* o *Preemptible* **no aplican** al plan Always Free. Si no ves On-demand disponible, probablemente la capacidad del shape seleccionado esté agotada en ese dominio.

---

## Paso 3 — Selección del Sistema Operativo

![Paso 3 - Seleccionar el SO, recomendado Ubuntu 24.04](../imagenes/Creacion%20de%20Instancia%2003.png)

Selecciona la imagen del sistema operativo. Se **recomienda Ubuntu 24.04** por su amplia compatibilidad con herramientas modernas, documentación abundante y buen soporte de la comunidad.

Alternativas válidas:
- **Oracle Linux** (si prefieres el stack nativo de Oracle)
- **Debian** (muy estable y ligero)

Evita imágenes marcadas como *deprecated* o con soporte próximo a finalizar.

---

## Paso 4 — Procesador (Shape)

![Paso 4 - Procesador Ampere A1 Flex para capa gratuita](../imagenes/Creacion%20de%20Instancia%2004.png)

Para la **capa gratuita**, la mejor opción es **Ampere A1 Flex (ARM)**. Ofrece hasta **2 OCPUs y 12 GB de RAM** gratuitas, muy superior a las opciones AMD/x86 del plan free.

> **Aviso:** Este shape suele estar **copado** (sin capacidad disponible). Si aparece el error *"Out of host capacity"*, intenta:
> - Cambiar de dominio de disponibilidad
> - Reintentar en otro horario (madrugada suele funcionar mejor)
> - Usar un script de reintento automático
>
> Como respaldo, el shape **VM.Standard.E2.1.Micro** (x86) siempre está disponible en el plan free, aunque con menos recursos (1 OCPU, 1 GB RAM).

---

## Paso 5 — Security

![Paso 5 - Security, en capa gratuita no hay opciones que configurar](../imagenes/Creacion%20de%20Instancia%2005.png)

En la capa gratuita, esta sección **no ofrece opciones configurables** (como *Shielded instances* o *Confidential computing*). Puedes **pasar directamente al siguiente paso** sin modificar nada.

---

## Paso 6 — VNIC (Red)

![Paso 6 - Crear una nueva VNIC con subred](../imagenes/Creacion%20de%20Instancia%2006.png)

Selecciona **"Create new virtual cloud network"** o, si ya tienes una, elige **"Select existing"**. Lo recomendable para empezar:

- **Crear una nueva VCN** con una subred pública
- La subred debe tener acceso a **Internet Gateway** si vas a conectarte por SSH desde fuera

> **Nota:** Si creas la VCN desde el asistente de Instancia, OCI configura automáticamente el Internet Gateway y las reglas de seguridad básicas.

---

## Paso 7 — Dirección IP

![Paso 7 - IPv4 seleccionar crear automáticamente](../imagenes/Creacion%20de%20Instancia%2007.png)

Selecciona **"Automatically assign public IPv4 address"**. Esto te dará una IP pública para conectarte por SSH y exponer servicios.

Si más adelante quieres una IP **reservada** (que no cambie al reiniciar), puedes asignarla después desde *Reserved Public IPs* y asociarla a la VNIC.

---

## Paso 8 — Claves SSH

![Paso 8 - Descargar la clave privada y pública](../imagenes/Creacion%20de%20Instancia%2008.png)

Aquí defines cómo accederás al servidor. Tienes dos opciones:

1. **Generar un par de claves** desde OCI → descarga la **clave privada** (`.key`) y guarda también la **clave pública**.
2. **Subir tu propia clave pública** (recomendado si ya usas SSH con otras máquinas).

> **Importante:**
> - Guarda las claves en una **carpeta fuera del proyecto**, nunca dentro del repositorio de Git.
> - Ajusta permisos de la clave privada: `chmod 400 tu-clave.key`
> - Añade `*.key` y `*.pem` a tu `.gitignore` si trabajas en el mismo directorio.

---

## Paso 9 — Boot Volume

![Paso 9 - Boot Volume, dejar configuración por defecto](../imagenes/Creacion%20de%20Instancia%2009.png)

Deja la **configuración por defecto**. OCI asignará un volumen de arranque adecuado al shape seleccionado (normalmente 50 GB en el plan free).

Opciones avanzadas que puedes ignorar por ahora:
- Cifrado con claves gestionadas por el usuario
- Backups automáticos del boot volume (puedes activarlos luego)

---

## ✅ Verificación final

Antes de pulsar **Create**, revisa:

- [ ] Nombre y dominio correctos
- [ ] Shape acorde a la capa gratuita (Ampere A1 o E2.1.Micro)
- [ ] Subred pública con Internet Gateway
- [ ] IP pública asignada automáticamente
- [ ] Clave SSH descargada y guardada **fuera** del repo
- [ ] Boot volume por defecto

La instancia pasa por el estado **PROVISIONING → RUNNING** en 1-2 minutos.

---

## Recomendaciones finales

### Después de crear la instancia
1. **Conéctate por SSH:**
   ```bash
   ssh -i ruta/a/tu-clave.key ubuntu@<IP-PUBLICA>
   ```

2. **Actualiza el sistema:**
   ```bash
   sudo apt update && sudo apt upgrade -y
   ```

3. **Abre los puertos 80 y 8000** en la Security List de la VCN y en el firewall
   interno de la VM (ver
   [Despliegue con Docker](Despliegue_Docker_OCI.md#2-apertura-de-puertos-reglas-de-entrada-en-oci)).

4. **Instala Git y Docker** en la instancia:
   ```bash
   sudo apt install -y git docker.io docker-compose-v2
   sudo usermod -aG docker $USER
   newgrp docker
   ```

5. **Continúa con el despliegue:** clona la rama `secondary` y ejecuta
   `docker compose up -d --build` según
   [Despliegue con Docker en OCI](Despliegue_Docker_OCI.md).

### Buenas prácticas
- Etiqueta la instancia con el proyecto (`nuevamente`) para identificar costes.
- Configura alertas de presupuesto en *Billing → Budgets* para no salir de la
  capa gratuita.
- Si usas el shape `VM.Standard.E2.1.Micro`, el backend puede quedarse corto de
  memoria durante la ingesta; considera limitar el tamaño de los documentos.
- Guarda la clave privada SSH fuera del repositorio y nunca la subas a Git.

---

<div align="right">

[Volver al README](../../README.md)

</div>
