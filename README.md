# tonycoach

Convierte vídeos largos de coaches (15–20 min) en clips verticales 9:16 con subtítulos y los deja
programados para TikTok, Instagram Reels y YouTube Shorts a través de Metricool.

```
YouTube / archivo ─► descarga ─► Whisper (transcripción) ─► Claude (elige highlights y textos)
   ─► ffmpeg (recorte 9:16 siguiendo la cara + subtítulos + gancho + crédito)
   ─► revisión (approve/reject) ─► franjas horarias ─► CSV de carga masiva de Metricool
```

## Antes de empezar: permisos

El sistema **solo procesa canales marcados con `permission: true` en `creators.yaml`**. Pide permiso
por escrito a cada creador y guárdalo. Cada clip lleva el @ del creador en pantalla y un enlace al
vídeo original en la descripción. Subir contenido ajeno sin permiso provoca reclamaciones de
Content ID, strikes y cierres de cuenta.

### Vídeos que se pueden reutilizar sin pedir permiso

- **Creative Commons**: algunos autores publican en YouTube con licencia *Creative Commons Atribución*,
  que permite reutilizar el vídeo dando crédito. `python -m shorts discover "búsqueda"` los encuentra y
  comprueba la licencia de cada vídeo; esos vídeos se procesan aunque el canal no esté en `creators.yaml`.
  Ojo: hay muchas resubidas (Tony Robbins, Jim Rohn…) marcadas como CC por quien no es el autor;
  usa solo vídeos subidos por el canal original.
- **Campañas de clipping** (Whop Content Rewards, Vyro…): el creador da el permiso, los vídeos y además
  paga por visualizaciones. Cumple las reglas de cada campaña (etiquetas, enlaces, formato).

## Requisitos

- Python 3.10 o superior
- ffmpeg (Windows: `winget install ffmpeg` · Mac: `brew install ffmpeg`)
- Una API key de Anthropic (https://console.anthropic.com) para elegir los highlights
- La fuente de los subtítulos instalada (por defecto Montserrat ExtraBold, de Google Fonts)

## Instalación

```bash
git clone https://github.com/andonialvarez/tonycoach
cd tonycoach
python -m venv .venv
# Windows: .venv\Scripts\activate    ·    Mac/Linux: source .venv/bin/activate
pip install -r requirements.txt

cp config.example.yaml config.yaml
cp creators.example.yaml creators.yaml
```

Define la clave como variable de entorno (no la guardes en el repo):

```bash
# Windows (PowerShell):  setx ANTHROPIC_API_KEY "sk-ant-..."   (y abre una terminal nueva)
# Mac/Linux:             export ANTHROPIC_API_KEY="sk-ant-..."
```

## Uso

```bash
python -m shorts process "https://www.youtube.com/watch?v=XXXX"   # un vídeo concreto
python -m shorts process-file video.mp4 --creator "Nombre del coach" --url "https://youtu.be/XXXX"
python -m shorts watch          # busca vídeos nuevos en todos los canales autorizados
python -m shorts discover "motivación disciplina"   # lista vídeos Creative Commons

python -m shorts review         # lista los clips pendientes (están en output/clips/)
python -m shorts approve VIDEOID-01 VIDEOID-03     # o: approve all
python -m shorts reject VIDEOID-02

python -m shorts schedule       # asigna las próximas franjas libres por plataforma
python -m shorts export         # genera output/exports/metricool-*.csv
```

`python -m shorts run` hace todo de una vez (vigilar canales y, si `auto_approve: true`, programar y
exportar). Puedes lanzarlo cada día con el Programador de tareas de Windows o con `cron` en Mac/Linux.

## Metricool

1. En Metricool conecta TikTok, Instagram y YouTube (inicio de sesión oficial de cada red).
2. El CSV que genera `export` sigue la plantilla de Planificación → ⋮ → Importar CSV
   (una fila por clip y red, separador `;`). Incluido en el plan gratuito.
3. Sube los clips a una carpeta pública (Google Drive/Dropbox con enlace, un bucket…) y pon su URL en
   `metricool.media_base_url`. Si la dejas vacía, el CSV lleva la ruta local y adjuntas cada vídeo a mano.
4. Importa el CSV generado por `python -m shorts export`.

La API de Metricool (plan Advanced) permitiría saltarse el CSV; está pendiente (`metricool.mode: api`).

## Horarios

Las franjas iniciales están en `config.yaml → schedule` (hora de `timezone`). Una publicación como
máximo por franja y plataforma. Son un punto de partida: tras 2–3 semanas, revisa en Metricool a qué
horas rinde mejor tu audiencia y ajústalas.

## Ajustes útiles

- `whisper.model`: `small` va bien en CPU; `medium` o `large-v3` transcriben mejor si tienes GPU.
- `clips.per_video`, `min_seconds`, `max_seconds`: cuántos clips y de qué duración.
- `style`: fuente, tamaño, palabras por línea, color de la palabra activa, posición.
- `llm.effort`: `medium` por defecto; `high` elige algo mejor a cambio de más coste.

## Tests

```bash
python -m pytest -q
```

## Próximos pasos

- Publicación directa con las APIs oficiales (YouTube Data API, Instagram Graph API, TikTok Content
  Posting API) cuando estén aprobadas las apps de desarrollador, sin pasar por Metricool.
- Ajuste automático de franjas con las analíticas de tus cuentas.
