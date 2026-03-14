import os
import sys
import tempfile
import parselmouth
import tkinter as tk
from tkinter import messagebox
from pathlib import Path
import numpy as np
from datetime import datetime

# --- Configuration FFmpeg ---
def _setup_ffmpeg():
    ffmpeg_bin = Path(__file__).parent / "ffmpeg-N-123477-g5640bd3a4f-win64-gpl" / "bin"
    if str(ffmpeg_bin) not in os.environ.get("PATH", ""):
        os.environ["PATH"] = str(ffmpeg_bin) + os.pathsep + os.environ["PATH"]

INPUTS_DIR      = Path("inputs")
OUTPUTS_BASE    = Path("outputs")
SUPPORTED_FORMATS = {".mp3", ".wav", ".flac", ".ogg", ".m4a"}


# --- Moteur audio ---
def transform_audio(input_path, pitch_semitones, formant_val, range_val, speed_val):
    snd = parselmouth.Sound(str(input_path))
    if snd.n_channels > 1:
        snd = snd.convert_to_mono()

    pitch_obj    = snd.to_pitch()
    median_pitch = parselmouth.praat.call(pitch_obj, "Get quantile", 0, 0, 0.5, "Hertz")
    target_pitch = median_pitch * (2 ** (pitch_semitones / 12)) if (median_pitch > 0 and not np.isnan(median_pitch)) else 0

    return parselmouth.praat.call(
        snd, "Change gender",
        75, 600,
        formant_val,
        target_pitch,
        range_val,
        speed_val
    )


# --- Apercu ---
def play_preview(s_pitch, s_formant, s_range, s_speed):
    files = [f for f in INPUTS_DIR.iterdir() if f.suffix.lower() in SUPPORTED_FORMATS]
    if not files:
        messagebox.showwarning("Attention", "Dossier inputs/ vide.")
        return

    OUTPUTS_BASE.mkdir(exist_ok=True)
    temp_out = OUTPUTS_BASE / "temp_preview.wav"
    temp_in  = None  # initialise ici pour le finally

    try:
        snd_src = parselmouth.Sound(str(files[0])).extract_part(0, 3.0)

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            temp_in = tmp.name

        snd_src.save(temp_in, "WAV")
        result = transform_audio(temp_in, s_pitch.get(), s_formant.get(), s_range.get(), s_speed.get())
        result.save(str(temp_out), "WAV")

        # Lecture multiplateforme
        if sys.platform == "win32":
            import winsound
            winsound.PlaySound(str(temp_out), winsound.SND_FILENAME | winsound.SND_ASYNC)
        elif sys.platform == "darwin":
            os.system(f"afplay '{temp_out}' &")
        else:
            os.system(f"aplay '{temp_out}' &")

    except Exception as e:
        messagebox.showerror("Erreur apercu", str(e))
    finally:
        if temp_in and os.path.exists(temp_in):
            os.remove(temp_in)


# --- Traitement par lots ---
def run_batch(s_pitch, s_formant, s_range, s_speed, root):
    p, f, r, s = s_pitch.get(), s_formant.get(), s_range.get(), s_speed.get()

    timestamp    = datetime.now().strftime("%H%M%S")
    folder_name  = f"SESSION_P{p}_F{f}_R{r}_S{s}_{timestamp}"
    session_dir  = OUTPUTS_BASE / folder_name

    root.withdraw()  # masquer sans detruire
    _setup_ffmpeg()
    session_dir.mkdir(parents=True, exist_ok=True)

    with open(session_dir / "config.txt", "w") as cfg:
        cfg.write(f"Configuration Voixo - {datetime.now()}\n")
        cfg.write(f"Pitch: {p} | Formants: {f} | Range: {r} | Speed: {s}\n")

    files  = [file for file in INPUTS_DIR.iterdir() if file.suffix.lower() in SUPPORTED_FORMATS]
    errors = []

    for file in files:
        out_path = session_dir / (file.stem + "_anon.wav")
        try:
            result = transform_audio(file, p, f, r, s)
            result.save(str(out_path), "WAV")
            print(f"OK -> {out_path.name}")
        except Exception as e:
            print(f"Erreur sur {file.name} : {e}")
            errors.append((file.name, str(e)))

    msg = f"Dossier de session cree :\n{folder_name}\n\n{len(files) - len(errors)}/{len(files)} fichier(s) traite(s)."
    if errors:
        msg += "\n\nEchecs :\n" + "\n".join(f"- {n} : {e}" for n, e in errors)

    messagebox.showinfo("Termine", msg)
    root.destroy()


# --- Interface ---
def open_ui():
    root = tk.Tk()
    root.title("Voixo - Laboratoire vocal")
    root.geometry("500x720")

    tk.Label(root, text="Laboratoire vocal", font=("Arial", 16, "bold"), fg="#333").pack(pady=20)

    def slider(label, hint, from_, to, resolution, default):
        tk.Label(root, text=label, font=("Arial", 10, "bold")).pack()
        tk.Label(root, text=hint, fg="gray", font=("Arial", 8)).pack()
        s = tk.Scale(root, from_=from_, to=to, resolution=resolution, orient=tk.HORIZONTAL, length=380)
        s.set(default)
        s.pack()
        return s

    s_pitch   = slider("Hauteur (Pitch)",       "Grave (-) <---> Aigu (+)",                      -10.0, 10.0, 0.1,  2.5)
    s_formant = slider("Timbre (Formants)",      "< 1.0 = Large/Grave  |  > 1.0 = Fin/Aigu",      0.7,  1.3,  0.01, 0.92)
    s_range   = slider("Melodie (Pitch Range)",  "0.0 = Robotique  |  1.0 = Naturel  |  2.0 = Exagere", 0.0, 2.0, 0.05, 1.0)
    s_speed   = slider("Vitesse (Tempo)",        "0.5 = Lent  |  1.0 = Normal  |  1.5 = Rapide",  0.5,  1.5,  0.05, 1.0)

    tk.Button(
        root, text="Ecouter l'apercu (3s)",
        command=lambda: play_preview(s_pitch, s_formant, s_range, s_speed),
        bg="#2196F3", fg="white", font=("Arial", 10, "bold"), pady=15, width=40
    ).pack(pady=30)

    tk.Button(
        root, text="Lancer le traitement par lots",
        command=lambda: run_batch(s_pitch, s_formant, s_range, s_speed, root),
        bg="#4CAF50", fg="white", font=("Arial", 10, "bold"), pady=15, width=40
    ).pack()

    root.mainloop()


if __name__ == "__main__":
    open_ui()