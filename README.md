# Austrian Library HUFS

한국외국어대학교 서양어대학 독일어과 부속 오스트리아도서관 디지털화 및 AI 기술 접목 프로젝트

🌐 **서비스**: [austrian-library-hufs.vercel.app](https://austrian-library-hufs.vercel.app/#/)
🤖 **도서 분류기**: [Book Genre Classifier](https://huggingface.co/spaces/jsjang0104/Book-Classifier)

## Structure
```
├── backend/        # Django REST API
├── frontend/       # Vue.js 프론트엔드
└── docs/
    ├── data/       # 도서 데이터 및 DB 추가 현황
    ├── dev/        # 개발 기록
    └── management/ # 운영 가이드라인 및 보고서
```

## 연동된 Project
- 2025-2 HUFS H-UP 진로탐색학점제: full stack development (창조상 수상)
- 2025-2 Understanding Machine Learning: book genre classifier — [GitHub](https://github.com/jsjang0104/Book-Classifier)
- 2026-1 Introduction to Multimodel AI:
- 2026-1 Information Retrieval and Recommender System:

## 참고사항
- **model/ 수정 시**: https://huggingface.co/jsjang0104/book-genre-classifier-bert 와 연동되어있음. 코드 수정 시 두 곳에 전부 push할 것
  - `git push origin main`
  - `git push hf main`
