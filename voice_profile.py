import os
import sys
import tempfile
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
from datetime import datetime

import numpy as np
import parselmouth

# ---------------------------------------------------------------------------
# FFmpeg
# ---------------------------------------------------------------------------
def _setup_ffmpeg():
    ffmpeg_bin = Path(__file__).parent / "ffmpeg-N-123477-g5640bd3a4f-win64-gpl" / "bin"
    if str(ffmpeg_bin) not in os.environ.get("PATH", ""):
        os.environ["PATH"] = str(ffmpeg_bin) + os.pathsep + os.environ["PATH"]

# ---------------------------------------------------------------------------
# Profils vocaux
# ---------------------------------------------------------------------------
PROFILES = {
    "Manuel":        None,
    "Neutre":        {"pitch": 1.00, "formant": 1.00, "range": 1.00, "speed": 1.00},
    "Enfant":        {"pitch": 1.40, "formant": 1.15, "range": 1.30, "speed": 1.05},
    "Adulte grave":  {"pitch": 0.75, "formant": 0.85, "range": 0.90, "speed": 0.95},
    "Reconfortant":  {"pitch": 1.05, "formant": 0.95, "range": 0.75, "speed": 0.90},
}

# ---------------------------------------------------------------------------
# Analyse Praat
# ---------------------------------------------------------------------------
def analyze_voice(input_path: Path) -> dict:
    snd = parselmouth.Sound(str(input_path))
    if snd.n_channels > 1:
        snd = snd.convert_to_mono()

    pitch_obj    = snd.to_pitch()
    pitch_values = pitch_obj.selected_array["frequency"]
    pitch_values = pitch_values[pitch_values > 0]

    if len(pitch_values) == 0:
        raise ValueError("Aucun pitch detecte — fichier muet ou bruit pur ?")

    pitch_median = float(np.median(pitch_values))
    pitch_range  = float(np.percentile(pitch_values, 90) - np.percentile(pitch_values, 10))

    intensity    = snd.to_intensity()
    int_values   = intensity.values[0]
    threshold    = np.percentile(int_values, 30)
    voiced_ratio = float(np.mean(int_values > threshold))

    return {
        "pitch_median":  pitch_median,
        "pitch_range":   pitch_range,
        "voiced_ratio":  voiced_ratio,
        "duration":      snd.duration,
        "sample_rate":   int(snd.sampling_frequency),
        "channels":      snd.n_channels,
    }

# ---------------------------------------------------------------------------
# Transformation
# ---------------------------------------------------------------------------
def transform_audio(input_path: Path, pitch_ratio, formant_val, range_val, speed_val, analysis: dict):
    snd = parselmouth.Sound(str(input_path))
    if snd.n_channels > 1:
        snd = snd.convert_to_mono()

    target_pitch = analysis["pitch_median"] * pitch_ratio
    target_pitch = max(50.0, min(800.0, target_pitch))

    return parselmouth.praat.call(
        snd, "Change gender",
        75, 600,
        formant_val,
        target_pitch,
        range_val,
        speed_val,
    )

# ---------------------------------------------------------------------------
# Lecture audio multiplateforme
# ---------------------------------------------------------------------------
def play_wav(path: str):
    if sys.platform == "win32":
        import winsound
        winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC)
    elif sys.platform == "darwin":
        os.system(f"afplay '{path}' &")
    else:
        os.system(f"aplay '{path}' &")

