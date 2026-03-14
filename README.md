# Voixo

Outil de modification et d'anonymisation vocale basé sur Praat/parselmouth.

## Fonctionnalités

- Anonymisation de fichiers audio (MP3, WAV, FLAC, OGG, M4A)
- Profils vocaux précalibrés (Enfant, Adulte grave, Réconfortant)
- Paramétrage manuel (pitch, formants, mélodie, tempo)
- Aperçu 3 secondes avant export
- Traitement par lots

## Installation
```bash
pip install parselmouth numpy
```

## Utilisation
```bash
python voixo_ui.py
```

## Structure
```
voixo/
├── voixo_ui.py        # Interface principale
├── voice_profiles.py  # Moteur de transformation par lots
├── inputs/            # Fichiers source (non versionné)
└── outputs/           # Fichiers générés (non versionné)
```