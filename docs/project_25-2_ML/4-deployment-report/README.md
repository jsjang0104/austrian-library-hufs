# 도서 분야 분류기
한국외국어대학교 독일어과 귀속 오스트리아 도서관(본관 301호)의 데이터베이스 구축을 도와주는 도서 분야 분류기입니다.

## 사용 방법
1. 서비스 접속: https://huggingface.co/spaces/jsjang0104/book-genre-classifier-service
2. 파일 업로드: **'title', 'author', 'location'이 담긴 csv 파일**을 업로드하세요!
    - 💡 교수님 채점 편의를 위하여 zip 파일 안에 sample_data_korean_english.csv를 sample로 넣어두었습니다.
3. 검수 및 수정: AI가 분석한 분야 순위를 보고 *어학(Sprachwissenschaft), 문학(Literatur), 역사(Geschichte), 사회과학(Sozialwissenschaften)* 중 골라주세요!
    - ⚠️ 모델은 *기타(Sonstiges)*를 분류를 지원하지 않습니다. 기타 선택에 관한 판단은 사용자의 몫입니다!
    - 💡 확신도 0.85 이하인 빨간색 도서를 주의깊게 확인하세요!
4. 결과 다운로드: 'subject' 열이 자동으로 채워진 **최종 csv 파일**을 다운로드하면 끝!

## 시스템 구조
1. 접근성: Hugging Face 서버에서 Gradio 코드가 시행되며, 별도의 로컬 서버 구동 없이도 누구나 서비스에 24시간 접근할 수 있습니다.
2. app.py: 코드가 시행되면 Hugging Face에 저장된 가중치 (https://huggingface.co/jsjang0104/book-genre-classifier-bert)를 불러와서 모델이 로드됩니다.
3. input and output: 사용자는 title, author, location이 담긴 csv 파일을 로드하고, 클래스별 모델의 확신도를 받으며 웹상에서 선택합니다. 선택한 결과물은 기존 도서 정보 옆에 추가되어 csv 파일로 다운로드 할 수 있게 제공됩니다.  


## Key Features
1. 오스트리아 도서관 맞춤형 커스텀 AI
    - 기존 십진분류법(DDC)은 10가지 분류가 필요하여 오스트리아 도서관의 소장 도서 특성(독일학 중심)에 적절하지 않았습니다.
    - 도서관이 소장 중인 도서 특성에 맞춰 4대 핵심 분야(어학, 문학, 역사, 사회과학) 분류를 적용했습니다.

2. 도서관 업무 효율 up!
    - 기존 업무 방식: 조교가 독일어 원서를 직접 읽거나 생성형 AI의 도움을 받아 수기로 분야를 작성 (높은 피로도, 긴 소요시간, 높은 오류율)
    - 새로운 방식: 조교들은 도서 위치, 책 제목, 저자만 입력하세요! 나머지는 AI로 자동화하여 업무 난이도를 낮추고 정확성을 높입니다.

3. Gradio를 이용한 비전공자도 쉽게 사용 가능한 UI
    - vscode가 뭐고 ipynb는 뭔가요 ㅠㅠ 
    - 오스트리아 도서관 조교들은 모두 독일어과 학부생들로, 다른 IT 비전공자 조교들도 csv 파일과 웹 링크만 있으면 편하게 이용 가능!