# ---------------------------------------------------------------------------
# Interface principale
# ---------------------------------------------------------------------------
class VoixoApp:
    def __init__(self, root):
        self.root      = root
        self.root.title("Voixo - Laboratoire vocal")
        self.root.geometry("580x700")
        self.root.resizable(True, True)

        self.input_path = None
        self.analysis   = None
        self.temp_out   = None

        self._build_ui()
        _setup_ffmpeg()

    # -----------------------------------------------------------------------
    # Construction UI
    # -----------------------------------------------------------------------
    def _build_ui(self):

        # --- Barre d'actions fixe en bas (toujours visible) ---
        frm_bottom = tk.Frame(self.root, bg="#f0f0f0", bd=1, relief="raised")
        frm_bottom.pack(side="bottom", fill="x", padx=0, pady=0)

        frm_btns = tk.Frame(frm_bottom, bg="#f0f0f0")
        frm_btns.pack(pady=10)

        tk.Button(frm_btns, text="Ecouter l'apercu (3s)",
                  command=self._preview,
                  bg="#1976D2", fg="white", font=("Arial", 10, "bold"),
                  pady=10, width=22).pack(side="left", padx=8)

        tk.Button(frm_btns, text="Exporter le fichier",
                  command=self._export,
                  bg="#388E3C", fg="white", font=("Arial", 10, "bold"),
                  pady=10, width=22).pack(side="left", padx=8)

        self.lbl_status = tk.Label(frm_bottom, text="", font=("Arial", 9),
                                   fg="#555", bg="#f0f0f0")
        self.lbl_status.pack(pady=(0, 6))

        # --- Zone scrollable pour le contenu ---
        canvas    = tk.Canvas(self.root, borderwidth=0, highlightthickness=0)
        scrollbar = tk.Scrollbar(self.root, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        self.frame = tk.Frame(canvas)
        self.frame_id = canvas.create_window((0, 0), window=self.frame, anchor="nw")

        def _on_frame_configure(e):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _on_canvas_configure(e):
            canvas.itemconfig(self.frame_id, width=e.width)

        self.frame.bind("<Configure>", _on_frame_configure)
        canvas.bind("<Configure>", _on_canvas_configure)
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(-1*(e.delta//120), "units"))

        f = self.frame  # alias pour la lisibilite

        # Titre
        tk.Label(f, text="Voixo — Laboratoire vocal",
                 font=("Arial", 15, "bold"), fg="#222").pack(pady=(20, 4))
        tk.Label(f, text="Modification et anonymisation de voix",
                 font=("Arial", 9), fg="#888").pack(pady=(0, 16))

        # --- Bloc 1 : Fichier source ---
        self._section(f, "1. Fichier source")

        self.lbl_file = tk.Label(f, text="Aucun fichier selectionne",
                                 font=("Arial", 9), fg="#666", wraplength=480)
        self.lbl_file.pack(padx=20, pady=4)

        tk.Button(f, text="Choisir un fichier audio",
                  command=self._pick_file,
                  bg="#1976D2", fg="white", font=("Arial", 10, "bold"),
                  pady=8, width=36).pack(pady=(0, 4))

        # --- Bloc 2 : Analyse Praat ---
        self._section(f, "2. Analyse Praat")

        self.frm_analysis = tk.Frame(f, bg="#f5f5f5", bd=1, relief="solid")
        self.frm_analysis.pack(fill="x", padx=20, pady=4)

        self.lbl_pitch    = self._info_row(self.frm_analysis, "Pitch median")
        self.lbl_range    = self._info_row(self.frm_analysis, "Etendue pitch")
        self.lbl_voiced   = self._info_row(self.frm_analysis, "Ratio voix active")
        self.lbl_duration = self._info_row(self.frm_analysis, "Duree")
        self.lbl_sr       = self._info_row(self.frm_analysis, "Sample rate")

        # --- Bloc 3 : Preset ---
        self._section(f, "3. Profil vocal")

        frm_presets = tk.Frame(f)
        frm_presets.pack(pady=4)

        self.preset_var = tk.StringVar(value="Manuel")
        for name in PROFILES:
            tk.Radiobutton(frm_presets, text=name, variable=self.preset_var,
                           value=name, font=("Arial", 10),
                           command=self._apply_preset).pack(side="left", padx=8)

        # --- Bloc 4 : Parametres manuels ---
        self._section(f, "4. Parametres")

        self.s_pitch   = self._slider(f, "Hauteur (Pitch ratio)",
                                      "0.5 = Tres grave  |  1.0 = Original  |  1.5 = Tres aigu",
                                      0.5, 1.5, 0.01, 1.0)
        self.s_formant = self._slider(f, "Timbre (Formant ratio)",
                                      "0.7 = Large/Grave  |  1.0 = Original  |  1.3 = Fin/Aigu",
                                      0.7, 1.3, 0.01, 1.0)
        self.s_range   = self._slider(f, "Melodie (Pitch range)",
                                      "0.0 = Robotique  |  1.0 = Naturel  |  2.0 = Exagere",
                                      0.0, 2.0, 0.05, 1.0)
        self.s_speed   = self._slider(f, "Vitesse (Tempo)",
                                      "0.5 = Lent  |  1.0 = Normal  |  1.5 = Rapide",
                                      0.5, 1.5, 0.05, 1.0)

        tk.Frame(f, height=20).pack()  # espace bas

    def _section(self, parent, title):
        frm = tk.Frame(parent, bg="#ddd", height=1)
        frm.pack(fill="x", padx=20, pady=(12, 2))
        tk.Label(parent, text=title,
                 font=("Arial", 10, "bold"), fg="#333").pack(anchor="w", padx=20)

    def _info_row(self, parent, label):
        frm = tk.Frame(parent, bg="#f5f5f5")
        frm.pack(fill="x", padx=10, pady=2)
        tk.Label(frm, text=label + " :", font=("Arial", 9), fg="#555",
                 bg="#f5f5f5", width=20, anchor="w").pack(side="left")
        lbl = tk.Label(frm, text="—", font=("Arial", 9, "bold"), fg="#222", bg="#f5f5f5")
        lbl.pack(side="left")
        return lbl

    def _slider(self, parent, label, hint, from_, to, resolution, default):
        tk.Label(parent, text=label,
                 font=("Arial", 9, "bold")).pack(anchor="w", padx=20, pady=(6, 0))
        tk.Label(parent, text=hint,
                 font=("Arial", 8), fg="#888").pack(anchor="w", padx=20)
        s = tk.Scale(parent, from_=from_, to=to, resolution=resolution,
                     orient=tk.HORIZONTAL, length=500,
                     command=lambda _: self._on_slider_change())
        s.set(default)
        s.pack(padx=20)
        return s

    # -----------------------------------------------------------------------
    # Logique
    # -----------------------------------------------------------------------
    def _pick_file(self):
        path = filedialog.askopenfilename(
            title="Choisir un fichier audio",
            filetypes=[("Fichiers audio", "*.mp3 *.wav *.flac *.ogg *.m4a"), ("Tous", "*.*")]
        )
        if not path:
            return

        self.input_path = Path(path)
        self.lbl_file.config(text=str(self.input_path), fg="#222")
        self._status("Analyse en cours...")
        self.root.update()

        try:
            self.analysis = analyze_voice(self.input_path)
            self._update_analysis_display()
            self._apply_preset()
            self._status("Fichier charge et analyse.")
        except Exception as e:
            messagebox.showerror("Erreur d'analyse", str(e))
            self._status("Erreur lors de l'analyse.")

    def _update_analysis_display(self):
        a = self.analysis
        self.lbl_pitch.config(   text=f"{a['pitch_median']:.1f} Hz")
        self.lbl_range.config(   text=f"{a['pitch_range']:.1f} Hz")
        self.lbl_voiced.config(  text=f"{a['voiced_ratio']*100:.0f} %")
        self.lbl_duration.config(text=f"{a['duration']:.1f} s")
        self.lbl_sr.config(      text=f"{a['sample_rate']} Hz")

    def _apply_preset(self):
        name = self.preset_var.get()
        if name == "Manuel" or PROFILES[name] is None:
            return
        p = PROFILES[name]
        self.s_pitch.set(p["pitch"])
        self.s_formant.set(p["formant"])
        self.s_range.set(p["range"])
        self.s_speed.set(p["speed"])

    def _on_slider_change(self):
        self.preset_var.set("Manuel")

    def _get_params(self):
        return (
            self.s_pitch.get(),
            self.s_formant.get(),
            self.s_range.get(),
            self.s_speed.get(),
        )

    def _check_ready(self) -> bool:
        if not self.input_path or not self.analysis:
            messagebox.showwarning("Attention", "Veuillez d'abord charger un fichier audio.")
            return False
        return True

    def _preview(self):
        if not self._check_ready():
            return
        self._status("Generation de l'apercu...")
        self.root.update()

        temp_in = None
        try:
            snd_src = parselmouth.Sound(str(self.input_path))
            if snd_src.n_channels > 1:
                snd_src = snd_src.convert_to_mono()
            snd_src = snd_src.extract_part(0, min(3.0, snd_src.duration))

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                temp_in = tmp.name
            snd_src.save(temp_in, "WAV")

            analysis_preview = analyze_voice(Path(temp_in))
            result = transform_audio(Path(temp_in), *self._get_params(), analysis_preview)

            tmp_out = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            self.temp_out = tmp_out.name
            tmp_out.close()
            result.save(self.temp_out, "WAV")

            play_wav(self.temp_out)
            self._status("Lecture de l'apercu (3s)...")

        except Exception as e:
            messagebox.showerror("Erreur apercu", str(e))
            self._status("Erreur lors de l'apercu.")
        finally:
            if temp_in and os.path.exists(temp_in):
                os.remove(temp_in)

    def _export(self):
        if not self._check_ready():
            return

        preset   = self.preset_var.get().replace(" ", "_").lower()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"{self.input_path.stem}_{preset}_{timestamp}.wav"

        out_path = filedialog.asksaveasfilename(
            title="Exporter le fichier transforme",
            defaultextension=".wav",
            initialfile=default_name,
            filetypes=[("Fichier WAV", "*.wav")]
        )
        if not out_path:
            return

        self._status("Traitement en cours...")
        self.root.update()

        try:
            result = transform_audio(self.input_path, *self._get_params(), self.analysis)
            result.save(out_path, "WAV")
            self._status(f"Exporte : {Path(out_path).name}")
            messagebox.showinfo("Termine", f"Fichier exporte :\n{out_path}")
        except Exception as e:
            messagebox.showerror("Erreur export", str(e))
            self._status("Erreur lors de l'export.")

    def _status(self, msg: str):
        self.lbl_status.config(text=msg)

# ---------------------------------------------------------------------------
# Point d'entree
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    root = tk.Tk()
    app  = VoixoApp(root)
    root.mainloop()