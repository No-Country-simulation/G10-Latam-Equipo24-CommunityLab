# Configuración y Setup de OCI (Oracle Cloud Infrastructure)

Este documento detalla los pasos necesarios para configurar y conectar el almacenamiento de objetos de Oracle Cloud Infrastructure (OCI Object Storage) en **CommunityLab**, garantizando que el sistema pueda persistir los activos de distribución generados de forma automática o degradar limpiamente a un snapshot local si no hay credenciales disponibles.

---

## 1. Arquitectura de Almacenamiento

El pipeline de CommunityLab interactúa con OCI Object Storage mediante el SDK oficial de Python (`oci`). 

- **Servicio utilizado:** OCI Object Storage (Bucket estándar).
- **Región por defecto:** `sa-valparaiso-1` (Región de Valparaíso, Chile).
- **Nombre del Bucket:** `communitylab-activos-marketing`
- **Estructura de objetos:** Los paquetes de distribución generados se almacenan bajo la ruta:
  ```text
  activos/YYYY-semana-WW/paquete-distribucion.json
  ```
- **Modo de Degradación (Graceful Degradation):** Si el SDK de OCI no está instalado, faltan credenciales o la red falla, el pipeline **nunca rompe**: degrada automáticamente a un almacenamiento local basado en archivos bajo `storage/activos/`.

---

## 2. Requisitos Previos en OCI

Para configurar tu propio Tenancy y Bucket:

1. Tener una cuenta activa en Oracle Cloud Infrastructure (capa *Always Free* o superior).
2. Crear un **Bucket** (ej. `communitylab-activos-marketing`) en la región elegida (ej. `sa-valparaiso-1`) con nivel de visibilidad **Privado**.
3. Crear un **Usuario de Servicio** o usuario dedicado para la aplicación en la consola de OCI.
4. Generar un par de **claves API (RSA)**:
   - Clave privada (`.pem`) guardada de forma segura en tu máquina local.
   - Huella digital (*fingerprint*) asociada a dicha clave.
5. Obtener los siguientes identificadores desde la consola de OCI:
   - **Tenancy OCID** (`ocid1.tenancy...`)
   - **User OCID** (`ocid1.user...`)
   - **Region** (ej. `sa-valparaiso-1`)

---

## 3. Variables de Entorno

Para conectar el pipeline con OCI, debés configurar las siguientes variables de entorno en tu archivo `.env` local (copiando desde `.env.example`). 

> ⚠️ **IMPORTANTE:** Jamás subas tu archivo `.env`, llaves `.pem` ni OCIDs reales al repositorio público. El archivo `.gitignore` ya se encarga de excluirlos.

```env
# OCI Object Storage Configuration
OCI_USER_ID="ocid1.user.oc1..tu_user_ocid_aqui"
OCI_PRIVATE_KEY_PATH="path/a/tu/api-key.pem"
OCI_FINGERPRINT="xx:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx"
OCI_TENANCY_ID="ocid1.tenancy.oc1..tu_tenancy_ocid_aqui"
OCI_REGION="sa-valparaiso-1"
OCI_BUCKET_NAME="communitylab-activos-marketing"
```

> La clave privada se puede declarar de dos formas y alcanza con una: como
> **ruta** (`OCI_PRIVATE_KEY_PATH`, para el checkout local) o como **contenido**
> (`OCI_PRIVATE_KEY`, para los secrets de la nube). Si la ruta apunta a un
> archivo que existe, esa gana; si no, se usa el contenido. Ver
> [`ARQ-07`](DECISIONS.md#arq-07--la-clave-privada-llega-como-archivo-o-como-contenido).


---

## 4. Verificación y Pruebas

Una vez configuradas las credenciales, podés verificar el funcionamiento del almacenamiento corriendo el pipeline de demostración:

```bash
python scripts/run_demo.py data/sample/demo_fixed.json
```

Si las credenciales son correctas y hay conectividad, verás en los logs la confirmación de la subida a OCI con el estado `guardado_con_exito`. En caso contrario, el sistema informará la degradación a snapshot local de forma transparente.
