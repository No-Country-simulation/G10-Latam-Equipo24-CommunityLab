# ☁️ Evidencia de Integración con OCI Object Storage (Requisito R5)

> **Autor:** @emanuelperacchia  
> **Fecha de validación:** Octubre 2026  
> **Estado:** ✅ Verificado y operativo en capa Always Free (`sa-valparaiso-1`)

---

## 1. Resumen de Infraestructura Configurada
- **Tenancy / Cuenta:** Activa en Oracle Cloud Infrastructure (Región `sa-valparaiso-1`).
- **Compartimiento:** `com-proyecto-comunitylab` (Hijo del proyecto principal).
- **VCN:** `vcn-communitylab` (Bloque CIDR: `10.0.0.0/16`).
- **Subredes:** 
  - Pública (`public-subnet`) con DNS label `public`.
  - Privada (`private-subnet`) con DNS label `private`.
- **Object Storage Bucket:** `communitylab-activos-marketing` (Visibilidad: Privada, Cifrado con claves administradas por Oracle).

---

## 2. Validación de Conectividad y Permisos (Script de Prueba)

Para demostrar que la aplicación se comunica de forma exitosa con el bucket OCI utilizando las credenciales de API Key y la llave privada `.pem`, se ejecutó el comando de prueba de almacenamiento:

```bash
python -c "from src.oci.storage import OCIStorage; print(OCIStorage().test_connection_and_upload('communitylab-activos-marketing'))"
```

### Output obtenido (Evidencia de éxito):
```python
(True, "Successfully connected to bucket 'communitylab-activos-marketing' and uploaded file 'test-integration.txt'.")
```

---

## 3. Comprobación en la Consola de OCI
Al ingresar a la OCI Console en **Object Storage → Buckets → communitylab-activos-marketing**, se constata la presencia del archivo `test-integration.txt` generado automáticamente por el script de prueba, confirmando que las operaciones de lectura y escritura (`GET` y `PUT`) funcionan sin fricciones.

---
*Documento generado como evidencia técnica para el equipo de desarrollo y validación del QA.*
