import streamlit as st
import os
import tempfile
import time
from moviepy.editor import VideoFileClip
import whisper
import pandas as pd
from fpdf import FPDF
import base64
import moviepy.config as moviepy_config

# Spécifier le chemin vers ffmpeg si nécessaire
# moviepy_config.change_settings({"FFMPEG_BINARY": "/chemin/complet/vers/ffmpeg"})

# Configuration de la page
st.set_page_config(
    page_title="Transcription Vidéo - Outil Entreprise",
    page_icon="🎥",
    layout="wide"
)

# Titre et description
st.title("Transcription Vidéo Automatique")
st.markdown("### Convertissez facilement vos vidéos en texte")
st.markdown("Cet outil vous permet de transcrire le contenu audio de vos vidéos et de télécharger le résultat en différents formats.")

# Fonction pour extraire l'audio
def extract_audio(video_path, audio_path):
    """Extraire l'audio d'une vidéo"""
    with st.spinner("Extraction de l'audio en cours..."):
        video = VideoFileClip(video_path)
        audio = video.audio
        audio.write_audiofile(audio_path, verbose=False, logger=None)
        video.close()
    return audio_path

# Fonction pour transcrire avec Whisper
def transcribe_with_whisper(audio_path, language=None):
    """Transcription avec le modèle Whisper"""
    with st.spinner("Transcription avec Whisper en cours (cela peut prendre quelques minutes)..."):
        model = whisper.load_model("base")
        result = model.transcribe(audio_path, language=language)
    return result["text"]

# Fonctions pour télécharger les fichiers
def get_download_link(text, filename, format_type):
    """Générer un lien de téléchargement pour différents formats"""
    if format_type == "txt":
        # Format TXT
        b64 = base64.b64encode(text.encode()).decode()
        href = f'<a href="data:file/txt;base64,{b64}" download="{filename}.txt">Télécharger en TXT</a>'
    elif format_type == "md":
        # Format Markdown
        md_text = f"# Transcription\n\n{text}"
        b64 = base64.b64encode(md_text.encode()).decode()
        href = f'<a href="data:file/markdown;base64,{b64}" download="{filename}.md">Télécharger en MD</a>'
    elif format_type == "pdf":
        # Format PDF
        pdf = FPDF()
        pdf.add_page()
        
        # Essayer d'utiliser DejaVu pour les caractères spéciaux français
        try:
            pdf.add_font('DejaVu', '', 'DejaVuSansCondensed.ttf', uni=True)
            pdf.set_font('DejaVu', '', 12)
        except RuntimeError:
            pdf.set_font("Arial", size=12)
        
        # Séparation du texte en lignes pour éviter les dépassements de page
        text_lines = text.split('\n')
        for line in text_lines:
            # Traiter les longues lignes
            while len(line) > 0:
                if len(line) > 75:  # Nombre approximatif de caractères par ligne
                    # Essayer d'encoder en utf8 si possible
                    try:
                        pdf.multi_cell(0, 10, line[:75])
                    except:
                        # Fallback pour les caractères spéciaux
                        pdf.multi_cell(0, 10, line[:75].encode('latin-1', 'replace').decode('latin-1'))
                    line = line[75:]
                else:
                    try:
                        pdf.multi_cell(0, 10, line)
                    except:
                        pdf.multi_cell(0, 10, line.encode('latin-1', 'replace').decode('latin-1'))
                    line = ""
        
        pdf_output = pdf.output(dest="S").encode("latin1", errors="replace")
        b64 = base64.b64encode(pdf_output).decode()
        href = f'<a href="data:application/pdf;base64,{b64}" download="{filename}.pdf">Télécharger en PDF</a>'
    
    return href

