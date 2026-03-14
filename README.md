# Voixo

Outil de modification et d'anonymisation vocale basé sur Praat/parselmouth.

## Fonctionnalités

- Anonymisation de fichiers audio (MP3, WAV, FLAC, OGG, M4A)
- Profils vocaux précalibrés (Enfant, Adulte grave, Réconfortant)
- Paramétrage manuel (pitch, formants, mélodie, tempo)
- Aperçu 3 secondes avant export
- Traitement par lots
- API HTTP via FastAPI

## Installation

```bash
pip install parselmouth numpy fastapi uvicorn python-multipart
```

## Utilisation

### Interface desktop

```bash
python voixo_ui.py
```

### API

```bash
uvicorn api.main:app --reload --port 8000
```

Documentation interactive disponible sur `http://localhost:8000/docs`.

## Routes API

| Méthode | Route        | Description                                      |
|---------|--------------|--------------------------------------------------|
| GET     | `/`          | Santé de l'API                                   |
| GET     | `/profiles`  | Liste des profils vocaux disponibles             |
| POST    | `/analyze`   | Analyse acoustique Praat d'un fichier audio      |
| POST    | `/transform` | Transformation vocale avec preset ou paramètres manuels |

## Structure

```
voixo/
├── core/
│   ├── __init__.py        # Exports du module
│   ├── analyzer.py        # Analyse acoustique Praat
│   ├── profiles.py        # Profils vocaux et calcul des paramètres
│   └── transformer.py     # Transformation audio PSOLA
├── api/
│   ├── __init__.py
│   ├── main.py            # Routes FastAPI
│   └── schemas.py         # Modèles Pydantic
├── voixo_ui.py            # Interface desktop tkinter
├── inputs/                # Fichiers source (non versionné)
└── outputs/               # Fichiers générés (non versionné)
```

## Roadmap

- [ ] Analyse automatique pour recommandation de profil (speechbrain)
- [ ] Conversion voix-à-voix profonde (RVC)
- [ ] Front web (React + FastAPI)