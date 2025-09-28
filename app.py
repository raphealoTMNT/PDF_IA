import streamlit as st
import os
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from backend.audit_engine import PedagogicalAuditEngine
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
import io

# Configuration de la page
st.set_page_config(
    page_title="Audit Pédagogique IA",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Clé API Groq (à sécuriser en production)
GROQ_API_KEY = "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"

# Initialisation des dossiers
for directory in ["data/uploads", "data/audits", "config"]:
    os.makedirs(directory, exist_ok=True)

# Initialisation de l'état de session
if 'audit_engine' not in st.session_state:
    try:
        st.session_state.audit_engine = PedagogicalAuditEngine(GROQ_API_KEY)
    except Exception as e:
        st.error(f"Erreur d'initialisation du moteur d'audit: {str(e)}")
        st.session_state.audit_engine = None

if 'current_audit' not in st.session_state:
    st.session_state.current_audit = None

if 'audit_in_progress' not in st.session_state:
    st.session_state.audit_in_progress = False

# Nouvelles variables pour le workflow en 3 étapes
if 'current_step' not in st.session_state:
    st.session_state.current_step = 1

if 'module_file' not in st.session_state:
    st.session_state.module_file = None

if 'support_file' not in st.session_state:
    st.session_state.support_file = None

if 'module_file_path' not in st.session_state:
    st.session_state.module_file_path = None

if 'support_file_path' not in st.session_state:
    st.session_state.support_file_path = None

def create_gauge_chart(score, title):
    """Crée un graphique en jauge pour afficher un score."""
    fig = go.Figure(go.Indicator(
        mode = "gauge+number+delta",
        value = score,
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': title},
        delta = {'reference': 50},
        gauge = {
            'axis': {'range': [None, 100]},
            'bar': {'color': "darkblue"},
            'steps': [
                {'range': [0, 40], 'color': "lightgray"},
                {'range': [40, 55], 'color': "yellow"},
                {'range': [55, 70], 'color': "orange"},
                {'range': [70, 85], 'color': "lightgreen"},
                {'range': [85, 100], 'color': "green"}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 90
            }
        }
    ))
    
    fig.update_layout(height=300)
    return fig

def create_criteria_chart(criteria_scores):
    """Crée un graphique radar des scores par critère."""
    criteria_names = []
    scores = []
    
    for key, data in criteria_scores.items():
        # Récupération du nom du critère depuis la grille
        if st.session_state.audit_engine:
            criterion_name = st.session_state.audit_engine.grille['criteria'][key]['name']
        else:
            criterion_name = key.replace('_', ' ').title()
        
        criteria_names.append(criterion_name)
        scores.append(data['score'])
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatterpolar(
        r=scores,
        theta=criteria_names,
        fill='toself',
        name='Scores'
    ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 5]
            )
        ),
        showlegend=False,
        title="Scores par Critère",
        height=400
    )
    
    return fig

def export_to_pdf(audit_report):
    """Exporte le rapport d'audit en PDF."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    
    # Titre
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=30,
        textColor=colors.darkblue
    )
    
    story.append(Paragraph(f"Rapport d'Audit Pédagogique", title_style))
    story.append(Paragraph(f"Fichier: {audit_report['metadata']['filename']}", styles['Heading2']))
    story.append(Paragraph(f"Date: {audit_report['metadata']['audit_date'][:10]}", styles['Normal']))
    story.append(Spacer(1, 20))
    
    # Score global
    story.append(Paragraph("Score Global", styles['Heading2']))
    score_text = f"Note finale: {audit_report['scores']['final_score']}/100 (Grade: {audit_report['scores']['grade']})"
    story.append(Paragraph(score_text, styles['Normal']))
    story.append(Paragraph(audit_report['scores']['grade_description'], styles['Normal']))
    story.append(Spacer(1, 20))
    
    # Scores par critère
    story.append(Paragraph("Scores par Critère", styles['Heading2']))
    
    criteria_data = [['Critère', 'Score', 'Commentaire']]
    for key, data in audit_report['scores']['criteria_scores'].items():
        if st.session_state.audit_engine:
            criterion_name = st.session_state.audit_engine.grille['criteria'][key]['name']
        else:
            criterion_name = key.replace('_', ' ').title()
        
        criteria_data.append([
            criterion_name,
            f"{data['score']}/5",
            data['commentaire'][:100] + '...' if len(data['commentaire']) > 100 else data['commentaire']
        ])
    
    criteria_table = Table(criteria_data, colWidths=[2*inch, 1*inch, 3*inch])
    criteria_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    story.append(criteria_table)
    story.append(Spacer(1, 20))
    
    # Recommandations
    story.append(Paragraph("Recommandations Prioritaires", styles['Heading2']))
    for rec in audit_report['analysis']['global_recommendations']['recommandations_prioritaires']:
        story.append(Paragraph(f"• {rec}", styles['Normal']))
    
    doc.build(story)
    buffer.seek(0)
    return buffer

def show_new_audit_workflow():
    """Nouveau workflow d'audit en 3 étapes."""
    
    if not st.session_state.audit_engine:
        st.error("❌ Moteur d'audit non disponible. Vérifiez la configuration.")
        return
    
    # Affichage selon l'étape actuelle
    if st.session_state.current_step == 1:
        show_step1_module_upload()
    elif st.session_state.current_step == 2:
        show_step2_support_upload()
    elif st.session_state.current_step == 3:
        show_step3_analysis_dashboard()

