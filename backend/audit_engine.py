import json
import os
import re
import time
from datetime import datetime
from typing import Dict, List, Tuple, Any
from openai import OpenAI  # Utilisé pour l'API Groq via le SDK OpenAI
from backend.pdf_processor import PDFProcessor
import fitz  # PyMuPDF
import base64
from io import BytesIO

class PedagogicalAuditEngine:
    """
    Moteur d'audit pédagogique utilisant Groq AI pour évaluer des contenus éducatifs
    selon une grille de critères prédéfinie.
    """
    
    def __init__(self, groq_api_key: str, config_path: str = "config/grille_pedagogique.json"):
        """
        Initialise le moteur d'audit avec la clé API Groq et la grille d'évaluation.
        
        Args:
            groq_api_key (str): Clé API Groq
            config_path (str): Chemin vers la grille pédagogique JSON
        """
        # Client Groq utilisant le SDK OpenAI avec l'endpoint Groq
        self.groq_client = OpenAI(
            api_key=groq_api_key,
            base_url="https://api.groq.com/openai/v1"
        )
        self.pdf_processor = PDFProcessor()
        self.config_path = config_path
        self.grille = self._load_grille()
        self.subject_experts = self._load_subject_experts()
        self.current_subject = None
        
    def _load_grille(self) -> Dict:
        """Charge la grille pédagogique depuis le fichier JSON."""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Grille pédagogique non trouvée : {self.config_path}")
    
    def _load_subject_experts(self) -> Dict:
        """Charge les profils d'experts par matière."""
        try:
            with open("config/subject_experts.json", 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print("Fichier des experts par matière non trouvé, utilisation du mode générique")
            return {"subjects": {}}
    
    def set_subject_context(self, subject_key: str):
        """Définit le contexte de matière pour l'audit."""
        if subject_key in self.subject_experts.get("subjects", {}):
            self.current_subject = subject_key
            print(f"Contexte expert défini pour: {self.subject_experts['subjects'][subject_key]['name']}")
        else:
            self.current_subject = None
            print("Contexte générique utilisé")
    
    def get_available_subjects(self) -> List[str]:
        """Retourne la liste des matières disponibles."""
        return list(self.subject_experts.get("subjects", {}).keys())
    
    def get_subject_expert_info(self, subject: str) -> Dict:
        """Retourne les informations détaillées d'un expert pour une matière donnée."""
        return self.subject_experts.get("subjects", {}).get(subject, {})

    def _extract_text_content(self, pdf_path: str) -> Dict:
        """Extrait le contenu textuel du PDF."""
        result = self.pdf_processor.process_pdf_file(pdf_path)
        if result is None:
            return {'content': '', 'statistics': {'page_count': 0, 'word_count': 0}}
        
        # Adapter la structure pour correspondre à ce qui est attendu
        return {
            'content': result.get('full_content', ''),
            'statistics': {
                'page_count': 1,  # PyPDF2 ne donne pas facilement le nombre de pages
                'word_count': result.get('statistics', {}).get('word_count', 0)
            }
        }
    
    def _extract_chapters(self, text_content: str) -> List[Dict]:
        """
        Extrait et identifie les chapitres du document.
        
        Returns:
            List[Dict]: Liste des chapitres avec titre et contenu
        """
        chapters = []
        
        # Patterns pour identifier les chapitres
        chapter_patterns = [
            r'(?i)chapitre\s+(\d+|[ivx]+)\s*[:.\-]?\s*(.+?)(?=\n)',
            r'(?i)partie\s+(\d+|[ivx]+)\s*[:.\-]?\s*(.+?)(?=\n)',
            r'(?i)section\s+(\d+(?:\.\d+)*)\s*[:.\-]?\s*(.+?)(?=\n)',
            r'(?i)^(\d+(?:\.\d+)*)\s*[:.\-]\s*(.+?)(?=\n)',
            r'(?i)^([A-Z][^\n]{10,80})(?=\n\n)'
        ]
        
        text_lines = text_content.split('\n')
        current_chapter = None
        chapter_content = []
        
        for i, line in enumerate(text_lines):
            line = line.strip()
            if not line:
                continue
                
            # Vérifier si la ligne correspond à un titre de chapitre
            is_chapter_title = False
            chapter_title = ""
            
            for pattern in chapter_patterns:
                match = re.match(pattern, line)
                if match:
                    is_chapter_title = True
                    if len(match.groups()) >= 2:
                        chapter_title = f"{match.group(1)} - {match.group(2)}"
                    else:
                        chapter_title = match.group(1) if match.group(1) else line
                    break
            
            if is_chapter_title:
                # Sauvegarder le chapitre précédent
                if current_chapter and chapter_content:
                    chapters.append({
                        'title': current_chapter,
                        'content': '\n'.join(chapter_content),
                        'word_count': len(' '.join(chapter_content).split())
                    })
                
                # Commencer un nouveau chapitre
                current_chapter = chapter_title
                chapter_content = []
            else:
                if current_chapter:
                    chapter_content.append(line)
        
        # Ajouter le dernier chapitre
        if current_chapter and chapter_content:
            chapters.append({
                'title': current_chapter,
                'content': '\n'.join(chapter_content),
                'word_count': len(' '.join(chapter_content).split())
            })
        
        # Si aucun chapitre n'est détecté, traiter tout le contenu comme un seul chapitre
        if not chapters:
            chapters.append({
                'title': 'Document complet',
                'content': text_content,
                'word_count': len(text_content.split())
            })
        
        return chapters
    
    def _analyze_chapter_conformity(self, chapter: Dict) -> Dict:
        """
        Analyse la conformité d'un chapitre selon les critères pédagogiques.
        
        Args:
            chapter (Dict): Chapitre à analyser
            
        Returns:
            Dict: Analyse de conformité du chapitre
        """
        prompt = f"""
        Tu es un expert en pédagogie. Analyse ce chapitre de cours pour vérifier sa conformité pédagogique.
        
        CHAPITRE : {chapter['title']}
        CONTENU :
        {chapter['content'][:3000]}
        
        CRITÈRES À VÉRIFIER :
        1. OBJECTIFS : Le chapitre définit-il clairement ses objectifs d'apprentissage ?
        2. COMPÉTENCES : Les compétences à acquérir sont-elles explicites ?
        3. CONTENU : Le contenu est-il structuré, progressif et adapté ?
        4. RÉFÉRENCES : Y a-t-il des références bibliographiques ou ressources ?
        5. VOLUME : Le volume de contenu est-il approprié (cours/TD/TP) ?
        
        RÉPONSE ATTENDUE (FORMAT JSON) :
        {{
            "objectifs": {{
                "present": true/false,
                "clairs": true/false,
                "score": 0-5,
                "commentaire": "analyse détaillée"
            }},
            "competences": {{
                "definies": true/false,
                "explicites": true/false,
                "score": 0-5,
                "commentaire": "analyse détaillée"
            }},
            "contenu": {{
                "structure": true/false,
                "progression": true/false,
                "adapte": true/false,
                "score": 0-5,
                "commentaire": "analyse détaillée"
            }},
            "references": {{
                "presentes": true/false,
                "pertinentes": true/false,
                "score": 0-5,
                "commentaire": "analyse détaillée"
            }},
            "volume": {{
                "approprie": true/false,
                "equilibre_cours_td_tp": true/false,
                "score": 0-5,
                "commentaire": "analyse détaillée"
            }},
            "score_global": 0-5,
            "conformite": "conforme"/"partiellement_conforme"/"non_conforme",
            "recommandations": ["recommandation1", "recommandation2"]
        }}
        """
        
        try:
            response = self.groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "Tu es un expert en évaluation pédagogique. Réponds uniquement en JSON valide."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1500
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # Nettoyage du JSON
            if result_text.startswith('```json'):
                result_text = result_text[7:-3]
            elif result_text.startswith('```'):
                result_text = result_text[3:-3]
                
            result = json.loads(result_text)
            return result
            
        except Exception as e:
            return {
                "objectifs": {"present": False, "clairs": False, "score": 0, "commentaire": f"Erreur d'analyse: {str(e)}"},
                "competences": {"definies": False, "explicites": False, "score": 0, "commentaire": f"Erreur d'analyse: {str(e)}"},
                "contenu": {"structure": False, "progression": False, "adapte": False, "score": 0, "commentaire": f"Erreur d'analyse: {str(e)}"},
                "references": {"presentes": False, "pertinentes": False, "score": 0, "commentaire": f"Erreur d'analyse: {str(e)}"},
                "volume": {"approprie": False, "equilibre_cours_td_tp": False, "score": 0, "commentaire": f"Erreur d'analyse: {str(e)}"},
                "score_global": 0,
                "conformite": "non_conforme",
                "recommandations": ["Relancer l'analyse après vérification du contenu"]
            }
    
    def _analyze_criterion(self, criterion_key: str, criterion_data: Dict, text_content: str) -> Dict:
        """
        Analyse un critère spécifique en utilisant l'IA.
        
        Args:
            criterion_key (str): Clé du critère
            criterion_data (Dict): Données du critère
            text_content (str): Contenu textuel à analyser
            
        Returns:
            Dict: Résultat de l'analyse avec score, commentaires et preuves
        """
        
        # Ajout du contexte expert si une matière est sélectionnée
        expert_context = ""
        if self.current_subject and self.current_subject in self.subject_experts.get("subjects", {}):
            subject_data = self.subject_experts["subjects"][self.current_subject]
            expertise = subject_data.get('expertise', {})
            expert_context = f"""
            
CONTEXTE EXPERT - {subject_data['name']} :
{subject_data['analysis_prompt']}

CONCEPTS CLÉS À ÉVALUER :
{', '.join(expertise.get('key_concepts', []))}

CRITÈRES D'ÉVALUATION SPÉCIALISÉS :
{chr(10).join([f"- {key}: {value}" for key, value in expertise.get('evaluation_criteria', {}).items()])}

FOCUS PÉDAGOGIQUE :
{chr(10).join([f"- {focus}" for focus in expertise.get('pedagogical_focus', [])])}
            """
        
        # Construction du prompt pour l'IA
        prompt = f"""
        Tu es un expert en pédagogie{f" spécialisé en {self.subject_experts['subjects'][self.current_subject]['name']}" if self.current_subject else ""} chargé d'évaluer un contenu éducatif selon le critère suivant :
        
        CRITÈRE : {criterion_data['name']}
        DESCRIPTION : {criterion_data['description']}
        INDICATEURS À ÉVALUER :
        {chr(10).join([f"- {indicator}" for indicator in criterion_data['indicators']])}
        
        MOTS-CLÉS À RECHERCHER :
        {', '.join(self.grille['keywords'].get(criterion_key, []))}
        {expert_context}
        
        CONTENU À ANALYSER :
        {text_content[:4000]}  # Limite pour éviter les tokens excessifs
        
        INSTRUCTIONS :
        1. Évalue ce contenu selon les indicateurs listés{" et le contexte expert spécialisé" if self.current_subject else ""}
        2. Attribue une note de 0 à 5 (5 = excellent, 0 = absent/très insuffisant)
        3. Fournis un commentaire détaillé justifiant ta note
        4. Identifie des extraits du texte comme preuves (citations courtes)
        5. Liste les forces et faiblesses identifiées
        6. Propose des recommandations d'amélioration{f" adaptées à l'enseignement de {self.subject_experts['subjects'][self.current_subject]['name']}" if self.current_subject else ""}
        
        RÉPONSE ATTENDUE (FORMAT JSON) :
        {{
            "score": [note de 0 à 5],
            "commentaire": "[analyse détaillée]",
            "preuves": ["extrait1", "extrait2"],
            "forces": ["force1", "force2"],
            "faiblesses": ["faiblesse1", "faiblesse2"],
            "recommandations": ["recommandation1", "recommandation2"]
        }}
        """
        
        # Retry avec délai pour gérer les limites de taux
        max_retries = 3
        retry_delay = 2  # secondes
        
        for attempt in range(max_retries):
            try:
                response = self.groq_client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": f"Tu es un expert en évaluation pédagogique{(' spécialisé en ' + self.subject_experts['subjects'][self.current_subject]['name']) if self.current_subject else ''}. Réponds uniquement en JSON valide."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    max_tokens=1000
                )
                break  # Succès, sortir de la boucle
            except Exception as api_error:
                if "429" in str(api_error) or "rate_limit" in str(api_error).lower():
                    if attempt < max_retries - 1:
                        print(f"Limite de taux atteinte, attente de {retry_delay} secondes...")
                        time.sleep(retry_delay)
                        retry_delay *= 2  # Augmenter le délai exponentiellement
                        continue
                raise api_error  # Re-lancer l'erreur si tous les essais échouent
        
        try:
            
            # Parse de la réponse JSON
            result_text = response.choices[0].message.content.strip()
            
            # Nettoyage du JSON (suppression des balises markdown si présentes)
            if result_text.startswith('```json'):
                result_text = result_text[7:-3]
            elif result_text.startswith('```'):
                result_text = result_text[3:-3]
                
            result = json.loads(result_text)
            
            # Validation et normalisation du score
            result['score'] = max(0, min(5, float(result.get('score', 0))))
            
            return result
            
        except Exception as e:
            print(f"Erreur lors de l'analyse du critère {criterion_key}: {str(e)}")
            return {
                "score": 0,
                "commentaire": f"Erreur d'analyse: {str(e)}",
                "preuves": [],
                "forces": [],
                "faiblesses": ["Analyse impossible"],
                "recommandations": ["Vérifier le contenu et relancer l'analyse"]
            }
    
    def _check_mandatory_sections(self, text_content: str) -> Dict:
        """Vérifie la présence des sections obligatoires."""
        mandatory_sections = self.grille['mandatory_sections']
        found_sections = []
        missing_sections = []
        
        text_lower = text_content.lower()
        
        for section in mandatory_sections:
            # Recherche de mots-clés liés à chaque section
            section_keywords = {
                'introduction': ['introduction', 'présentation', 'avant-propos'],
                'objectifs': ['objectif', 'but', 'finalité', 'compétence'],
                'contenu principal': ['chapitre', 'section', 'partie', 'cours'],
                'conclusion': ['conclusion', 'synthèse', 'bilan', 'résumé']
            }
            
            keywords = section_keywords.get(section, [section])
            if any(keyword in text_lower for keyword in keywords):
                found_sections.append(section)
            else:
                missing_sections.append(section)
        
        return {
            'found_sections': found_sections,
            'missing_sections': missing_sections,
            'completion_rate': len(found_sections) / len(mandatory_sections) * 100
        }
    
    def _count_elements(self, text_content: str) -> Dict:
        """Compte automatiquement les exemples et exercices."""
        text_lower = text_content.lower()
        
        # Patterns pour détecter les exemples
        example_patterns = [
            r'exemple\s*\d*\s*:',
            r'par exemple',
            r'illustration\s*\d*',
            r'cas\s*\d*\s*:'
        ]
        
        # Patterns pour détecter les exercices
        exercise_patterns = [
            r'exercice\s*\d*',
            r'activité\s*\d*',
            r'travail\s*pratique',
            r'tp\s*\d*',
            r'question\s*\d*'
        ]
        
        examples_count = sum(len(re.findall(pattern, text_lower)) for pattern in example_patterns)
        exercises_count = sum(len(re.findall(pattern, text_lower)) for pattern in exercise_patterns)
        
        return {
            'examples_count': examples_count,
            'exercises_count': exercises_count
        }
    
    def _calculate_final_grade(self, scores: Dict) -> Tuple[float, str]:
        """Calcule la note finale et le grade correspondant."""
        total_weighted_score = 0
        total_weight = 0
        
        for criterion_key, result in scores.items():
            if criterion_key in self.grille['criteria']:
                weight = self.grille['criteria'][criterion_key]['weight']
                score = result['score']
                total_weighted_score += (score / 5) * weight
                total_weight += weight
        
        final_score = (total_weighted_score / total_weight) * 100 if total_weight > 0 else 0
        
        # Détermination du grade
        grade = 'E'
        for grade_key, grade_data in self.grille['grading_scale'].items():
            if grade_data['min_score'] <= final_score <= grade_data['max_score']:
                grade = grade_key
                break
        
        return round(final_score, 2), grade
    
    def _generate_global_recommendations(self, scores: Dict, final_score: float) -> Dict:
        """Génère des recommandations globales avec priorités."""
        all_forces = []
        all_weaknesses = []
        all_recommendations = []
        
        # Collecte des forces et faiblesses
        for criterion_key, result in scores.items():
            all_forces.extend(result.get('forces', []))
            all_weaknesses.extend(result.get('faiblesses', []))
            all_recommendations.extend(result.get('recommandations', []))
        
        # Priorisation des recommandations selon le score
        priority_recommendations = []
        
        if final_score < 40:
            priority_recommendations = [
                "Refonte complète du contenu nécessaire",
                "Restructuration de l'organisation pédagogique",
                "Amélioration majeure de la clarté"
            ]
        elif final_score < 55:
            priority_recommendations = [
                "Amélioration de la structure générale",
                "Ajout d'exemples et d'exercices",
                "Clarification des objectifs"
            ]
        elif final_score < 70:
            priority_recommendations = [
                "Enrichissement des exemples concrets",
                "Amélioration des méthodes d'évaluation",
                "Renforcement des références"
            ]
        else:
            priority_recommendations = [
                "Optimisation des détails",
                "Enrichissement des ressources complémentaires"
            ]
        
        return {
            'forces': list(set(all_forces))[:5],  # Top 5 forces uniques
            'faiblesses': list(set(all_weaknesses))[:5],  # Top 5 faiblesses uniques
            'recommandations_prioritaires': priority_recommendations,
            'recommandations_detaillees': list(set(all_recommendations))[:10]
        }
    
    def audit_pdf(self, pdf_path: str, filename: str) -> Dict:
        """
        Effectue un audit complet d'un fichier PDF.
        
        Args:
            pdf_path (str): Chemin vers le fichier PDF
            filename (str): Nom du fichier
            
        Returns:
            Dict: Rapport d'audit complet
        """
        
        print(f"Début de l'audit de {filename}...")
        
        # 1. Extraction du contenu
        try:
            pdf_data = self._extract_text_content(pdf_path)
            text_content = pdf_data.get('content', '')
        except Exception as e:
            return {
                'error': f"Erreur d'extraction PDF: {str(e)}",
                'filename': filename,
                'audit_date': datetime.now().isoformat()
            }
        
        # 2. Analyse par critère
        criterion_scores = {}
        for i, (criterion_key, criterion_data) in enumerate(self.grille['criteria'].items()):
            print(f"Analyse du critère: {criterion_data['name']}")
            criterion_scores[criterion_key] = self._analyze_criterion(
                criterion_key, criterion_data, text_content
            )
            # Délai entre les critères pour éviter les limites de taux
            if i < len(self.grille['criteria']) - 1:  # Pas de délai après le dernier critère
                time.sleep(1)  # 1 seconde entre chaque critère
        
        # 3. Vérification des sections obligatoires
        sections_check = self._check_mandatory_sections(text_content)
        
        # 4. Comptage des éléments
        elements_count = self._count_elements(text_content)
        
        # 5. Calcul de la note finale
        final_score, grade = self._calculate_final_grade(criterion_scores)
        
        # 6. Génération des recommandations globales
        global_recommendations = self._generate_global_recommendations(criterion_scores, final_score)
        
        # 7. Construction du rapport final
        audit_report = {
            'metadata': {
                'filename': filename,
                'audit_date': datetime.now().isoformat(),
                'grille_version': self.grille['metadata']['version'],
                'total_pages': pdf_data.get('statistics', {}).get('page_count', 0),
                'word_count': pdf_data.get('statistics', {}).get('word_count', 0)
            },
            'scores': {
                'final_score': final_score,
                'grade': grade,
                'grade_description': self.grille['grading_scale'][grade]['description'],
                'criteria_scores': criterion_scores
            },
            'analysis': {
                'mandatory_sections': sections_check,
                'elements_count': elements_count,
                'global_recommendations': global_recommendations
            },
            'raw_data': {
                'extracted_text_preview': text_content[:500] + '...' if len(text_content) > 500 else text_content,
                'pdf_statistics': pdf_data.get('statistics', {})
            }
        }
        
        print(f"Audit terminé. Score final: {final_score}/100 (Grade: {grade})")
        
        return audit_report
    
    def audit_pdf_chapter_by_chapter(self, pdf_path: str, filename: str) -> Dict:
        """
        Effectue un audit détaillé chapitre par chapitre d'un fichier PDF.
        Vérifie la conformité de chaque chapitre selon les critères pédagogiques.
        
        Args:
            pdf_path (str): Chemin vers le fichier PDF
            filename (str): Nom du fichier
            
        Returns:
            Dict: Rapport d'audit détaillé avec analyse chapitre par chapitre
        """
        
        print(f"Début de l'audit chapitre par chapitre de {filename}...")
        
        # 1. Extraction du contenu
        try:
            pdf_data = self._extract_text_content(pdf_path)
            text_content = pdf_data.get('content', '')
        except Exception as e:
            return {
                'error': f"Erreur d'extraction PDF: {str(e)}",
                'filename': filename,
                'audit_date': datetime.now().isoformat()
            }
        
        # 2. Extraction des chapitres
        chapters = self._extract_chapters(text_content)
        print(f"Chapitres détectés: {len(chapters)}")
        
        # 3. Analyse de conformité pour chaque chapitre
        chapter_analyses = []
        conformity_summary = {
            'conforme': 0,
            'partiellement_conforme': 0,
            'non_conforme': 0
        }
        
        for i, chapter in enumerate(chapters):
            print(f"Analyse du chapitre {i+1}/{len(chapters)}: {chapter['title'][:50]}...")
            
            chapter_analysis = self._analyze_chapter_conformity(chapter)
            chapter_analysis['chapter_info'] = {
                'title': chapter['title'],
                'word_count': chapter['word_count'],
                'chapter_number': i + 1
            }
            
            chapter_analyses.append(chapter_analysis)
            
            # Mise à jour du résumé de conformité
            conformity = chapter_analysis.get('conformite', 'non_conforme')
            if conformity in conformity_summary:
                conformity_summary[conformity] += 1
            
            # Délai entre les chapitres pour éviter les limites de taux
            if i < len(chapters) - 1:
                time.sleep(2)
        
        # 4. Analyse globale du document (méthode existante)
        print("Analyse globale du document...")
        global_audit = self.audit_pdf(pdf_path, filename)
        
        # 5. Calcul des scores moyens par critère
        criteria_averages = {
            'objectifs': 0,
            'competences': 0,
            'contenu': 0,
            'references': 0,
            'volume': 0
        }
        
        valid_chapters = [ch for ch in chapter_analyses if ch.get('score_global', 0) > 0]
        if valid_chapters:
            for criterion in criteria_averages.keys():
                scores = [ch.get(criterion, {}).get('score', 0) for ch in valid_chapters]
                criteria_averages[criterion] = round(sum(scores) / len(scores), 2) if scores else 0
        
        # 6. Génération de recommandations spécifiques
        all_recommendations = []
        critical_issues = []
        
        for chapter_analysis in chapter_analyses:
            all_recommendations.extend(chapter_analysis.get('recommandations', []))
            
            # Identification des problèmes critiques
            if chapter_analysis.get('conformite') == 'non_conforme':
                critical_issues.append(f"Chapitre '{chapter_analysis['chapter_info']['title']}' non conforme")
        
        # Calcul du score final basé sur la moyenne des scores de conformité
        final_score = round((conformity_summary['conforme'] / len(chapters)) * 100, 2) if chapters else 0
        
        # Détermination du grade
        grade = 'E'
        for grade_key, grade_data in self.grille['grading_scale'].items():
            if grade_data['min_score'] <= final_score <= grade_data['max_score']:
                grade = grade_key
                break
        
        # 7. Construction du rapport final
        audit_report = {
            'metadata': {
                'filename': filename,
                'audit_type': 'chapter_by_chapter',
                'audit_date': datetime.now().isoformat(),
                'grille_version': self.grille['metadata']['version'],
                'total_pages': pdf_data.get('statistics', {}).get('page_count', 0),
                'word_count': pdf_data.get('statistics', {}).get('word_count', 0),
                'chapters_count': len(chapters)
            },
            'scores': {
                'final_score': final_score,
                'grade': grade,
                'grade_description': self.grille['grading_scale'][grade]['description']
            },
            'chapters': chapter_analyses,
            'chapter_analysis': {
                'chapters': chapter_analyses,
                'conformity_summary': conformity_summary,
                'criteria_averages': criteria_averages,
                'conformity_rate': final_score
            },
            'global_analysis': global_audit,
            'synthesis': {
                'critical_issues': list(set(critical_issues)),
                'priority_recommendations': list(set(all_recommendations))[:10],
                'overall_conformity': 'conforme' if conformity_summary['conforme'] > len(chapters) / 2 else 
                                    'partiellement_conforme' if conformity_summary['partiellement_conforme'] > 0 else 
                                    'non_conforme',
                'improvement_areas': [
                    criterion for criterion, score in criteria_averages.items() 
                    if score < 3
                ]
            },
            'recommendations': [{
                'priority': 'high' if final_score < 50 else 'medium' if final_score < 70 else 'low',
                'message': rec
            } for rec in list(set(all_recommendations))[:10]]
        }
        
        print(f"Audit chapitre par chapitre terminé. Conformité globale: {audit_report['synthesis']['overall_conformity']}")
        print(f"Chapitres conformes: {conformity_summary['conforme']}/{len(chapters)}")
        
        return audit_report
    
    def _calculate_grade(self, score: float) -> Dict:
        """Calcule le grade basé sur le score."""
        for grade_key, grade_data in self.grille['grading_scale'].items():
            if grade_data['min_score'] <= score <= grade_data['max_score']:
                return {'grade': grade_key, 'description': grade_data['description']}
        return {'grade': 'E', 'description': 'Non évalué'}
    
    def _calculate_chapter_conformity_summary(self, chapters: List[Dict]) -> Dict:
        """Calcule un résumé de conformité des chapitres."""
        total_chapters = len(chapters)
        if total_chapters == 0:
            return {"conforming_chapters": 0, "total_chapters": 0, "conformity_rate": 0.0}
        
        conforming_chapters = sum(1 for ch in chapters if ch.get('conformite') == 'conforme')
        conformity_rate = (conforming_chapters / total_chapters) * 100
        
        return {
            "conforming_chapters": conforming_chapters,
            "total_chapters": total_chapters,
            "conformity_rate": conformity_rate
        }
    
    def _calculate_criteria_averages(self, chapters: List[Dict]) -> Dict:
        """Calcule les moyennes des critères à travers tous les chapitres."""
        if not chapters:
            return {}
        
        criteria = ['objectifs', 'competences', 'contenu', 'references', 'volume']
        averages = {}
        
        for criterion in criteria:
            scores = [ch.get(criterion, {}).get('score', 0) for ch in chapters]
            averages[criterion] = sum(scores) / len(scores) if scores else 0
        
        return averages

    def audit_pdf_with_support(self, module_path: str, support_path: str, filename: str) -> Dict:
        """
        Effectue un audit complet d'un fichier PDF module avec un document support.
        
        Args:
            module_path (str): Chemin vers le fichier PDF module principal
            support_path (str): Chemin vers le fichier PDF de support
            filename (str): Nom du fichier module
            
        Returns:
            Dict: Rapport d'audit complet
        """
        
        print(f"Début de l'audit de {filename} avec document support...")
        
        # 1. Extraction du contenu des deux fichiers
        try:
            # Contenu du module principal
            module_data = self._extract_text_content(module_path)
            module_content = module_data.get('content', '')
            
            # Contenu du document support
            support_data = self._extract_text_content(support_path)
            support_content = support_data.get('content', '')
            
            # Combinaison des contenus pour l'analyse
            combined_content = f"CONTENU PRINCIPAL DU MODULE:\n{module_content}\n\nDOCUMENT SUPPORT COMPLÉMENTAIRE:\n{support_content}"
            
        except Exception as e:
            return {
                'error': f"Erreur d'extraction PDF: {str(e)}",
                'filename': filename,
                'audit_date': datetime.now().isoformat()
            }
        
        # 2. Analyse par critère avec le contenu combiné
        criterion_scores = {}
        for i, (criterion_key, criterion_data) in enumerate(self.grille['criteria'].items()):
            print(f"Analyse du critère: {criterion_data['name']} (avec support)")
            criterion_scores[criterion_key] = self._analyze_criterion(
                criterion_key, criterion_data, combined_content
            )
            # Délai entre les critères pour éviter les limites de taux
            if i < len(self.grille['criteria']) - 1:  # Pas de délai après le dernier critère
                time.sleep(1)  # 1 seconde entre chaque critère
        
        # 3. Vérification des sections obligatoires sur le contenu combiné
        sections_check = self._check_mandatory_sections(combined_content)
        
        # 4. Comptage des éléments sur le contenu combiné
        elements_count = self._count_elements(combined_content)
        
        # 5. Calcul de la note finale
        final_score, grade = self._calculate_final_grade(criterion_scores)
        
        # 6. Génération des recommandations globales
        global_recommendations = self._generate_global_recommendations(criterion_scores, final_score)
        
        # 7. Construction du rapport final avec informations sur les deux fichiers
        total_word_count = module_data.get('statistics', {}).get('word_count', 0) + support_data.get('statistics', {}).get('word_count', 0)
        total_pages = module_data.get('statistics', {}).get('page_count', 0) + support_data.get('statistics', {}).get('page_count', 0)
        
        audit_report = {
            'metadata': {
                'filename': filename,
                'support_document': True,
                'audit_date': datetime.now().isoformat(),
                'grille_version': self.grille['metadata']['version'],
                'total_pages': total_pages,
                'word_count': total_word_count,
                'module_pages': module_data.get('statistics', {}).get('page_count', 0),
                'support_pages': support_data.get('statistics', {}).get('page_count', 0)
            },
            'scores': {
                'final_score': final_score,
                'grade': grade,
                'grade_description': self.grille['grading_scale'][grade]['description'],
                'criteria_scores': criterion_scores
            },
            'analysis': {
                'mandatory_sections': sections_check,
                'elements_count': elements_count,
                'global_recommendations': global_recommendations
            },
            'raw_data': {
                'extracted_text_preview': combined_content[:500] + '...' if len(combined_content) > 500 else combined_content,
                'module_statistics': module_data.get('statistics', {}),
                'support_statistics': support_data.get('statistics', {})
            }
        }
        
        print(f"Audit terminé (avec support). Score final: {final_score}/100 (Grade: {grade})")
        
        return audit_report
    
    def save_audit_report(self, audit_report: Dict, output_dir: str = "data/audits") -> str:
        """
        Sauvegarde le rapport d'audit en JSON et met à jour l'index.
        
        Args:
            audit_report (Dict): Rapport d'audit
            output_dir (str): Dossier de sortie
            
        Returns:
            str: Chemin du fichier sauvegardé
        """
        
        # Création du nom de fichier unique
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = audit_report['metadata']['filename']
        safe_filename = re.sub(r'[^\w\-_\.]', '_', filename)
        json_filename = f"audit_{safe_filename}_{timestamp}.json"
        json_path = os.path.join(output_dir, json_filename)
        
        # Sauvegarde du rapport
        os.makedirs(output_dir, exist_ok=True)
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(audit_report, f, ensure_ascii=False, indent=2)
        
        # Mise à jour de l'index
        self._update_index(audit_report, json_path)
        
        return json_path
    
    def _update_index(self, audit_report: Dict, json_path: str):
        """Met à jour l'index global des audits."""
        index_path = "data/index.json"
        
        # Chargement de l'index existant
        try:
            with open(index_path, 'r', encoding='utf-8') as f:
                index_data = json.load(f)
        except FileNotFoundError:
            index_data = {
                'metadata': {
                    'created_date': datetime.now().isoformat(),
                    'total_audits': 0,
                    'version': '1.0'
                },
                'audits': []
            }
        
        # Ajout du nouvel audit
        audit_entry = {
            'id': len(index_data['audits']) + 1,
            'filename': audit_report['metadata']['filename'],
            'audit_date': audit_report['metadata']['audit_date'],
            'final_score': audit_report['scores']['final_score'],
            'grade': audit_report['scores']['grade'],
            'json_file': json_path,
            'word_count': audit_report['metadata']['word_count']
        }
        
        index_data['audits'].append(audit_entry)
        index_data['metadata']['total_audits'] = len(index_data['audits'])
        index_data['metadata']['last_updated'] = datetime.now().isoformat()
        
        # Sauvegarde de l'index mis à jour
        with open(index_path, 'w', encoding='utf-8') as f:
            json.dump(index_data, f, ensure_ascii=False, indent=2)
    
    def get_audit_history(self) -> Dict:
        """Récupère l'historique des audits depuis l'index."""
        index_path = "data/index.json"
        
        try:
            with open(index_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {
                'metadata': {'total_audits': 0},
                'audits': []
            }
    
    def generate_pdf_preview(self, pdf_path: str, max_pages: int = 3) -> Dict:
        """Génère une prévisualisation du PDF avec les premières pages et extraits de texte.
        
        Args:
            pdf_path (str): Chemin vers le fichier PDF
            max_pages (int): Nombre maximum de pages à prévisualiser
            
        Returns:
            Dict: Informations de prévisualisation incluant métadonnées, extraits de texte et images
        """
        try:
            doc = fitz.open(pdf_path)
            preview_data = {
                'metadata': {
                    'title': doc.metadata.get('title', 'Sans titre'),
                    'author': doc.metadata.get('author', 'Auteur inconnu'),
                    'page_count': len(doc),
                    'file_size': os.path.getsize(pdf_path)
                },
                'text_excerpts': [],
                'page_images': []
            }
            
            # Extraire le texte des premières pages
            for page_num in range(min(max_pages, len(doc))):
                page = doc[page_num]
                text = page.get_text()
                
                # Nettoyer et limiter le texte
                clean_text = ' '.join(text.split())[:500] + '...' if len(text) > 500 else text
                
                preview_data['text_excerpts'].append({
                    'page': page_num + 1,
                    'text': clean_text
                })
                
                # Générer une image de la page (optionnel, pour une vraie prévisualisation visuelle)
                try:
                    pix = page.get_pixmap(matrix=fitz.Matrix(0.5, 0.5))  # Réduire la taille
                    img_data = pix.tobytes("png")
                    img_base64 = base64.b64encode(img_data).decode()
                    
                    preview_data['page_images'].append({
                        'page': page_num + 1,
                        'image_base64': img_base64
                    })
                except Exception as e:
                    print(f"Erreur lors de la génération de l'image pour la page {page_num + 1}: {e}")
            
            doc.close()
            return preview_data
            
        except Exception as e:
            return {
                'error': f"Erreur lors de la prévisualisation du PDF: {str(e)}",
                'metadata': {'page_count': 0, 'file_size': 0},
                'text_excerpts': [],
                'page_images': []
            }
    
    def load_audit_report(self, json_path: str) -> Dict:
        """Charge un rapport d'audit spécifique."""
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Rapport d'audit non trouvé: {json_path}")