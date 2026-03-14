"""
Profils vocaux et calcul des parametres Praat.

Chaque profil est defini par des ratios relatifs appliques
aux caracteristiques mesurees de la voix source.

Sources :
    Titze, I.R. (1994). Principles of Voice Production.
    Puts, D.A. et al. (2006). Dominance and the evolution of sexual dimorphism
    in human voice pitch. Evolution and Human Behavior.
"""

from __future__ import annotations

PROFILES: dict[str, dict[str, float] | None] = {
    "Manuel": None,
    "Neutre": {
        "pitch_ratio":   1.00,
        "formant_ratio": 1.00,
        "range_ratio":   1.00,
        "speed_ratio":   1.00,
    },
    "Enfant": {
        "pitch_ratio":   1.40,   # +40% plus aigu
        "formant_ratio": 1.15,   # +15% conduit vocal plus court
        "range_ratio":   1.30,   # +30% melodie plus expressive
        "speed_ratio":   1.05,
    },
    "Adulte grave": {
        "pitch_ratio":   0.75,   # -25% plus grave
        "formant_ratio": 0.85,   # -15% conduit vocal plus long
        "range_ratio":   0.90,   # -10% voix plus posee
        "speed_ratio":   0.95,
    },
    "Reconfortant": {
        "pitch_ratio":   1.05,   # +5% leger
        "formant_ratio": 0.95,   # -5% timbre doux
        "range_ratio":   0.75,   # -25% peu de variation melodique
        "speed_ratio":   0.90,   # plus lent
    },
}

# Limites acceptees par Praat pour "Change gender"
_PITCH_MIN_HZ = 50.0
_PITCH_MAX_HZ = 800.0


def list_profiles() -> list[str]:
    """Retourne la liste des noms de profils disponibles."""
    return list(PROFILES.keys())


def compute_params(analysis: dict, profile_name: str) -> dict:
    """
    Calcule les parametres concrets pour "Change gender" en appliquant
    les ratios du profil aux valeurs mesurees sur la voix source.

    Args:
        analysis     : dict retourne par analyzer.analyze_voice()
        profile_name : nom du profil (doit etre dans PROFILES)

    Retourne :
        target_pitch  (float) : pitch cible en Hz (clamp 50-800)
        formant_ratio (float) : ratio de decalage des formants
        range_ratio   (float) : ratio d'etendue melodique
        speed_ratio   (float) : ratio de vitesse
    """
    if profile_name not in PROFILES:
        raise ValueError(
            f"Profil inconnu : '{profile_name}'. "
            f"Disponibles : {list_profiles()}"
        )

    profile = PROFILES[profile_name]
    if profile is None:
        raise ValueError(
            "Le profil 'Manuel' ne peut pas etre calcule automatiquement. "
            "Passez les parametres directement a transform_audio()."
        )

    target_pitch = analysis["pitch_median"] * profile["pitch_ratio"]
    target_pitch = max(_PITCH_MIN_HZ, min(_PITCH_MAX_HZ, target_pitch))

    return {
        "target_pitch":  target_pitch,
        "formant_ratio": profile["formant_ratio"],
        "range_ratio":   profile["range_ratio"],
        "speed_ratio":   profile["speed_ratio"],
    }