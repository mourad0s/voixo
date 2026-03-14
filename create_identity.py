import os
import parselmouth
from parselmouth.praat import call

project_root = os.path.dirname(os.path.abspath(__file__))
ffmpeg_bin = os.path.join(project_root, "ffmpeg-N-123477-g5640bd3a4f-win64-gpl", "bin")

if ffmpeg_bin not in os.environ["PATH"]:
    os.environ["PATH"] = ffmpeg_bin + os.pathsep + os.environ["PATH"]


def create_unique_identity(input_wav, output_wav, formant_shift=1.1, pitch_shift=1.0):
    """
    Modifie les formants et le pitch pour créer une nouvelle identité vocale.
    formant_shift : > 1.0 = plus fin, < 1.0 = plus profond/épais
    pitch_shift : > 1.0 = plus aigu, < 1.0 = plus grave
    """
    if not os.path.exists(input_wav):
        print(f"Erreur : Le fichier {input_wav} est introuvable dans le dossier 'inputs'.")
        return

    print(f"⏳ Transformation de {input_wav}...")
    sound = parselmouth.Sound(input_wav)

    # L'algorithme 'Change gender' de Praat est excellent pour modifier l'identité
    # tout en restant naturel.
    new_sound = call(sound, "Change gender", 75, 600, formant_shift, pitch_shift, 1.7, 0.4)

    new_sound.save(output_wav, "WAV")
    print(f"✅ Nouvelle identité sauvegardée dans : {output_wav}")


if __name__ == "__main__":
    create_unique_identity("inputs/ma_voix_brute.wav", "identity/ma_nouvelle_voix.wav")