def check_ffmpeg():
    """Vérifier si ffmpeg est installé et accessible"""
    import subprocess
    try:
        subprocess.run(['ffmpeg', '-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        return False

def main():
    # Vérification de ffmpeg
    if not check_ffmpeg():
        st.error("""
        ⚠️ ERREUR: ffmpeg n'a pas été trouvé sur votre système. 
        
        Pour résoudre ce problème:
        1. Installez ffmpeg sur votre système
        2. OU spécifiez le chemin dans le code (décommentez et modifiez la ligne 'moviepy_config.change_settings')
        
        Pour plus d'informations sur l'installation de ffmpeg, consultez: https://ffmpeg.org/download.html
        """)
        st.stop()
    
    # Sélection de la langue
    language_options = {
        "Français": "fr",
        "Anglais": "en",
        "Espagnol": "es",
        "Allemand": "de",
        "Italien": "it",
        "Détection automatique": None
    }
    selected_language_name = st.selectbox("Sélectionnez la langue de la vidéo", options=list(language_options.keys()))
    selected_language = language_options[selected_language_name]
    
    # Chargement de la vidéo
    uploaded_file = st.file_uploader("Chargez votre fichier vidéo", type=['mp4', 'avi', 'mov', 'mkv'])
    
    if uploaded_file is not None:
        # Informations sur le fichier
        file_details = {"Nom du fichier": uploaded_file.name, "Taille": f"{uploaded_file.size / (1024*1024):.2f} MB"}
        st.write("Détails du fichier:")
        st.json(file_details)
        
        # Créer un dossier temporaire pour le traitement
        with tempfile.TemporaryDirectory() as temp_dir:
            # Sauvegarder la vidéo téléchargée
            temp_video_path = os.path.join(temp_dir, uploaded_file.name)
            with open(temp_video_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            # Extraire le nom de base pour les fichiers générés
            file_base_name = os.path.splitext(uploaded_file.name)[0]
            temp_audio_path = os.path.join(temp_dir, f"{file_base_name}.wav")
            
            # Bouton pour lancer la transcription
            if st.button("Lancer la transcription"):
                # Extraire l'audio
                try:
                    extract_audio(temp_video_path, temp_audio_path)
                    st.success("Audio extrait avec succès!")
                    
                    # Transcrire l'audio
                    try:
                        transcription = transcribe_with_whisper(temp_audio_path, selected_language)
                        st.success("Transcription terminée!")
                        
                        # Afficher la transcription
                        st.subheader("Résultat de la transcription")
                        st.text_area("Texte transcrit", transcription, height=300)
                        
                        # Options de téléchargement
                        st.subheader("Télécharger la transcription")
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            st.markdown(get_download_link(transcription, file_base_name, "txt"), unsafe_allow_html=True)
                        
                        with col2:
                            st.markdown(get_download_link(transcription, file_base_name, "md"), unsafe_allow_html=True)
                        
                        with col3:
                            st.markdown(get_download_link(transcription, file_base_name, "pdf"), unsafe_allow_html=True)
                        
                        # Ajout d'informations de traitement
                        with st.expander("Informations de traitement"):
                            st.write(f"Langue utilisée: {selected_language_name}")
                            st.write(f"Modèle de transcription: Whisper (base)")
                            st.write(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
                            
                    except Exception as e:
                        st.error(f"Erreur lors de la transcription: {str(e)}")
                
                except Exception as e:
                    st.error(f"Erreur lors de l'extraction audio: {str(e)}")

    # Ajout d'informations sur l'utilisation
    with st.expander("Instructions d'utilisation"):
        st.write("""
        1. Sélectionnez la langue de la vidéo (ou détection automatique)
        2. Cliquez sur 'Parcourir' pour charger votre fichier vidéo
        3. Appuyez sur 'Lancer la transcription'
        4. Une fois la transcription terminée, vous pouvez la visualiser et la télécharger dans différents formats
        """)
    
    # Pied de page
    st.markdown("---")
    st.markdown("Outil de transcription vidéo développé pour usage interne en entreprise")

if __name__ == "__main__":
    main()
