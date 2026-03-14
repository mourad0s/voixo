"""
Schemas Pydantic — typage des requetes et reponses de l'API.

Pydantic valide automatiquement les donnees entrantes et sortantes.
Si un client envoie "formant_ratio": "abc", FastAPI retourne une erreur
422 claire avant meme d'appeler le core/.
"""

from pydantic import BaseModel, Field


class AnalysisResponse(BaseModel):
    """Reponse de POST /analyze — caracteristiques acoustiques mesurees par Praat."""

    pitch_median:  float = Field(description="Pitch median en Hz")
    pitch_range:   float = Field(description="Etendue pitch (p90 - p10) en Hz")
    voiced_ratio:  float = Field(description="Ratio de duree voisee (0.0 - 1.0)")
    duration:      float = Field(description="Duree totale en secondes")
    sample_rate:   int   = Field(description="Frequence d'echantillonnage en Hz")
    channels:      int   = Field(description="Nombre de canaux du fichier source")


class TransformRequest(BaseModel):
    """
    Parametres de transformation pour POST /transform.
    Tous ont des valeurs par defaut — on peut n'envoyer que ce qu'on veut changer.
    """

    profile:       str   = Field(default="Manuel",
                                 description="Nom du profil preset (Manuel = parametres manuels)")
    pitch_ratio:   float = Field(default=1.0,  ge=0.5,  le=1.5,
                                 description="Ratio de hauteur (1.0 = original)")
    formant_ratio: float = Field(default=1.0,  ge=0.7,  le=1.3,
                                 description="Ratio de timbre (1.0 = original)")
    range_ratio:   float = Field(default=1.0,  ge=0.0,  le=2.0,
                                 description="Ratio d'etendue melodique (1.0 = naturel)")
    speed_ratio:   float = Field(default=1.0,  ge=0.5,  le=1.5,
                                 description="Ratio de vitesse (1.0 = normal)")