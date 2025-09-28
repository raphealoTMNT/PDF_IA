# PDF_IA - Audit Pédagogique PDF

Une application web interactive développée avec Streamlit et Python qui permet d'auditer des documents pédagogiques PDF avec intelligence artificielle.

## 🚀 Fonctionnalités

### Étape 1 : Upload de Fichier PDF Module
- Téléchargement de fichiers PDF uniquement
- Informations détaillées sur le fichier PDF
- Sauvegarde automatique dans le dossier `data/uploads/`

### Étape 2 : Upload de Document PDF Support (Optionnel)
- Téléchargement de documents PDF de support uniquement
- Informations sur la taille et le type du fichier
- Sauvegarde automatique dans le dossier `data/uploads/`

### Étape 3 : Audit et Dashboard
- **Audit Standard** : Analyse globale du document pédagogique
- **Audit Chapitre par Chapitre** : Analyse détaillée de chaque section
- Scoring automatique basé sur une grille pédagogique
- Recommandations personnalisées
- Export des résultats en JSON
- Visualisation des résultats avec graphiques et métriques

## 📋 Prérequis

- Python 3.8 ou supérieur
- pip (gestionnaire de paquets Python)

## 🛠️ Installation

1. Clonez ou téléchargez ce projet
2. Naviguez vers le dossier du projet :
   ```bash
   cd "ia agent"
   ```

3. Installez les dépendances :
   ```bash
   pip install -r requirements.txt
   ```

## 🚀 Lancement de l'application

1. Exécutez la commande suivante dans le terminal :
   ```bash
   streamlit run app.py
   ```

2. L'application s'ouvrira automatiquement dans votre navigateur à l'adresse :
   ```
   http://localhost:8501
   ```

## 📁 Structure du projet

```
ia agent/
├── app.py                 # Application principale Streamlit
├── requirements.txt       # Dépendances Python
├── README.md             # Documentation
├── data/                 # Dossier de données
│   ├── uploads/          # Fichiers PDF téléchargés
│   ├── audits/           # Rapports d'audit générés
│   └── index.json        # Index des audits
├── backend/              # Moteur d'audit
│   ├── audit_engine.py   # Logique d'audit IA
│   └── pdf_processor.py  # Traitement des PDF
└── config/               # Configuration
    └── grille_pedagogique.json
```

## 🎯 Utilisation

1. **Navigation** : Utilisez la barre latérale pour naviguer entre les étapes
2. **Progression** : Une barre de progression indique votre avancement
3. **Upload** : Glissez-déposez ou sélectionnez vos fichiers dans chaque étape
4. **Audit** : Choisissez entre audit standard ou chapitre par chapitre
5. **Résultats** : Consultez les scores, recommandations et analyses détaillées
6. **Export** : Téléchargez les résultats au format JSON

## 🔧 Personnalisation

Vous pouvez facilement personnaliser l'application en modifiant :
- La grille pédagogique dans `config/grille_pedagogique.json`
- Les critères d'audit dans `backend/audit_engine.py`
- L'interface utilisateur dans `app.py`
- Les algorithmes de traitement PDF dans `backend/pdf_processor.py`

## 📝 Notes

- Seuls les fichiers PDF sont acceptés pour garantir la compatibilité
- Les fichiers PDF sont sauvegardés localement dans le dossier `data/uploads/`
- L'application utilise les sessions Streamlit pour maintenir l'état entre les étapes
- Tous les fichiers PDF sont traités côté serveur pour plus de sécurité
- Les audits sont sauvegardés automatiquement avec horodatage

## 🆘 Support

En cas de problème :
1. Vérifiez que toutes les dépendances sont installées
2. Assurez-vous d'utiliser Python 3.8+
3. Consultez les logs dans le terminal pour les erreurs détaillées
