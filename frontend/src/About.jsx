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
          독일어 문헌 데이터를 이용한 디지털 인문학의 가치를 추구하는 독일어과의 정체성을 공고히 하고 있습니다.<br />
          현재까지 도입된 AI 기술은 다음과 같습니다.
        </p>

      <div className="tech-AI-1">
        <h2>1. 장르 분류 AI</h2>
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
          해당 작업은 수백 권 이상의 도서도 한꺼번에 처리할 수 있으며, Hugging Face가 제공하는 무료 CPU를 이용하여 비용이 발생하지 않습니다.
        </p> 
        <br />
      
      </div>

      <div className="tech-AI-2">
        <h2>2. 의미 기반 검색 AI (진행 중)</h2>
          <br />
        <h3>2.1 도입 배경</h3>
          <p>
          현재 검색 시스템은 정확한 제목을 알아야만 검색이 가능한 완전 일치 기반으로 동작합니다.<br />
          예를 들어 "괴테"로 검색 시 "Goethe" 결과가 출력되지 않는 등의 문제가 있으며,
          "희극"과 같은 구체적인 장르·내용 기반 검색도 불가능합니다.<br />
          이를 해결하고자 다국어 임베딩 모델 기반의 의미 기반 검색 시스템 도입을 진행 중입니다.
          </p>
          <br />
        <h3>2.2 시스템 설계</h3>
          <p>
          Pretrained-Model: <a href="https://huggingface.co/FacebookAI/xlm-roberta-base">XLM-RoBERTa</a><br />
          벡터 검색: FAISS <br />
          <br />
          <strong>임베딩 사전 계산 (오프라인)</strong><br />
          첫 구축 단계에서 전체 도서(제목 + 저자)를 XLM-RoBERTa로 임베딩 계산 후 FAISS 인덱스로 저장합니다.<br />
          이후 신규 도서 추가 시 해당 도서 임베딩만 계산하여 인덱스에 추가하므로 전체 재계산이 필요하지 않습니다.<br />
          <br />
          <strong>검색 (온라인, 실시간)</strong><br />
          1. 키워드 매칭 (최우선, 기존 방식): 제목/저자 정확 매칭<br />
          2. 벡터 유사도 검색: 쿼리를 XLM-RoBERTa로 임베딩하여 FAISS로 유사 도서를 검색합니다. 
          이때 한국어, 독일어, 영어 등의 cross-lingual을 자동으로 지원합니다.<br />
          3. UI 노출: 키워드 결과를 우선시하여 중복 제거 후 벡터 결과를 추가하여 최종 반환합니다.<br />
          <br />
          </p>
          <br />
        <h3>2.3 평가 계획</h3>
          <p>
          Metric: Precision@K<br />
          샘플 쿼리셋을 직접 제작하여 상위 K개 결과의 관련성을 직접 labeling, 이후 기존의 키워드 매칭 시스템과 비교하여 개선 폭을 측정할 예정입니다.
          </p>
          <br />
      </div>
    </main>
  );
}

export default About;
