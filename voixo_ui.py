import os
import sys
import tempfile
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
from datetime import datetime

from core import (
    analyze_voice,
    transform_audio,
    save_audio,
    PROFILES,
    compute_params,
)

# ---------------------------------------------------------------------------
# FFmpeg
# ---------------------------------------------------------------------------
def _setup_ffmpeg():
    ffmpeg_bin = Path(__file__).parent / "ffmpeg-N-123477-g5640bd3a4f-win64-gpl" / "bin"
    if str(ffmpeg_bin) not in os.environ.get("PATH", ""):
        os.environ["PATH"] = str(ffmpeg_bin) + os.pathsep + os.environ["PATH"]

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
        self.root       = root
        self.root.title("Voixo - Laboratoire vocal")
        self.root.geometry("580x700")
        self.root.resizable(True, True)

        self.input_path = None
        self.analysis   = None
        self.temp_out   = None

        self._build_ui()
        _setup_ffmpeg()

    def _build_ui(self):

        # Barre d'actions fixe en bas
        frm_bottom = tk.Frame(self.root, bg="#f0f0f0", bd=1, relief="raised")
        frm_bottom.pack(side="bottom", fill="x")

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

        # Zone scrollable
        canvas    = tk.Canvas(self.root, borderwidth=0, highlightthickness=0)
        scrollbar = tk.Scrollbar(self.root, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        self.frame    = tk.Frame(canvas)
        self.frame_id = canvas.create_window((0, 0), window=self.frame, anchor="nw")

        self.frame.bind("<Configure>",
                        lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>",
                    lambda e: canvas.itemconfig(self.frame_id, width=e.width))
        canvas.bind_all("<MouseWheel>",
                        lambda e: canvas.yview_scroll(-1 * (e.delta // 120), "units"))

        f = self.frame

        tk.Label(f, text="Voixo — Laboratoire vocal",
                 font=("Arial", 15, "bold"), fg="#222").pack(pady=(20, 4))
        tk.Label(f, text="Modification et anonymisation de voix",
                 font=("Arial", 9), fg="#888").pack(pady=(0, 16))

        # Bloc 1 : Fichier source
        self._section(f, "1. Fichier source")
        self.lbl_file = tk.Label(f, text="Aucun fichier selectionne",
                                 font=("Arial", 9), fg="#666", wraplength=480)
        self.lbl_file.pack(padx=20, pady=4)
        tk.Button(f, text="Choisir un fichier audio",
                  command=self._pick_file,
                  bg="#1976D2", fg="white", font=("Arial", 10, "bold"),
                  pady=8, width=36).pack(pady=(0, 4))

        # Bloc 2 : Analyse Praat
        self._section(f, "2. Analyse Praat")
        frm_analysis = tk.Frame(f, bg="#f5f5f5", bd=1, relief="solid")
        frm_analysis.pack(fill="x", padx=20, pady=4)
        self.lbl_pitch    = self._info_row(frm_analysis, "Pitch median")
        self.lbl_range    = self._info_row(frm_analysis, "Etendue pitch")
        self.lbl_voiced   = self._info_row(frm_analysis, "Ratio voix active")
        self.lbl_duration = self._info_row(frm_analysis, "Duree")
        self.lbl_sr       = self._info_row(frm_analysis, "Sample rate")

        # Bloc 3 : Profil vocal
        self._section(f, "3. Profil vocal")
        frm_presets = tk.Frame(f)
        frm_presets.pack(pady=4)
        self.preset_var = tk.StringVar(value="Manuel")
        for name in PROFILES:
            tk.Radiobutton(frm_presets, text=name, variable=self.preset_var,
                           value=name, font=("Arial", 10),
                           command=self._apply_preset).pack(side="left", padx=8)

        # Bloc 4 : Parametres
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

        tk.Frame(f, height=20).pack()

    def _section(self, parent, title):
        tk.Frame(parent, bg="#ddd", height=1).pack(fill="x", padx=20, pady=(12, 2))
        tk.Label(parent, text=title,
                 font=("Arial", 10, "bold"), fg="#333").pack(anchor="w", padx=20)

    def _info_row(self, parent, label):
        frm = tk.Frame(parent, bg="#f5f5f5")
        frm.pack(fill="x", padx=10, pady=2)
        tk.Label(frm, text=label + " :", font=("Arial", 9), fg="#555",
                 bg="#f5f5f5", width=20, anchor="w").pack(side="left")
        lbl = tk.Label(frm, text="—", font=("Arial", 9, "bold"),
                       fg="#222", bg="#f5f5f5")
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

    def _pick_file(self):
        path = filedialog.askopenfilename(
            title="Choisir un fichier audio",
            filetypes=[("Fichiers audio", "*.mp3 *.wav *.flac *.ogg *.m4a"),
                       ("Tous", "*.*")]
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
        self.lbl_voiced.config(  text=f"{a['voiced_ratio'] * 100:.0f} %")
        self.lbl_duration.config(text=f"{a['duration']:.1f} s")
        self.lbl_sr.config(      text=f"{a['sample_rate']} Hz")

    def _apply_preset(self):
        name = self.preset_var.get()
        if name == "Manuel" or PROFILES[name] is None or self.analysis is None:
            return
        params = compute_params(self.analysis, name)
        pitch_ratio = round(params["target_pitch"] / self.analysis["pitch_median"], 2)
        self.s_pitch.set(pitch_ratio)
        self.s_formant.set(params["formant_ratio"])
        self.s_range.set(params["range_ratio"])
        self.s_speed.set(params["speed_ratio"])

    def _on_slider_change(self):
        self.preset_var.set("Manuel")

    def _get_params(self) -> dict:
        pitch_median = self.analysis["pitch_median"] if self.analysis else 150.0
        target_pitch = max(50.0, min(800.0, pitch_median * self.s_pitch.get()))
        return {
            "target_pitch":  target_pitch,
            "formant_ratio": self.s_formant.get(),
            "range_ratio":   self.s_range.get(),
            "speed_ratio":   self.s_speed.get(),
        }

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
            import parselmouth as _pm
            snd_src = _pm.Sound(str(self.input_path))
            if snd_src.n_channels > 1:
                snd_src = snd_src.convert_to_mono()
            snd_src = snd_src.extract_part(0, min(3.0, snd_src.duration))

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                temp_in = tmp.name
            snd_src.save(temp_in, "WAV")

            analysis_preview = analyze_voice(Path(temp_in))
            target_pitch = max(50.0, min(800.0,
                               analysis_preview["pitch_median"] * self.s_pitch.get()))

            result = transform_audio(
                Path(temp_in),
                target_pitch,
                self.s_formant.get(),
                self.s_range.get(),
                self.s_speed.get(),
            )
            tmp_out = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            self.temp_out = tmp_out.name
            tmp_out.close()
            save_audio(result, Path(self.temp_out))
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
        preset       = self.preset_var.get().replace(" ", "_").lower()
        timestamp    = datetime.now().strftime("%Y%m%d_%H%M%S")
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
            p = self._get_params()
            result = transform_audio(
                self.input_path,
                p["target_pitch"],
                p["formant_ratio"],
                p["range_ratio"],
                p["speed_ratio"],
            )
            save_audio(result, Path(out_path))
            self._status(f"Exporte : {Path(out_path).name}")
            messagebox.showinfo("Termine", f"Fichier exporte :\n{out_path}")
        except Exception as e:
            messagebox.showerror("Erreur export", str(e))
            self._status("Erreur lors de l'export.")

    def _status(self, msg: str):
        self.lbl_status.config(text=msg)


if __name__ == "__main__":
    root = tk.Tk()
    app  = VoixoApp(root)
    root.mainloop()