def show_step1_module_upload():
    """Étape 1: Upload du fichier module PDF."""
    st.header("📄 Étape 1: Téléchargement du Module")
    st.write("Téléchargez le fichier PDF du module pédagogique à auditer (obligatoire).")
    
    # Upload de fichier module
    uploaded_file = st.file_uploader(
        "📁 Sélectionnez votre fichier module PDF",
        type=['pdf'],
        help="Formats acceptés: PDF uniquement",
        key="module_uploader"
    )
    
    if uploaded_file is not None:
        # Vérification si le fichier existe déjà
        upload_path = os.path.join("data/uploads", f"module_{uploaded_file.name}")
        
        if os.path.exists(upload_path):
            st.warning(f"⚠️ Le fichier '{uploaded_file.name}' existe déjà dans le dossier uploads.")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔄 Remplacer le fichier", key="replace_module"):
                    with open(upload_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    st.success(f"✅ Fichier '{uploaded_file.name}' remplacé avec succès!")
                    st.session_state.file_replaced = True
            
            with col2:
                if st.button("📂 Utiliser le fichier existant", key="use_existing_module"):
                    st.info(f"📋 Utilisation du fichier existant '{uploaded_file.name}'")
                    st.session_state.file_replaced = False
        else:
            # Sauvegarde du nouveau fichier
            with open(upload_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            st.session_state.file_replaced = False
        
        # Mise à jour de l'état de session
        st.session_state.module_file = uploaded_file.name
        st.session_state.module_file_path = upload_path
        
        # Affichage des informations si le fichier a été traité
        if os.path.exists(upload_path) and (st.session_state.get('file_replaced') is not False):
            if st.session_state.get('file_replaced') == True:
                st.success(f"✅ Module '{uploaded_file.name}' remplacé avec succès!")
            elif st.session_state.get('file_replaced') == False:
                st.info(f"📋 Utilisation du fichier existant '{uploaded_file.name}'")
            else:
                st.success(f"✅ Module '{uploaded_file.name}' téléchargé avec succès!")
            
            # Informations sur le fichier
            file_size = os.path.getsize(upload_path)
            st.info(f"📊 Taille: {file_size:,} bytes | Type: PDF")
        
        # Prévisualisation du PDF
        if st.session_state.audit_engine:
            with st.expander("👁️ Prévisualisation du document", expanded=False):
                try:
                    preview_data = st.session_state.audit_engine.generate_pdf_preview(upload_path)
                    
                    if 'error' not in preview_data:
                        # Métadonnées du document
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write(f"**Titre:** {preview_data['metadata']['title']}")
                            st.write(f"**Pages:** {preview_data['metadata']['page_count']}")
                        with col2:
                            st.write(f"**Auteur:** {preview_data['metadata']['author']}")
                            st.write(f"**Taille:** {preview_data['metadata']['file_size']:,} bytes")
                        
                        st.divider()
                        
                        # Extraits de texte des premières pages
                        st.subheader("📝 Extraits de contenu")
                        for excerpt in preview_data['text_excerpts']:
                            if excerpt['text'].strip():
                                st.write(f"**Page {excerpt['page']}:**")
                                st.write(excerpt['text'])
                                st.write("---")
                    else:
                        st.error(f"Erreur lors de la prévisualisation: {preview_data['error']}")
                        
                except Exception as e:
                    st.error(f"Erreur lors de la génération de la prévisualisation: {str(e)}")
        
        # Bouton pour passer à l'étape suivante
        col1, col2, col3 = st.columns([1, 1, 2])
        
        with col1:
            if st.button("➡️ Étape Suivante", type="primary"):
                st.session_state.current_step = 2
                st.rerun()
        
        with col2:
            if st.button("⏭️ Passer à l'Analyse", help="Analyser uniquement le module sans document support"):
                st.session_state.current_step = 3
                st.rerun()
    
    # Affichage du fichier déjà uploadé si présent
    elif st.session_state.module_file:
        st.success(f"✅ Module déjà téléchargé: {st.session_state.module_file}")
        
        col1, col2, col3 = st.columns([1, 1, 2])
        
        with col1:
            if st.button("🔄 Changer Module"):
                st.session_state.module_file = None
                st.session_state.module_file_path = None
                st.rerun()
        
        with col2:
            if st.button("➡️ Étape Suivante", type="primary"):
                st.session_state.current_step = 2
                st.rerun()
        
        with col3:
            if st.button("⏭️ Passer à l'Analyse", help="Analyser uniquement le module sans document support"):
                st.session_state.current_step = 3
                st.rerun()

def show_step2_support_upload():
    """Étape 2: Upload optionnel du document support."""
    st.header("📄 Étape 2: Document Support (Optionnel)")
    st.write("Téléchargez un document support PDF pour enrichir l'analyse (optionnel).")
    
    # Rappel du module uploadé
    if st.session_state.module_file:
        st.info(f"📋 Module principal: {st.session_state.module_file}")
    
    # Upload de fichier support
    uploaded_file = st.file_uploader(
        "📁 Sélectionnez votre document support PDF (optionnel)",
        type=['pdf'],
        help="Formats acceptés: PDF uniquement",
        key="support_uploader"
    )
    
    if uploaded_file is not None:
        # Vérification si le fichier existe déjà
        upload_path = os.path.join("data/uploads", f"support_{uploaded_file.name}")
        
        if os.path.exists(upload_path):
            st.warning(f"⚠️ Le fichier '{uploaded_file.name}' existe déjà dans le dossier uploads.")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔄 Remplacer le fichier", key="replace_support"):
                    with open(upload_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    st.success(f"✅ Fichier '{uploaded_file.name}' remplacé avec succès!")
                    st.session_state.support_file_replaced = True
            
            with col2:
                if st.button("📂 Utiliser le fichier existant", key="use_existing_support"):
                    st.info(f"📋 Utilisation du fichier existant '{uploaded_file.name}'")
                    st.session_state.support_file_replaced = False
        else:
            # Sauvegarde du nouveau fichier
            with open(upload_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            st.session_state.support_file_replaced = False
        
        # Mise à jour de l'état de session
        st.session_state.support_file = uploaded_file.name
        st.session_state.support_file_path = upload_path
        
        # Affichage des informations si le fichier a été traité
        if os.path.exists(upload_path) and (st.session_state.get('support_file_replaced') is not False):
            if st.session_state.get('support_file_replaced') == True:
                st.success(f"✅ Document support '{uploaded_file.name}' remplacé avec succès!")
            elif st.session_state.get('support_file_replaced') == False:
                st.info(f"📋 Utilisation du fichier existant '{uploaded_file.name}'")
            else:
                st.success(f"✅ Document support '{uploaded_file.name}' téléchargé avec succès!")
            
            # Informations sur le fichier
            file_size = os.path.getsize(upload_path)
            st.info(f"📊 Taille: {file_size:,} bytes | Type: PDF")
        
        # Prévisualisation du PDF support
        if st.session_state.audit_engine:
            with st.expander("👁️ Prévisualisation du document support", expanded=False):
                try:
                    preview_data = st.session_state.audit_engine.generate_pdf_preview(upload_path)
                    
                    if 'error' not in preview_data:
                        # Métadonnées du document
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write(f"**Titre:** {preview_data['metadata']['title']}")
                            st.write(f"**Pages:** {preview_data['metadata']['page_count']}")
                        with col2:
                            st.write(f"**Auteur:** {preview_data['metadata']['author']}")
                            st.write(f"**Taille:** {preview_data['metadata']['file_size']:,} bytes")
                        
                        st.divider()
                        
                        # Extraits de texte des premières pages
                        st.subheader("📝 Extraits de contenu")
                        for excerpt in preview_data['text_excerpts']:
                            if excerpt['text'].strip():
                                st.write(f"**Page {excerpt['page']}:**")
                                st.write(excerpt['text'])
                                st.write("---")
                    else:
                        st.error(f"Erreur lors de la prévisualisation: {preview_data['error']}")
                        
                except Exception as e:
                    st.error(f"Erreur lors de la génération de la prévisualisation: {str(e)}")
    
    # Boutons de navigation
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        if st.button("⬅️ Retour Étape 1"):
            st.session_state.current_step = 1
            st.rerun()
    
    with col2:
        if st.button("➡️ Lancer l'Analyse", type="primary"):
            st.session_state.current_step = 3
            st.rerun()
    
    # Affichage du fichier support déjà uploadé si présent
    if st.session_state.support_file:
        st.success(f"✅ Document support: {st.session_state.support_file}")
        
        if st.button("🔄 Changer Document Support"):
            st.session_state.support_file = None
            st.session_state.support_file_path = None
            st.rerun()

def show_step3_analysis_dashboard():
    """Étape 3: Dashboard d'analyse et résultats."""
    st.header("📊 Étape 3: Analyse et Résultats")
    
    # Résumé des fichiers
    st.subheader("📋 Fichiers à analyser")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.session_state.module_file:
            st.success(f"📄 Module: {st.session_state.module_file}")
        else:
            st.error("❌ Aucun module téléchargé")
            if st.button("⬅️ Retour Étape 1"):
                st.session_state.current_step = 1
                st.rerun()
            return
    
    with col2:
        if st.session_state.support_file:
            st.info(f"📄 Support: {st.session_state.support_file}")
        else:
            st.info("📄 Support: Aucun (analyse du module seul)")
    
    # Boutons de navigation
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        if st.button("⬅️ Retour Étape 2"):
            st.session_state.current_step = 2
            st.rerun()
    
    with col2:
        if st.button("🔄 Nouveau Audit"):
            # Reset de toutes les variables
            st.session_state.current_step = 1
            st.session_state.module_file = None
            st.session_state.support_file = None
            st.session_state.module_file_path = None
            st.session_state.support_file_path = None
            st.session_state.current_audit = None
            st.session_state.audit_in_progress = False
            st.rerun()
    
    # Options d'audit
    if not st.session_state.audit_in_progress and not st.session_state.current_audit:
        st.subheader("🔧 Options d'Audit")
        
        # Choix du type d'audit
        audit_type = st.radio(
            "Choisissez le type d'audit:",
            ["standard", "chapter_by_chapter"],
            format_func=lambda x: {
                "standard": "📊 Audit Standard",
                "chapter_by_chapter": "📖 Audit Chapitre par Chapitre"
            }[x],
            index=0
        )
        
        # Descriptions des types d'audit
        if audit_type == "standard":
            st.info("📊 **Audit Standard** - Analyse globale du document pédagogique selon les critères de qualité définis.")
        else:
            st.info("📖 **Audit Chapitre par Chapitre** - Analyse détaillée de chaque chapitre individuellement avec conformité par section.")
        
        # Stockage du type d'audit choisi
        st.session_state.audit_type = audit_type
        
        if st.button("🚀 Lancer l'Audit", type="primary"):
            st.session_state.audit_in_progress = True
            st.rerun()
    
    # Audit en cours
    if st.session_state.audit_in_progress:
        st.warning("⏳ Audit en cours... Veuillez patienter.")
        
        try:
            with st.spinner("Analyse en cours par l'IA..."):
                # Barre de progression
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                status_text.text("Extraction du contenu PDF...")
                progress_bar.progress(20)
                
                # Lancement de l'audit selon le type choisi
                audit_type = st.session_state.get('audit_type', 'standard')
                
                if audit_type == "chapter_by_chapter":
                    # Audit chapitre par chapitre
                    audit_result = st.session_state.audit_engine.audit_pdf_chapter_by_chapter(
                        st.session_state.module_file_path, 
                        st.session_state.module_file
                    )
                elif st.session_state.support_file_path:
                    # Audit standard avec module et support
                    audit_result = st.session_state.audit_engine.audit_pdf_with_support(
                        st.session_state.module_file_path, 
                        st.session_state.support_file_path,
                        st.session_state.module_file
                    )
                else:
                    # Audit standard du module seul
                    audit_result = st.session_state.audit_engine.audit_pdf(
                        st.session_state.module_file_path, 
                        st.session_state.module_file
                    )
                
                status_text.text("Analyse des critères pédagogiques...")
                progress_bar.progress(60)
                
                # Sauvegarde du rapport
                json_path = st.session_state.audit_engine.save_audit_report(audit_result)
                
                status_text.text("Génération du rapport final...")
                progress_bar.progress(100)
                
                # Stockage du résultat
                st.session_state.current_audit = audit_result
                st.session_state.audit_in_progress = False
                
                status_text.text("✅ Audit terminé avec succès!")
                st.success(f"📄 Rapport sauvegardé: {os.path.basename(json_path)}")
                
                st.rerun()
                
        except Exception as e:
            st.error(f"❌ Erreur lors de l'audit: {str(e)}")
            st.session_state.audit_in_progress = False
            st.session_state.current_audit = None
    
    # Affichage des résultats
    if st.session_state.current_audit and not st.session_state.audit_in_progress:
        show_audit_results(st.session_state.current_audit)

def show_audit_results(audit_report):
    """Affiche les résultats de l'audit selon le type."""
    st.divider()
    
    # Déterminer le type d'audit et afficher le titre approprié
    if audit_report.get('metadata', {}).get('audit_type') == 'chapter_by_chapter':
        st.header("📖 Résultats de l'Audit Chapitre par Chapitre")
        show_chapter_by_chapter_results(audit_report)
    else:
        st.header("📊 Résultats de l'Audit Standard")
        show_standard_audit_results(audit_report)

def show_chapter_by_chapter_results(audit_report):
    """Affiche les résultats de l'audit chapitre par chapitre."""
    
    # Score global avec jauge
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        fig_gauge = create_gauge_chart(
            audit_report['scores']['final_score'],
            "Conformité Globale"
        )
        st.plotly_chart(fig_gauge, use_container_width=True)
    
    with col2:
        st.metric(
            "Conformité",
            f"{audit_report['scores']['final_score']}/100",
            delta=None
        )
        
        grade = audit_report['scores']['grade']
        grade_colors = {'A': '🟢', 'B': '🔵', 'C': '🟡', 'D': '🟠', 'E': '🔴'}
        st.metric(
            "Grade",
            f"{grade_colors.get(grade, '')} {grade}"
        )
    
    with col3:
        st.metric(
            "Chapitres analysés",
            f"{audit_report['metadata']['chapters_count']}"
        )
        
        conformity_summary = audit_report.get('chapter_analysis', {}).get('conformity_summary', {})
        st.metric(
            "Chapitres conformes",
            f"{conformity_summary.get('conforme', 0)}/{audit_report['metadata']['chapters_count']}"
        )
    
    # Description du grade
    st.info(f"**{grade}** - {audit_report['scores']['grade_description']}")
    
    # Onglets pour les détails
    tab1, tab2, tab3, tab4 = st.tabs(["📋 Chapitres", "📊 Synthèse", "💡 Recommandations", "📥 Export"])
    
    with tab1:
        st.subheader("Analyse par Chapitre")
        
        for i, chapter in enumerate(audit_report.get('chapters', []), 1):
            chapter_info = chapter.get('chapter_info', {})
            conformity = chapter.get('conformite', 'non_conforme')
            
            # Couleur selon la conformité
            color_map = {
                'conforme': '🟢',
                'partiellement_conforme': '🟡', 
                'non_conforme': '🔴'
            }
            
            with st.expander(f"{color_map.get(conformity, '⚪')} Chapitre {i}: {chapter_info.get('title', 'Sans titre')[:50]}..."):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.write(f"**Conformité:** {conformity.replace('_', ' ').title()}")
                    st.write(f"**Mots:** {chapter_info.get('word_count', 0)}")
                    
                    if chapter.get('recommandations'):
                        st.write("**Recommandations:**")
                        for rec in chapter['recommandations'][:3]:
                            st.write(f"• {rec}")
                
                with col2:
                    # Scores par critère pour ce chapitre
                    criteria_scores = {}
                    for criterion in ['objectifs', 'competences', 'contenu', 'references', 'volume']:
                        if criterion in chapter:
                            criteria_scores[criterion] = chapter[criterion].get('score', 0)
                    
                    if criteria_scores:
                        st.write("**Scores par critère:**")
                        for criterion, score in criteria_scores.items():
                            st.write(f"• {criterion.title()}: {score}/5")
    
    with tab2:
        st.subheader("Synthèse Globale")
        
        # Résumé de conformité
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Répartition de la Conformité:**")
            conformity_data = audit_report.get('chapter_analysis', {}).get('conformity_summary', {})
            
            for status, count in conformity_data.items():
                percentage = (count / audit_report['metadata']['chapters_count']) * 100 if audit_report['metadata']['chapters_count'] > 0 else 0
                st.write(f"• {status.replace('_', ' ').title()}: {count} ({percentage:.1f}%)")
        
        with col2:
            st.write("**Moyennes par Critère:**")
            criteria_averages = audit_report.get('chapter_analysis', {}).get('criteria_averages', {})
            
            for criterion, avg_score in criteria_averages.items():
                st.write(f"• {criterion.title()}: {avg_score}/5")
    
    with tab3:
        st.subheader("Recommandations Prioritaires")
        
        synthesis = audit_report.get('synthesis', {})
        
        if synthesis.get('critical_issues'):
            st.write("**🚨 Problèmes Critiques:**")
            for issue in synthesis['critical_issues']:
                st.error(f"• {issue}")
        
        if synthesis.get('priority_recommendations'):
            st.write("**💡 Recommandations Prioritaires:**")
            for rec in synthesis['priority_recommendations']:
                st.write(f"• {rec}")
        
        if synthesis.get('improvement_areas'):
            st.write("**📈 Domaines à Améliorer:**")
            for area in synthesis['improvement_areas']:
                st.write(f"• {area.replace('_', ' ').title()}")
    
    with tab4:
        st.subheader("Export du Rapport")
        
        if st.button("📄 Générer PDF", key="export_chapter_pdf"):
            try:
                pdf_buffer = export_to_pdf(audit_report)
                st.download_button(
                    label="⬇️ Télécharger le rapport PDF",
                    data=pdf_buffer,
                    file_name=f"rapport_audit_chapitres_{audit_report['metadata']['filename']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                    mime="application/pdf"
                )
                st.success("✅ Rapport PDF généré avec succès!")
            except Exception as e:
                st.error(f"❌ Erreur lors de la génération du PDF: {str(e)}")
        
        # Export JSON
        if st.button("📋 Télécharger JSON", key="export_chapter_json"):
            json_str = json.dumps(audit_report, indent=2, ensure_ascii=False)
            st.download_button(
                label="⬇️ Télécharger les données JSON",
                data=json_str,
                file_name=f"audit_chapitres_{audit_report['metadata']['filename']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )

def show_standard_audit_results(audit_report):
    """Affiche les résultats de l'audit standard."""
    
    # Score global avec jauge
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        fig_gauge = create_gauge_chart(
            audit_report['scores']['final_score'],
            "Score Global"
        )
        st.plotly_chart(fig_gauge, use_container_width=True)
    
    with col2:
        st.metric(
            "Note Finale",
            f"{audit_report['scores']['final_score']}/100",
            delta=None
        )
        
        grade = audit_report['scores']['grade']
        grade_colors = {'A': '🟢', 'B': '🔵', 'C': '🟡', 'D': '🟠', 'E': '🔴'}
        st.metric(
            "Grade",
            f"{grade_colors.get(grade, '')} {grade}"
        )
    
    with col3:
        st.metric(
            "Mots analysés",
            f"{audit_report['metadata']['word_count']:,}"
        )
        
        # Vérifier si les sections obligatoires existent
        # Gérer les différentes structures de données selon le type d'audit
        if 'analysis' in audit_report and 'mandatory_sections' in audit_report['analysis']:
            # Structure pour audit standard
            sections_found = len(audit_report['analysis']['mandatory_sections']['found_sections'])
            sections_total = len(audit_report['analysis']['mandatory_sections']['found_sections']) + len(audit_report['analysis']['mandatory_sections']['missing_sections'])
            st.metric(
                "Sections trouvées",
                f"{sections_found}/{sections_total}"
            )
        elif 'global_analysis' in audit_report and 'analysis' in audit_report['global_analysis']:
            # Structure pour audit chapitre par chapitre
            global_analysis = audit_report['global_analysis']['analysis']
            if 'mandatory_sections' in global_analysis:
                sections_found = len(global_analysis['mandatory_sections']['found_sections'])
                sections_total = len(global_analysis['mandatory_sections']['found_sections']) + len(global_analysis['mandatory_sections']['missing_sections'])
                st.metric(
                    "Sections trouvées",
                    f"{sections_found}/{sections_total}"
                )
            else:
                st.metric(
                    "Sections trouvées",
                    "N/A"
                )
        else:
            st.metric(
                "Sections trouvées",
                "N/A"
            )
    
    # Description du grade
    st.info(f"**{grade}** - {audit_report['scores']['grade_description']}")
    
    # Onglets pour les détails
    tab1, tab2, tab3, tab4 = st.tabs(["📋 Critères", "✅ Checklist", "💡 Recommandations", "📥 Export"])
    
    with tab1:
        st.subheader("Scores par Critère")
        
        # Graphique radar
        fig_radar = create_criteria_chart(audit_report['scores']['criteria_scores'])
        st.plotly_chart(fig_radar, use_container_width=True)
        
        # Tableau détaillé des critères
        st.subheader("Analyse Détaillée")
        
        for criterion_key, result in audit_report['scores']['criteria_scores'].items():
            if st.session_state.audit_engine:
                criterion_data = st.session_state.audit_engine.grille['criteria'][criterion_key]
                criterion_name = criterion_data['name']
                weight = criterion_data['weight']
            else:
                criterion_name = criterion_key.replace('_', ' ').title()
                weight = 0
            
            with st.expander(f"📊 {criterion_name} - Score: {result['score']}/5 (Poids: {weight}%)"):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.write("**Commentaire:**")
                    st.write(result['commentaire'])
                    
                    if result.get('preuves'):
                        st.write("**Preuves (extraits):**")
                        for i, preuve in enumerate(result['preuves'][:3], 1):
                            st.code(f"{i}. {preuve}")
                
                with col2:
                    if result.get('forces'):
                        st.write("**✅ Forces:**")
                        for force in result['forces'][:3]:
                            st.write(f"• {force}")
                    
                    if result.get('faiblesses'):
                        st.write("**❌ Faiblesses:**")
                        for faiblesse in result['faiblesses'][:3]:
                            st.write(f"• {faiblesse}")
    
    with tab2:
        st.subheader("Checklist des Éléments")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**✅ Sections Présentes:**")
            for section in audit_report['analysis']['mandatory_sections']['found_sections']:
                st.success(f"✅ {section.title()}")
            
            st.write("**❌ Sections Manquantes:**")
            for section in audit_report['analysis']['mandatory_sections']['missing_sections']:
                st.error(f"❌ {section.title()}")
        
        with col2:
            st.write("**📊 Éléments Comptés:**")
            elements = audit_report['analysis']['elements_count']
            
            st.metric("Exemples détectés", elements['examples_count'])
            st.metric("Exercices détectés", elements['exercises_count'])
            
            completion_rate = audit_report['analysis']['mandatory_sections']['completion_rate']
            st.metric("Taux de complétude", f"{completion_rate:.1f}%")
    
    with tab3:
        st.subheader("Recommandations d'Amélioration")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**🎯 Recommandations Prioritaires:**")
            for i, rec in enumerate(audit_report['analysis']['global_recommendations']['recommandations_prioritaires'], 1):
                st.write(f"{i}. {rec}")
        
        with col2:
            st.write("**💪 Forces Identifiées:**")
            for force in audit_report['analysis']['global_recommendations']['forces']:
                st.success(f"✅ {force}")
            
            st.write("**⚠️ Points d'Amélioration:**")
            for faiblesse in audit_report['analysis']['global_recommendations']['faiblesses']:
                st.warning(f"⚠️ {faiblesse}")
    
    with tab4:
        st.subheader("Export du Rapport")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Export JSON
            json_data = json.dumps(audit_report, ensure_ascii=False, indent=2)
            st.download_button(
                label="📥 Télécharger JSON",
                data=json_data,
                file_name=f"audit_{audit_report['metadata']['filename']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
        
        with col2:
            # Export PDF
            try:
                pdf_buffer = export_to_pdf(audit_report)
                st.download_button(
                    label="📄 Télécharger PDF",
                    data=pdf_buffer,
                    file_name=f"rapport_audit_{audit_report['metadata']['filename']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                    mime="application/pdf"
                )
            except Exception as e:
                st.error(f"Erreur génération PDF: {str(e)}")

# Fonction supprimée - Audit chapitre par chapitre non disponible

def show_history_page():
    """Page d'historique des audits."""
    st.header("📚 Historique des Audits")
    
    if not st.session_state.audit_engine:
        st.error("❌ Moteur d'audit non disponible.")
        return
    
    # Chargement de l'historique
    history = st.session_state.audit_engine.get_audit_history()
    
    if history['metadata']['total_audits'] == 0:
        st.info("📭 Aucun audit effectué pour le moment.")
        return
    
    # Statistiques globales
    st.subheader("📊 Statistiques Globales")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Audits", history['metadata']['total_audits'])
    
    with col2:
        if history['audits']:
            avg_score = sum(audit['final_score'] for audit in history['audits']) / len(history['audits'])
            st.metric("Score Moyen", f"{avg_score:.1f}/100")
    
    with col3:
        if history['audits']:
            grades = [audit['grade'] for audit in history['audits']]
            most_common_grade = max(set(grades), key=grades.count)
            st.metric("Grade le Plus Fréquent", most_common_grade)
    
    with col4:
        st.metric("Dernière Mise à Jour", history['metadata']['last_updated'][:10])
    
    # Graphique de l'évolution des scores
    if len(history['audits']) > 1:
        st.subheader("📈 Évolution des Scores")
        
        df = pd.DataFrame(history['audits'])
        df['audit_date'] = pd.to_datetime(df['audit_date'])
        
        fig = px.line(
            df, 
            x='audit_date', 
            y='final_score',
            title="Évolution des Scores d'Audit",
            markers=True
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    # Liste des audits
    st.subheader("📋 Liste des Audits")
    
    for audit in reversed(history['audits']):
        with st.expander(f"📄 {audit['filename']} - Score: {audit['final_score']}/100 ({audit['grade']}) - {audit['audit_date'][:10]}"):
            col1, col2, col3 = st.columns([2, 1, 1])
            
            with col1:
                st.write(f"**Fichier:** {audit['filename']}")
                st.write(f"**Date:** {audit['audit_date'][:19]}")
                st.write(f"**Mots:** {audit['word_count']:,}")
            
            with col2:
                st.metric("Score", f"{audit['final_score']}/100")
                grade_colors = {'A': '🟢', 'B': '🔵', 'C': '🟡', 'D': '🟠', 'E': '🔴'}
                st.write(f"**Grade:** {grade_colors.get(audit['grade'], '')} {audit['grade']}")
            
            with col3:
                if st.button(f"📖 Voir Détails", key=f"view_{audit['id']}"):
                    try:
                        detailed_report = st.session_state.audit_engine.load_audit_report(audit['json_file'])
                        st.session_state.current_audit = detailed_report
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erreur de chargement: {str(e)}")

def main():
    """Fonction principale de l'application."""
    
    # Sidebar pour la navigation
    with st.sidebar:
        st.title("🎓 Audit Pédagogique")
        st.write("Navigation")
        
        page = st.radio(
            "Choisissez une page:",
            ["📋 Étapes de l'Audit", "📚 Historique", "🔍 Comparaison PDF"],
            index=0
        )
        
        st.divider()
        
        # Affichage des étapes pour l'audit
        if page == "📋 Étapes de l'Audit":
            st.write("**📋 Progression de l'Audit**")
            
            # Étape 1
            step1_icon = "✅" if st.session_state.module_file else "📄"
            step1_color = "green" if st.session_state.module_file else "gray"
            st.markdown(f":{step1_color}[{step1_icon} Étape 1: Module PDF]")
            
            # Étape 2
            step2_icon = "✅" if st.session_state.support_file else "📄"
            step2_color = "green" if st.session_state.support_file else "gray"
            st.markdown(f":{step2_color}[{step2_icon} Étape 2: Support (optionnel)]")
            
            # Étape 3
            step3_icon = "📊"
            step3_color = "blue" if st.session_state.current_step == 3 else "gray"
            st.markdown(f":{step3_color}[{step3_icon} Étape 3: Analyse & Résultats]")
            
            st.divider()
        
        # Aide
        with st.expander("❓ Aide"):
            st.write("""
            **Comment utiliser l'application:**
            
            1. **Étape 1**: Téléchargez le fichier module PDF (obligatoire)
            2. **Étape 2**: Téléchargez un document support PDF (optionnel)
            3. **Étape 3**: Lancez l'analyse et consultez les résultats
            4. **Export**: Téléchargez le rapport en JSON/PDF
            5. **Historique**: Consultez les audits précédents
            
            **Critères évalués:**
            - Introduction & Objectifs
            - Structure & Progression
            - Clarté du Langage
            - Exemples Concrets
            - Exercices & Activités
            - Méthodes d'Évaluation
            - Résumé/Conclusion
            - Références & Ressources
            """)
    
    # Affichage de la page sélectionnée
    if page == "📋 Étapes de l'Audit":
        show_new_audit_workflow()
    elif page == "📚 Historique":
        show_history_page()
    elif page == "🔍 Comparaison PDF":
        show_pdf_comparison_page()

def show_pdf_comparison_page():
    """Page de comparaison entre deux fichiers PDF."""
    st.header("🔍 Comparaison de Fichiers PDF")
    st.write("Cette page vous permet de comparer deux fichiers PDF en extrayant et analysant leurs données.")
    
    # Options de comparaison
    comparison_mode = st.radio(
        "Mode de comparaison:",
        ["📤 Télécharger nouveaux fichiers", "📁 Utiliser fichiers existants"],
        horizontal=True
    )
    
    if comparison_mode == "📁 Utiliser fichiers existants":
        show_existing_files_comparison()
        return
    
    # Initialisation des variables de session pour la comparaison
    if 'comparison_file1' not in st.session_state:
        st.session_state.comparison_file1 = None
    if 'comparison_file2' not in st.session_state:
        st.session_state.comparison_file2 = None
    if 'comparison_data1' not in st.session_state:
        st.session_state.comparison_data1 = None
    if 'comparison_data2' not in st.session_state:
        st.session_state.comparison_data2 = None
    
    # Interface de téléchargement
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📄 Premier fichier PDF")
        uploaded_file1 = st.file_uploader(
            "Choisissez le premier fichier PDF",
            type=['pdf'],
            key="pdf1",
            help="Téléchargez le premier fichier PDF à comparer"
        )
        
        if uploaded_file1 is not None:
            # Sauvegarde du fichier
            file_path1 = os.path.join("data/uploads", uploaded_file1.name)
            with open(file_path1, "wb") as f:
                f.write(uploaded_file1.getbuffer())
            
            st.session_state.comparison_file1 = uploaded_file1.name
            st.success(f"✅ Fichier 1 téléchargé: {uploaded_file1.name}")
            
            # Extraction des données
            if st.button("🔍 Analyser Fichier 1", key="analyze1"):
                with st.spinner("Extraction des données du fichier 1..."):
                    try:
                        if st.session_state.audit_engine:
                            data1 = st.session_state.audit_engine.pdf_processor.process_pdf_file(file_path1)
                            st.session_state.comparison_data1 = data1
                            st.success("✅ Données extraites du fichier 1")
                        else:
                            st.error("❌ Moteur d'audit non disponible")
                    except Exception as e:
                        st.error(f"❌ Erreur lors de l'extraction: {str(e)}")
    
    with col2:
        st.subheader("📄 Deuxième fichier PDF")
        uploaded_file2 = st.file_uploader(
            "Choisissez le deuxième fichier PDF",
            type=['pdf'],
            key="pdf2",
            help="Téléchargez le deuxième fichier PDF à comparer"
        )
        
        if uploaded_file2 is not None:
            # Sauvegarde du fichier
            file_path2 = os.path.join("data/uploads", uploaded_file2.name)
            with open(file_path2, "wb") as f:
                f.write(uploaded_file2.getbuffer())
            
            st.session_state.comparison_file2 = uploaded_file2.name
            st.success(f"✅ Fichier 2 téléchargé: {uploaded_file2.name}")
            
            # Extraction des données
            if st.button("🔍 Analyser Fichier 2", key="analyze2"):
                with st.spinner("Extraction des données du fichier 2..."):
                    try:
                        if st.session_state.audit_engine:
                            data2 = st.session_state.audit_engine.pdf_processor.process_pdf_file(file_path2)
                            st.session_state.comparison_data2 = data2
                            st.success("✅ Données extraites du fichier 2")
                        else:
                            st.error("❌ Moteur d'audit non disponible")
                    except Exception as e:
                        st.error(f"❌ Erreur lors de l'extraction: {str(e)}")
    
    # Bouton de comparaison
    if st.session_state.comparison_data1 and st.session_state.comparison_data2:
        st.divider()
        if st.button("⚖️ Comparer les fichiers", type="primary", use_container_width=True):
            show_pdf_comparison_results()
    
    # Affichage des données extraites individuellement
    if st.session_state.comparison_data1 or st.session_state.comparison_data2:
        st.divider()
        st.subheader("📊 Données extraites")
        
        tab1, tab2 = st.tabs(["📄 Fichier 1", "📄 Fichier 2"])
        
        with tab1:
            if st.session_state.comparison_data1:
                show_pdf_data_summary(st.session_state.comparison_data1, "Fichier 1")
            else:
                st.info("Aucune donnée extraite pour le fichier 1")
        
        with tab2:
            if st.session_state.comparison_data2:
                show_pdf_data_summary(st.session_state.comparison_data2, "Fichier 2")
            else:
                st.info("Aucune donnée extraite pour le fichier 2")

def show_pdf_data_summary(data, title):
    """Affiche un résumé des données extraites d'un PDF."""
    st.write(f"**{title}**")
    
    # Statistiques générales
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Nombre de mots", data.get('statistics', {}).get('word_count', 'N/A'))
    
    with col2:
        st.metric("Nombre de caractères", data.get('statistics', {}).get('character_count', 'N/A'))
    
    with col3:
        st.metric("Nombre de lignes", data.get('statistics', {}).get('line_count', 'N/A'))
    
    # Mots-clés principaux
    if 'top_keywords' in data and data['top_keywords']:
        st.write("**Mots-clés principaux:**")
        keywords_df = pd.DataFrame(data['top_keywords'], columns=['Mot-clé', 'Fréquence'])
        st.dataframe(keywords_df, use_container_width=True)
    
    # Aperçu du contenu
    if 'content_preview' in data:
        with st.expander("📖 Aperçu du contenu"):
            st.text_area("Contenu", data['content_preview'], height=200, disabled=True)

def show_pdf_comparison_results():
    """Affiche les résultats de la comparaison entre les deux fichiers PDF."""
    st.subheader("⚖️ Résultats de la Comparaison")
    
    data1 = st.session_state.comparison_data1
    data2 = st.session_state.comparison_data2
    
    # Comparaison des statistiques
    st.write("### 📊 Comparaison des Statistiques")
    
    stats_comparison = pd.DataFrame({
        'Métrique': ['Nombre de mots', 'Nombre de caractères', 'Nombre de lignes'],
        'Fichier 1': [
            data1.get('statistics', {}).get('word_count', 0),
            data1.get('statistics', {}).get('character_count', 0),
            data1.get('statistics', {}).get('line_count', 0)
        ],
        'Fichier 2': [
            data2.get('statistics', {}).get('word_count', 0),
            data2.get('statistics', {}).get('character_count', 0),
            data2.get('statistics', {}).get('line_count', 0)
        ]
    })
    
    # Calcul des différences
    stats_comparison['Différence'] = stats_comparison['Fichier 2'] - stats_comparison['Fichier 1']
    stats_comparison['Différence (%)'] = ((stats_comparison['Fichier 2'] - stats_comparison['Fichier 1']) / stats_comparison['Fichier 1'] * 100).round(2)
    
    st.dataframe(stats_comparison, use_container_width=True)
    
    # Graphique de comparaison
    fig = px.bar(
        stats_comparison,
        x='Métrique',
        y=['Fichier 1', 'Fichier 2'],
        title="Comparaison des Statistiques",
        barmode='group'
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Comparaison des mots-clés
    st.write("### 🔤 Comparaison des Mots-clés")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Mots-clés Fichier 1:**")
        if data1.get('top_keywords'):
            keywords1_df = pd.DataFrame(data1['top_keywords'], columns=['Mot-clé', 'Fréquence'])
            st.dataframe(keywords1_df, use_container_width=True)
        else:
            st.info("Aucun mot-clé trouvé")
    
    with col2:
        st.write("**Mots-clés Fichier 2:**")
        if data2.get('top_keywords'):
            keywords2_df = pd.DataFrame(data2['top_keywords'], columns=['Mot-clé', 'Fréquence'])
            st.dataframe(keywords2_df, use_container_width=True)
        else:
            st.info("Aucun mot-clé trouvé")
    
    # Mots-clés communs
    if data1.get('top_keywords') and data2.get('top_keywords'):
        keywords1_set = set([kw[0] for kw in data1['top_keywords']])
        keywords2_set = set([kw[0] for kw in data2['top_keywords']])
        
        common_keywords = keywords1_set.intersection(keywords2_set)
        unique_to_1 = keywords1_set - keywords2_set
        unique_to_2 = keywords2_set - keywords1_set
        
        st.write("### 🔍 Analyse des Mots-clés")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Mots-clés communs", len(common_keywords))
            if common_keywords:
                st.write("**Mots communs:**")
                for kw in list(common_keywords)[:5]:
                    st.write(f"• {kw}")
        
        with col2:
            st.metric("Uniques au Fichier 1", len(unique_to_1))
            if unique_to_1:
                st.write("**Uniques au Fichier 1:**")
                for kw in list(unique_to_1)[:5]:
                    st.write(f"• {kw}")
        
        with col3:
            st.metric("Uniques au Fichier 2", len(unique_to_2))
            if unique_to_2:
                st.write("**Uniques au Fichier 2:**")
                for kw in list(unique_to_2)[:5]:
                    st.write(f"• {kw}")
    
    # Similarité textuelle avancée
    st.write("### 📈 Analyse de Similarité")
    
    content1 = data1.get('full_content', data1.get('content_preview', ''))
    content2 = data2.get('full_content', data2.get('content_preview', ''))
    
    if content1 and content2:
        # Calcul de similarité basé sur les mots communs
        words1 = set(content1.lower().split())
        words2 = set(content2.lower().split())
        
        common_words = words1.intersection(words2)
        total_words = words1.union(words2)
        
        similarity_score = len(common_words) / len(total_words) * 100 if total_words else 0
        
        # Calcul de similarité Jaccard pour les phrases
        sentences1 = set([s.strip().lower() for s in content1.split('.') if s.strip()])
        sentences2 = set([s.strip().lower() for s in content2.split('.') if s.strip()])
        
        common_sentences = sentences1.intersection(sentences2)
        total_sentences = sentences1.union(sentences2)
        
        sentence_similarity = len(common_sentences) / len(total_sentences) * 100 if total_sentences else 0
        
        # Affichage des métriques
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Similarité des Mots", f"{similarity_score:.1f}%")
        
        with col2:
            st.metric("Similarité des Phrases", f"{sentence_similarity:.1f}%")
        
        with col3:
            avg_similarity = (similarity_score + sentence_similarity) / 2
            st.metric("Score Global", f"{avg_similarity:.1f}%")
        
        # Indicateur visuel global
        if avg_similarity > 70:
            st.success("🟢 Documents très similaires")
        elif avg_similarity > 40:
            st.warning("🟡 Documents moyennement similaires")
        else:
            st.error("🔴 Documents peu similaires")
        
        # Analyse détaillée
        with st.expander("📊 Analyse Détaillée de Similarité"):
            st.write(f"**Mots communs:** {len(common_words)} sur {len(total_words)} mots uniques")
            st.write(f"**Phrases communes:** {len(common_sentences)} sur {len(total_sentences)} phrases uniques")
            
            if common_sentences:
                st.write("**Exemples de phrases communes:**")
                for i, sentence in enumerate(list(common_sentences)[:3]):
                    st.write(f"• {sentence[:100]}..." if len(sentence) > 100 else f"• {sentence}")
    
    # Bouton d'export des résultats
    st.divider()
    if st.button("📥 Exporter la Comparaison", use_container_width=True):
        export_comparison_results(data1, data2)

def show_existing_files_comparison():
    """Interface pour comparer des fichiers PDF existants."""
    st.subheader("📁 Comparaison de Fichiers Existants")
    
    # Récupération des fichiers PDF existants
    uploads_dir = "data/uploads"
    if not os.path.exists(uploads_dir):
        st.error("❌ Dossier uploads introuvable")
        return
    
    pdf_files = [f for f in os.listdir(uploads_dir) if f.endswith('.pdf')]
    
    if len(pdf_files) < 2:
        st.warning("⚠️ Il faut au moins 2 fichiers PDF dans le dossier uploads pour effectuer une comparaison.")
        st.info("Utilisez le mode 'Télécharger nouveaux fichiers' ou ajoutez des fichiers via l'audit pédagogique.")
        return
    
    st.success(f"✅ {len(pdf_files)} fichiers PDF trouvés")
    
    # Sélection des fichiers
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Premier fichier:**")
        selected_file1 = st.selectbox(
            "Choisissez le premier fichier",
            pdf_files,
            key="existing_file1"
        )
        
        if selected_file1:
            file_path1 = os.path.join(uploads_dir, selected_file1)
            file_size1 = os.path.getsize(file_path1) / 1024  # KB
            st.info(f"📄 {selected_file1} ({file_size1:.1f} KB)")
    
    with col2:
        st.write("**Deuxième fichier:**")
        available_files2 = [f for f in pdf_files if f != selected_file1]
        
        if available_files2:
            selected_file2 = st.selectbox(
                "Choisissez le deuxième fichier",
                available_files2,
                key="existing_file2"
            )
            
            if selected_file2:
                file_path2 = os.path.join(uploads_dir, selected_file2)
                file_size2 = os.path.getsize(file_path2) / 1024  # KB
                st.info(f"📄 {selected_file2} ({file_size2:.1f} KB)")
        else:
            st.error("❌ Aucun autre fichier disponible")
            return
    
    # Bouton de comparaison
    if selected_file1 and selected_file2:
        st.divider()
        
        if st.button("🔍 Analyser et Comparer", type="primary", use_container_width=True):
            with st.spinner("Extraction et analyse des données..."):
                try:
                    if st.session_state.audit_engine:
                        # Extraction des données des deux fichiers
                        file_path1 = os.path.join(uploads_dir, selected_file1)
                        file_path2 = os.path.join(uploads_dir, selected_file2)
                        
                        data1 = st.session_state.audit_engine.pdf_processor.process_pdf_file(file_path1)
                        data2 = st.session_state.audit_engine.pdf_processor.process_pdf_file(file_path2)
                        
                        if data1 and data2:
                            # Mise à jour des variables de session
                            st.session_state.comparison_file1 = selected_file1
                            st.session_state.comparison_file2 = selected_file2
                            st.session_state.comparison_data1 = data1
                            st.session_state.comparison_data2 = data2
                            
                            st.success("✅ Données extraites avec succès")
                            
                            # Affichage immédiat des résultats
                            show_pdf_comparison_results()
                        else:
                            st.error("❌ Erreur lors de l'extraction des données")
                    else:
                        st.error("❌ Moteur d'audit non disponible")
                        
                except Exception as e:
                    st.error(f"❌ Erreur lors de l'analyse: {str(e)}")

def export_comparison_results(data1, data2):
    """Exporte les résultats de comparaison en JSON."""
    comparison_results = {
        'comparison_date': datetime.now().isoformat(),
        'file1': {
            'name': st.session_state.comparison_file1,
            'data': data1
        },
        'file2': {
            'name': st.session_state.comparison_file2,
            'data': data2
        },
        'statistics_comparison': {
            'word_count_diff': data2.get('statistics', {}).get('word_count', 0) - data1.get('statistics', {}).get('word_count', 0),
            'character_count_diff': data2.get('statistics', {}).get('character_count', 0) - data1.get('statistics', {}).get('character_count', 0),
            'line_count_diff': data2.get('statistics', {}).get('line_count', 0) - data1.get('statistics', {}).get('line_count', 0)
        }
    }
    
    # Sauvegarde du fichier de comparaison
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"comparison_{st.session_state.comparison_file1}_{st.session_state.comparison_file2}_{timestamp}.json"
    filepath = os.path.join("data/audits", filename)
    
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(comparison_results, f, indent=2, ensure_ascii=False)
        
        st.success(f"✅ Comparaison exportée: {filename}")
        
        # Bouton de téléchargement
        with open(filepath, 'r', encoding='utf-8') as f:
            st.download_button(
                label="📥 Télécharger le fichier de comparaison",
                data=f.read(),
                file_name=filename,
                mime="application/json"
            )
    except Exception as e:
        st.error(f"❌ Erreur lors de l'export: {str(e)}")

if __name__ == "__main__":
    main()