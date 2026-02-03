# Contributing to RAG Support Agent

Thank you for your interest in contributing! This project follows standard professional development practices.

## Code of Conduct

Please be respectful and professional in all interactions.

## How to Contribute

1. **Fork the Repository**: Create your own fork of the project.
2. **Create a Branch**: Use descriptive branch names (e.g., `feature/add-search-filter`).
3. **Set Up Environment**:
   - Backend: Create a `venv` and install `requirements.txt`.
   - Frontend: Run `npm install`.
4. **Follow Standards**:
   - Adhere to the `.editorconfig` settings.
   - For Python: Follow PEP 8 guidelines.
   - For TypeScript: Use functional components and hooks.
5. **Submit a Pull Request**: Describe your changes clearly and link to any relevant issues.

## Development Setup

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn api.main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

## Questions?

Open a GitHub Issue for any clarification or feature requests.
