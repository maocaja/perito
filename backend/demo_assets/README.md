# demo_assets — adjuntos reales para la demo

Deja aquí los archivos reales (sintéticos, **sin PII real**) que `make demo-mail` adjunta a los correos de
prueba. Cuando el poller lee el correo desde Gmail, Perito baja estos adjuntos y los pinta en el front
(galería + visor del drawer).

## Archivos que Perito busca (deja los que tengas; los que falten caen al mock)

| Archivo                | Se adjunta como | Dónde se ve en Perito                    |
|------------------------|-----------------|------------------------------------------|
| `foto_siniestro.jpg`   | Foto            | Galería "Documentos e imágenes" + visor  |
| `denuncia.pdf`         | Denuncia        | Visor del drawer                         |
| `soat.pdf`             | SOAT            | Visor del drawer                         |

- Formatos soportados en el visor: **imágenes** (`.jpg`, `.jpeg`, `.png`) y **PDF** (`.pdf`).
- Si quieres, la foto puede ser distinta por escenario: `foto_feliz.jpg`, `foto_fraude.jpg`,
  `foto_no-encontrada.jpg`, `foto_campos-faltantes.jpg` (si no existe, se usa `foto_siniestro.jpg`).
- Si un archivo no existe, ese adjunto vuelve al mock sintético actual (P7 honesto).

## ⚠️ Solo para la demo
Estos archivos son **sintéticos, sin PII real**. En producción con correos reales, Perito sigue mostrando
solo la **huella** por privacidad (P5); esta ruta de render es exclusiva de los assets de esta carpeta.
