"""
API Voixo — FastAPI

Lancer le serveur :
    uvicorn api.main:app --reload --port 8000

Documentation interactive auto-generee par FastAPI :
    http://localhost:8000/docs       (Swagger UI)
    http://localhost:8000/redoc      (ReDoc)
"""

import os
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from fastapi.responses import FileResponse

from core import analyze_voice, transform_audio, save_audio, compute_params, PROFILES
from api.schemas import AnalysisResponse, TransformRequest

# ---------------------------------------------------------------------------
# Initialisation de l'app
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Voixo API",
    description="Modification et anonymisation vocale via Praat/parselmouth.",
    version="1.0.0",
)

SUPPORTED_FORMATS = {".mp3", ".wav", ".flac", ".ogg", ".m4a"}


# ---------------------------------------------------------------------------
# Utilitaires
# ---------------------------------------------------------------------------
def _check_format(filename: str) -> None:
    """Leve une HTTPException 400 si le format n'est pas supporte."""
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_FORMATS:
        raise HTTPException(
            status_code=400,
            detail=f"Format non supporte : '{suffix}'. "
                   f"Formats acceptes : {sorted(SUPPORTED_FORMATS)}",
        )


def _save_upload(upload: UploadFile) -> Path:
    """
    Sauvegarde un fichier uploade dans un fichier temporaire.
    Retourne le chemin du fichier temporaire.
    Le fichier temporaire doit etre supprime par l'appelant.
    """
    suffix = Path(upload.filename).suffix.lower()
    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    try:
        tmp.write(upload.file.read())
    finally:
        tmp.close()
    return Path(tmp.name)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/", summary="Sante de l'API")
def root():
    """Verifie que l'API est en ligne."""
    return {"status": "ok", "service": "Voixo API", "version": "1.0.0"}


@app.get("/profiles", summary="Liste des profils vocaux disponibles")
def get_profiles():
    """
    Retourne la liste des profils preset avec leurs ratios.
    Utile pour un front qui veut afficher les options disponibles.
    """
    return {
        name: ratios
        for name, ratios in PROFILES.items()
        if ratios is not None  # exclut "Manuel" qui n'a pas de ratios fixes
    }


@app.post(
    "/analyze",
    response_model=AnalysisResponse,
    summary="Analyse acoustique d'un fichier audio",
)
async def analyze(file: UploadFile = File(description="Fichier audio a analyser")):
    """
    Analyse un fichier audio via Praat et retourne ses caracteristiques acoustiques :
    pitch median, etendue pitch, ratio de parole active, duree, sample rate.

    Ces valeurs sont utilisees par le front pour afficher les infos du fichier
    et par POST /transform pour calculer les parametres relatifs.
    """
    _check_format(file.filename)
    tmp_path = _save_upload(file)

    try:
        result = analyze_voice(tmp_path)
        return AnalysisResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur d'analyse : {e}")
    finally:
        if tmp_path.exists():
            os.remove(tmp_path)


@app.post(
    "/transform",
    summary="Transformation vocale d'un fichier audio",
    response_class=FileResponse,
)
async def transform(
    file:          UploadFile = File(description="Fichier audio source"),
    profile:       str        = Form(default="Manuel"),
    pitch_ratio:   float      = Form(default=1.0),
    formant_ratio: float      = Form(default=1.0),
    range_ratio:   float      = Form(default=1.0),
    speed_ratio:   float      = Form(default=1.0),
):
    """
    Transforme un fichier audio selon les parametres fournis.

    Deux modes :
    - profile != 'Manuel' : les ratios du preset sont appliques automatiquement,
      les parametres manuels sont ignores.
    - profile == 'Manuel' : pitch_ratio, formant_ratio, range_ratio, speed_ratio
      sont utilises tels quels.

    Retourne le fichier WAV transforme en telechargement direct.

    Note : les parametres sont envoyes en multipart/form-data car le fichier
    audio est deja en multipart — on ne peut pas mixer JSON et fichier binaire
    dans la meme requete HTTP sans cette approche.
    """
    _check_format(file.filename)
    tmp_in  = _save_upload(file)
    tmp_out = None

    try:
        # Analyse pour calculer le pitch cible
        analysis = analyze_voice(tmp_in)

        # Choix des parametres selon le mode
        if profile != "Manuel" and profile in PROFILES and PROFILES[profile] is not None:
            params = compute_params(analysis, profile)
            target_pitch   = params["target_pitch"]
            formant_ratio  = params["formant_ratio"]
            range_ratio    = params["range_ratio"]
            speed_ratio    = params["speed_ratio"]
        else:
            # Mode manuel : pitch_ratio converti en Hz cible
            target_pitch = max(50.0, min(800.0, analysis["pitch_median"] * pitch_ratio))

        # Transformation
        result = transform_audio(
            tmp_in,
            target_pitch,
            formant_ratio,
            range_ratio,
            speed_ratio,
        )

        # Sauvegarde du resultat dans un fichier temporaire
        tmp_out_obj = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tmp_out = Path(tmp_out_obj.name)
        tmp_out_obj.close()
        save_audio(result, tmp_out)

        # Nom du fichier de telechargement
        stem     = Path(file.filename).stem
        dl_name  = f"{stem}_{profile.lower().replace(' ', '_')}.wav"

        # FileResponse streame le fichier puis le supprime (background)
        return FileResponse(
            path=str(tmp_out),
            media_type="audio/wav",
            filename=dl_name,
            background=None,  # suppression manuelle apres envoi
        )

    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur de transformation : {e}")
    finally:
        if tmp_in.exists():
            os.remove(tmp_in)
        # tmp_out est garde jusqu'a ce que FileResponse l'ait envoye
        # En production, utiliser BackgroundTasks pour le cleanup