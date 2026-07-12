//======================================================================
//======================================================================
// AI 도서관
//======================================================================
//======================================================================


import React from 'react';
import myImage from './assets/confusion_matrix.png';

function About() {
  return (
    <main className="main-content about-page">
      <br /><br />
        <h1>AI 도서관</h1>
        <p>
          도서관을 직접 찾아야 도서 목록 열람 · 대출 · 반납이 가능했던 기존 방식을 끝으로,
          2025년 2학기 우리 오스트리아 도서관은 전면 디지털화를 완료하였습니다.<br />
          이제 사용자들은 새로 구축된 데이터베이스 및 홈페이지를 통해 외부에서도 도서 목록을 쉽게 조회하고,
          대출 및 반납 여부를 확인할 수 있습니다. <br />
          <br />
          또한 우리 도서관은 이에 그치지 않고 다가오는 인공지능 시대에 발맞춰 AI 기술을 적극 도입하고 있습니다.<br />
          이를 통해 도서관 업무의 효율성을 높이고,
          독일어 문헌 데이터를 이용한 디지털 인문학의 가치를 추구하는 독일어과의 전문성을 공고히 하고 있습니다.<br />
          현재까지 도입된 AI 기술은 다음과 같습니다.
        </p>

      <div className="tech-AI-1">
        <h2>1. 장르 분류 AI (Genre Classification)</h2>
          <br />
        <h3>1.1 도입 배경</h3>
          <p>
          도서 목록 구축 과정에서 도서 분야를 사람이 직접 판단하여 수기로 입력한다면 
          잦은 오류와 긴 소요 시간 등의 문제가 야기됩니다. <br />
          이에 AI 모델을 학습시켜 도서 목록 구축 업무 난이도를 줄이고자 하였습니다. <br />
          사서가 입력한 도서 제목과 저자를 보고 AI 모델이 자동으로 분야를 예측합니다.
          </p>
          <br />
        <h3>1.2 모델 학습</h3>
        <p>
          Pre-trained Model: <a href="https://huggingface.co/google-bert/bert-base-multilingual-cased">mBERT</a><br />
          Dataset: <a href="https://huggingface.co/datasets/SBB/ARK-Metadata">Berlin State Library 제공 다국어 도서 공개 데이터셋</a> (training, evaluation, test 8:1:1)<br />
          Target Task: Multiclass Classification Fine-tuning (class: 문학, 어학, 사회과학, 역사)<br />
          Model Link: <a href="https://huggingface.co/jsjang0104/book-genre-classifier-bert">https://huggingface.co/jsjang0104/book-genre-classifier-bert</a>
          <br />
        </p>
          <br />
        <h3>1.3 모델 성능</h3>
          <p><strong>Overall Metrics</strong></p>
          <p>Accuracy(Overall) 0.7291</p>
          <p>F1-Score(Weighted) 0.7284</p>
          <p>F1-Score(Macro) 0.7262</p>
          <p>Precision(Weighted) 0.7314</p>
          <p>Recall(Weighted) 0.7291</p>
          <br />

          <p><strong>클래스별 F1-Score:</strong></p>
          <p>역사 (Geschichte): 0.6868</p>
          <p>문학 (Literatur): 0.7348</p>
          <p>사회과학 (Sozialwissenschaften): 0.7800</p>
          <p>어학 (Sprachwissenschaft): 0.7032</p>
          <br />

          <p><strong>Normalized Confusion Matrix:</strong></p>
          <img src={myImage} alt="Normalized Confusion Matrix" style={{ width: '40%' }} />
        <h3>1.4 서비스 배포</h3>
        <strong>서비스 링크</strong> <a href="https://huggingface.co/spaces/jsjang0104/Book-Classifier">https://huggingface.co/spaces/jsjang0104/Book-Classifier</a>
        <p>
          실제 서비스에서는 모델이 도서 제목, 저자, 위치를 입력으로 받아 자동으로 도서 분야를 예측한 뒤, 
          모든 메타 데이터를 바탕으로 고유 청구기호를 생성합니다. <br />
          이후 사서가 예측된 분야와 청구기호를 검토하여 최종적으로 도서 목록에 입력하는 방식으로 운영됩니다. <br />
          해당 작업은 수백 권 이상의 도서도 한꺼번에 처리할 수 있으며, Hugging Face가 제공하는 무료 Space를 이용하여 비용이 발생하지 않습니다.
        </p> 
        <br />
      
      </div>

      <div className="tech-AI-2">
        <h2>2. 의미 기반 검색 AI (Semantic Search)</h2>
          <br />
        <h3>2.1 도입 배경</h3>
          <p>
          기존 검색 시스템은 도서 제목·저자의 정확한 문자열 일치에만 의존하는 키워드 매칭 방식으로,
          한국어 쿼리로 독일어 원서를 검색하거나("괴테" → "Goethe"),
          "사랑 소설"·초급 문법"와 같은 장르·주제 기반 검색이 불가능한 한계가 있었습니다.<br />
          이를 해결하기 위해 다국어 임베딩 모델 기반의 하이브리드 검색 시스템을 구축하여 배포하였습니다.
          </p>
          <br />
        <h3>2.2 시스템 설계</h3>
          <p>
          Pretrained-Model: <a href="https://huggingface.co/intfloat/multilingual-e5-large">intfloat/multilingual-e5-large</a><br />
          벡터 검색: FAISS<br />
          <br />
          <strong>임베딩 입력 텍스트 구성</strong><br />
          단순 제목·저자 정보만으로는 의미 검색 품질이 낮아, 각 도서에 대해 <a href="https://huggingface.co/Qwen/Qwen3.6-27B-FP8">LLM</a>이 생성한
          독일어 맥락 요약문과 한국어 번역을 함께 임베딩 입력으로 사용합니다. 생성 품질 관리를 위해 JSON 구조화 출력과 언어 오염 자동 검증을 적용했습니다.<br />
          <br />
          <strong>임베딩 사전 계산 (오프라인)</strong><br />
          기존 도서 4,328권: 로컬 GPU에서 모델을 직접 로드하여 일괄 임베딩 후 FAISS 인덱스(books.faiss) 구축하였습니다.<br />
          신규 도서 등록 시: 사서가 관리자 페이지에서 맥락 텍스트와 번역을 직접 입력하며, 저장 시 HuggingFace Inference API로 임베딩이 계산되어 기존 인덱스에 자동 반영됩니다.<br />
          <br />
          <strong>하이브리드 검색 (온라인, 실시간)</strong><br />
          1. 키워드 매칭 (최우선): 제목·번역 제목·저자·번역 저자·청구기호 등 전 필드를 대상으로 부분 일치 검색을 수행합니다.<br />
          2. 벡터 유사도 검색: 검색어를 HuggingFace Inference API를 이용해 임베딩하여 FAISS 인덱스에서 유사 도서를 검색합니다.<br />
          3. 결과 병합: 이후 키워드 결과를 우선 반환하고, 추가된 벡터 유사도 검색 결과에서 중복 도서 제거 후 최종 반환합니다.<br />
          <br />
          검색 페이지의 <strong>✦ AI 검색</strong> 버튼으로 모드를 전환할 수 있으며,
          미활성 시 기존 키워드 검색, 활성 시 하이브리드 검색이 적용됩니다.<br />
          <br />
          </p>
          <br />
        <h3>2.3 평가 결과</h3>
          <p>
          Metric: Recall@30, 쿼리셋 29개 (ground truth를 운영 DB 기준으로 재구축)<br />
          <br />
          <strong>평균 Recall@30</strong><br />
          키워드 검색: 0.023 &nbsp;/&nbsp; 하이브리드 검색(개편 후, Qwen3.6+e5-large): 0.339<br />
          <br />
          맥락 텍스트 품질 개선과 임베딩 모델 업그레이드로 개편 전 대비 약 11배의 검색 품질 향상을 달성했습니다.<br />
          <br />
          관용 번역 제목이 번역 데이터에 반영되어 '마의 산'(Der Zauberberg)처럼 기존에 검색 불가능했던 도서를 찾을 수 있게 되었고,
          나아가 제목·저자에 검색어가 전혀 포함되지 않아도 의미 기반으로 도서가 검색됩니다.
          예를 들어 '베를린 장벽'을 검색하면 Ein Loch in der Mauer가,
          '모험 소설'을 검색하면 쥘 베른의 Meister Antifers wunderbare Abenteuer가,
          '독일어 인명 사전'을 검색하면 Lexikon literarischer Gestalten이 벡터 유사도만으로 반환됩니다.
          </p>
          <br />
      </div>
    </main>
  );
}

export default About;
