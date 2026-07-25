# Auditeur d'accessibilité web (RGAA)

Scanne une URL et génère un rapport d'accessibilité complet : score, violations classées par sévérité (critique, sérieux, modéré, mineur), éléments HTML concernés et lien vers la documentation de chaque règle. Basé sur [axe-core](https://github.com/dequelabs/axe-core), le moteur de règles utilisé par la plupart des outils d'audit d'accessibilité du marché.

## Pourquoi ce projet

Le RGAA (référentiel d'accessibilité français) impose des obligations d'accessibilité, notamment pour les sites publics. Ce projet automatise le premier niveau de diagnostic : plutôt que d'auditer une page à la main, on obtient en quelques secondes un score et une liste priorisée des problèmes à corriger.

## Stack

| Couche | Techno |
|--------|--------|
| Frontend | React + TypeScript (Vite) |
| Backend | FastAPI (Python) |
| Moteur de scan | Selenium (Chrome headless) + axe-core |
| Base de données | SQLite (historique des scans) |

## Lancer le projet en local

### Backend

```bash
cd backend
python -m venv venv
venv/Scripts/activate        # Windows
pip install -r requirements.txt
cp .env.example .env
uvicorn main:app --reload --port 8020
```

Nécessite Google Chrome installé (le scan pilote Chrome directement via Selenium, sans navigateur embarqué séparé).

### Frontend

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Ouvrir `http://localhost:5174`.

## Fonctionnalités

- Scan d'une URL : score sur 100, compteurs par sévérité, nombre de tests réussis
- Détail de chaque violation : description, règle enfreinte, éléments HTML concernés, lien vers la documentation Deque
- Historique de tous les scans effectués, consultable à tout moment
- Gestion des erreurs (URL invalide, page inaccessible, timeout)

## Structure

```
a11y-auditor/
├── backend/
│   ├── main.py          # Routes FastAPI (scans CRUD)
│   ├── scanner.py         # Pilotage Selenium + injection axe-core + scoring
│   ├── models.py           # Modèle SQLAlchemy Scan
│   ├── schemas.py
│   ├── database.py
│   ├── config.py
│   └── vendor/axe.min.js  # Moteur axe-core vendorisé localement
└── frontend/
    └── src/
        ├── App.tsx          # Formulaire, historique, résultats
        ├── api.ts
        ├── types.ts
        └── components/
            └── ViolationCard.tsx
```

## Calcul du score

Le score part de 100 et retire des points par violation détectée, pondérés par sévérité (critique -10, sérieux -6, modéré -3, mineur -1), plafonné à 5 occurrences par règle pour qu'un problème répété massivement ne fasse pas chuter le score de façon disproportionnée.
