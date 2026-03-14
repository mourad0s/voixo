import numpy as np
import parselmouth
from pathlib import Path


def analyze_voice(input_path: Path) -> dict:
    """
    Extrait les caracteristiques acoustiques d'un fichier audio via Praat.

    Retourne :
        pitch_median  (float) : pitch median en Hz
        pitch_range   (float) : etendue pitch (p90 - p10) en Hz
        voiced_ratio  (float) : ratio de la duree voisee (0.0 - 1.0)
        duration      (float) : duree totale en secondes
        sample_rate   (int)   : frequence d'echantillonnage en Hz
        channels      (int)   : nombre de canaux du fichier source
    """
    input_path = Path(input_path)
    if not input_path.exists():
        raise FileNotFoundError(f"Fichier introuvable : {input_path}")

    snd = parselmouth.Sound(str(input_path))
    if snd.n_channels > 1:
        snd = snd.convert_to_mono()

    # Pitch
    pitch_obj    = snd.to_pitch()
    pitch_values = pitch_obj.selected_array["frequency"]
    pitch_values = pitch_values[pitch_values > 0]

    if len(pitch_values) == 0:
        raise ValueError(
            f"Aucun pitch detecte dans '{input_path.name}'. "
            "Verifiez que le fichier contient bien une voix."
        )

    pitch_median = float(np.median(pitch_values))
    pitch_range  = float(
        np.percentile(pitch_values, 90) - np.percentile(pitch_values, 10)
    )

    # Ratio de parole active via intensite
    intensity    = snd.to_intensity()
    int_values   = intensity.values[0]
    threshold    = np.percentile(int_values, 30)
    voiced_ratio = float(np.mean(int_values > threshold))

    return {
        "pitch_median":  pitch_median,
        "pitch_range":   pitch_range,
        "voiced_ratio":  voiced_ratio,
        "duration":      float(snd.duration),
        "sample_rate":   int(snd.sampling_frequency),
        "channels":      int(snd.n_channels),
    }