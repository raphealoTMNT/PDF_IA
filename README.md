# Application Web Multi-Étapes avec Streamlit

Une application web interactive développée avec Streamlit et Python qui permet de gérer un processus en 3 étapes :

## 🚀 Fonctionnalités

### Étape 1 : Upload de Fichier PDF Module
- Téléchargement de fichiers PDF uniquement
- Informations détaillées sur le fichier PDF
- Sauvegarde automatique dans le dossier `data/uploads/`

### Étape 2 : Upload de Document PDF Support
- Téléchargement de documents PDF uniquement
- Informations sur la taille et le type du fichier
- Sauvegarde automatique dans le dossier `data/uploads/`

### Étape 3 : Dashboard
- Visualisation des fichiers PDF téléchargés
- Statistiques sur les fichiers PDF (taille, type, etc.)
- Graphiques et tableaux récapitulatifs
- Option de réinitialisation pour recommencer le processus

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
4. **Visualisation** : Consultez le dashboard pour voir un résumé de vos uploads
5. **Réinitialisation** : Utilisez le bouton "Recommencer" pour repartir de zéro

## 🔧 Personnalisation

Vous pouvez facilement personnaliser l'application en modifiant :
- Les fonctionnalités PDF dans les fonctions `show_step1()` et `show_step2()`
- Les visualisations dans la fonction `show_step3()`
- Le style et la mise en page dans la configuration Streamlit
- Ajouter des fonctionnalités d'analyse PDF avec des bibliothèques comme PyPDF2

## 📝 Notes

- Seuls les fichiers PDF sont acceptés pour garantir la compatibilité
- Les fichiers PDF sont sauvegardés localement dans le dossier `data/uploads/`
- L'application utilise les sessions Streamlit pour maintenir l'état entre les étapes
- Tous les fichiers PDF sont traités côté serveur pour plus de sécurité

## 🆘 Support

En cas de problème :
1. Vérifiez que toutes les dépendances sont installées
2. Assurez-vous d'utiliser Python 3.8+
3. Consultez les logs dans le terminal pour les erreurs détaillées