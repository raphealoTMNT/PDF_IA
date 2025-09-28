# 📋 Notes de Lancement - Application d'Audit Pédagogique IA

## 🚀 Comment lancer l'application

### Prérequis
- Python 3.8 ou supérieur
- VS Code (recommandé)
- Clé API Groq valide

### 1. Configuration initiale

#### A. Ouvrir le projet dans VS Code
```bash
# Ouvrir VS Code dans le dossier du projet
code "c:\Users\LVIG\Desktop\ia agent"
```

#### B. Créer un environnement virtuel (recommandé)
```bash
# Créer l'environnement virtuel
python -m venv venv

# Activer l'environnement virtuel
# Sur Windows PowerShell :
.\venv\Scripts\Activate.ps1
# Sur Windows CMD :
.\venv\Scripts\activate.bat
```

#### C. Installer les dépendances
```bash
pip install -r requirements.txt
```

### 2. Configuration des variables d'environnement

Le fichier `.env` doit contenir :
```env
GROQ_API_KEY=votre_clé_api_groq_ici
ENCRYPTION_PASSWORD=votre_mot_de_passe_chiffrement
```

**Important :** Remplacez `votre_clé_api_groq_ici` par votre vraie clé API Groq.

### 3. Lancement de l'application

#### Méthode 1 : Via le terminal
```bash
streamlit run app.py
```

#### Méthode 2 : Via Python module
```bash
python -m streamlit run app.py
```

#### Méthode 3 : Port personnalisé (si le port 8501 est occupé)
```bash
streamlit run app.py --server.port 8502
```

### 4. Accès à l'application

Une fois lancée, l'application sera accessible à :
- **URL locale :** http://localhost:8501
- **URL réseau :** http://[votre_ip]:8501

## 🛠️ Commandes utiles dans VS Code

### Terminal intégré
- `Ctrl + `` ` : Ouvrir/fermer le terminal
- `Ctrl + Shift + `` ` : Nouveau terminal

### Lancement rapide
1. Ouvrir le terminal intégré (`Ctrl + `` `)
2. Taper : `streamlit run app.py`
3. Appuyer sur `Entrée`

## 🔧 Résolution des problèmes courants

### Erreur "Module not found"
```bash
pip install -r requirements.txt
```

### Port occupé
```bash
streamlit run app.py --server.port 8502
```

### Clé API manquante
1. Ouvrir le fichier `.env`
2. Ajouter votre clé Groq :
   ```env
   GROQ_API_KEY=gsk_votre_clé_ici
   ```

### Erreur de permissions (environnement virtuel)
```bash
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

## 📁 Structure du projet

```
ia agent/
├── app.py                    # Application principale Streamlit
├── requirements.txt          # Dépendances Python
├── .env                     # Variables d'environnement
├── backend/
│   ├── audit_engine.py      # Moteur d'audit IA (Groq)
│   ├── encryption_manager.py # Gestionnaire de chiffrement
│   └── pdf_processor.py     # Traitement des PDF
├── config/
│   ├── grille_pedagogique.json
│   └── subject_experts.json
└── data/                    # Données et audits sauvegardés
```

## 🎯 Fonctionnalités disponibles

- ✅ **Audit automatique** de modules pédagogiques PDF
- ✅ **Analyse chapitre par chapitre** détaillée
- ✅ **Comparaison module/support** de cours
- ✅ **Rapports visuels** avec graphiques interactifs
- ✅ **Export PDF** des rapports d'audit
- ✅ **Historique** des audits précédents
- ✅ **Chiffrement** des données sensibles
- ✅ **Interface multilingue** (français/anglais)

## 🔐 Sécurité

- Les données sont chiffrées avec AES-256
- Les clés API sont stockées dans `.env` (non versionné)
- Les rapports d'audit sont chiffrés automatiquement

## 📊 Utilisation de l'API

L'application utilise **Groq AI** avec le modèle `llama-3.3-70b-versatile` pour :
- Analyser le contenu pédagogique
- Évaluer la conformité aux critères
- Générer des recommandations personnalisées

## 🆘 Support

En cas de problème :
1. Vérifier que toutes les dépendances sont installées
2. Vérifier la configuration du fichier `.env`
3. Consulter les logs dans le terminal
4. Redémarrer l'application si nécessaire

---

**Dernière mise à jour :** $(Get-Date -Format "dd/MM/yyyy HH:mm")
**Version :** 1.0 - Groq AI exclusif