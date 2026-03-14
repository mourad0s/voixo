import parselmouth
from pathlib import Path


def transform_audio(
    input_path: Path,
    target_pitch:  float,
    formant_ratio: float,
    range_ratio:   float,
    speed_ratio:   float,
) -> parselmouth.Sound:
    """
    Applique une transformation vocale via l'algorithme PSOLA de Praat.

    Args:
        input_path    : chemin vers le fichier audio source
        target_pitch  : pitch cible en Hz (calcule par profiles.compute_params)
        formant_ratio : ratio de decalage des formants (1.0 = inchange)
        range_ratio   : ratio d'etendue melodique (1.0 = naturel)
        speed_ratio   : ratio de vitesse (1.0 = normal)

    Retourne :
        parselmouth.Sound : objet audio transforme, pret a etre sauvegarde
    """
    input_path = Path(input_path)
    if not input_path.exists():
        raise FileNotFoundError(f"Fichier introuvable : {input_path}")

    snd = parselmouth.Sound(str(input_path))
    if snd.n_channels > 1:
        snd = snd.convert_to_mono()

    return parselmouth.praat.call(
        snd, "Change gender",
        75,            # pitch plancher (Hz) — voix humaine adulte minimum
        600,           # pitch plafond (Hz) — voix humaine adulte maximum
        formant_ratio,
        target_pitch,
        range_ratio,
        speed_ratio,
    )


def save_audio(sound: parselmouth.Sound, output_path: Path) -> None:
    """
    Sauvegarde un objet parselmouth.Sound en WAV.

    Args:
        sound       : objet audio transforme
        output_path : chemin de destination (le dossier est cree si absent)
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sound.save(str(output_path), "WAV")