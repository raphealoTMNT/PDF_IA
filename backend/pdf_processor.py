import json
import os
from datetime import datetime
from pathlib import Path
import PyPDF2
import re

class PDFProcessor:
    def __init__(self):
        self.data_dir = Path("data")
        self.data_dir.mkdir(exist_ok=True)
        
    def extract_text_from_pdf(self, pdf_path):
        """
        Extrait le texte d'un fichier PDF
        """
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                
                for page_num in range(len(pdf_reader.pages)):
                    page = pdf_reader.pages[page_num]
                    text += page.extract_text() + "\n"
                
                return text.strip()
        except Exception as e:
            print(f"Erreur lors de l'extraction du PDF {pdf_path}: {str(e)}")
            return None
     
    def analyze_pdf_content(self, text, filename):
        """
        Analyse le contenu du PDF et extrait des métadonnées
        """
        if not text:
            return None
            
        # Statistiques de base
        word_count = len(text.split())
        char_count = len(text)
        line_count = len(text.split('\n'))
        
        # Extraction de mots-clés (mots de plus de 4 caractères, fréquents)
        words = re.findall(r'\b\w{4,}\b', text.lower())
        word_freq = {}
        for word in words:
            word_freq[word] = word_freq.get(word, 0) + 1
        
        # Top 10 des mots les plus fréquents
        top_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:10]
        
        # Recherche de patterns spécifiques
        emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
        urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', text)
        dates = re.findall(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b', text)
        
        return {
            'filename': filename,
            'extraction_date': datetime.now().isoformat(),
            'statistics': {
                'word_count': word_count,
                'character_count': char_count,
                'line_count': line_count
            },
            'top_keywords': top_words,
            'extracted_data': {
                'emails': list(set(emails)),
                'urls': list(set(urls)),
                'dates': list(set(dates))
            },
            'content_preview': text[:500] + "..." if len(text) > 500 else text,
            'full_content': text  # Ajout du contenu complet
        }

    def save_to_json(self, data, filename_prefix):
        """
        Sauvegarde les données extraites en format JSON
        """
        if not data:
            return None
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_filename = f"{filename_prefix}_{timestamp}.json"
        json_path = self.data_dir / json_filename
        
        try:
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            return str(json_path)
        except Exception as e:
            print(f"Erreur lors de la sauvegarde JSON: {str(e)}")
            return None
     
    def process_pdf_file(self, pdf_path, file_type="document"):
        """
        Traite un fichier PDF complet: extraction + analyse + sauvegarde JSON
        """
        filename = os.path.basename(pdf_path)
        
        # Extraction du texte
        extracted_text = self.extract_text_from_pdf(pdf_path)
        
        if not extracted_text:
            return None
        
        # Analyse du contenu
        analysis_data = self.analyze_pdf_content(extracted_text, filename)
        
        if not analysis_data:
            return None
        
        # Ajout du type de fichier
        analysis_data['file_type'] = file_type
        analysis_data['original_path'] = pdf_path
        
        # Sauvegarde en JSON
        json_path = self.save_to_json(analysis_data, filename.replace('.pdf', ''))
        
        if json_path:
            analysis_data['json_path'] = json_path
        
        return analysis_data