import gradio as gr
import os
import torch
import torch.nn.functional as F
import numpy as np
import pandas as pd
from transformers import AutoTokenizer, AutoModelForSequenceClassification

# ==============================================================================
# [1] 모델
# ==============================================================================

# ------------------------------------------------------------------------------
# 하이퍼파라미터, 경로 설정
# ------------------------------------------------------------------------------
HF_MODEL_ID = "jsjang0104/book-genre-classifier-bert"
LABELS = [
    "Geschichte",
    "Literatur",
    "Sozialwissenschaften",
    "Sprachwissenschaft",
]  # CLASS_NAMES
NUM_CLASSES = len(LABELS)
MAX_LEN = 256  # training.ipynb와 동일
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print("✅ 하이퍼파라미터 및 경로 설정 완료")

print("--- 1. 모델 로드 시작 ---")
try:
    # 토크나이저 로드
    tokenizer = AutoTokenizer.from_pretrained(HF_MODEL_ID)

    # 가중치 파일 로드 및 모델 복원
    model = AutoModelForSequenceClassification.from_pretrained(
        HF_MODEL_ID, num_labels=NUM_CLASSES, trust_remote_code=True
    )
    model.to(device)
    model.eval()  # 모델을 평가 모드로 설정

    print(f"✅ 모델 '{HF_MODEL_ID}' 로드 완료 (Device: {device})")

except Exception as e:
    print(f"모델 로드 중 오류 발생: {e}")
    print("GitHub/Hugging Face ID 또는 네트워크 상태를 확인하세요.")
    print(f" [에러 해결 안내]")
    print(
        f"   - **원인:** Hugging Face의 최신 가중치 파일 형식인 'model.safetensors'를 로드하는 데 필요한 "
    )
    print(f"     라이브러리가 로컬 환경에 설치되어 있지 않습니다.")
    print(
        f"   - **해결 방법 (가장 유력):** 터미널/프롬프트에서 아래 명령어를 실행하여 'safetensors' 라이브러리를 설치하세요."
    )
    print(f"     >>> pip install safetensors")
    print(
        f"   - **추가 해결 방법:** 위 조치 후에도 오류가 지속되면 'transformers' 라이브러리를 최신 버전으로 업데이트하세요."
    )
    print(f"     >>> pip install --upgrade transformers")
    exit()


# ------------------------------------------------------------------------------
# 추론 함수 정의
# ------------------------------------------------------------------------------
def predict_genre(title: str):
    """
    주어진 제목에 대해 장르를 예측하고 상위 4개 클래스의 확률을 반환하는 함수
    """

    # 토크나이징 (기존 로직 유지)
    encoding = tokenizer.encode_plus(
        title,
        max_length=MAX_LEN,
        padding="max_length",
        truncation=True,
        return_tensors="pt",
    )

    # 디바이스 이동 및 추론 (기존 로직 유지)
    input_ids = encoding["input_ids"].to(device)
    attention_mask = encoding["attention_mask"].to(device)

    with torch.no_grad():
        outputs = model(input_ids=input_ids, attention_mask=attention_mask)
        logits = outputs.logits

    # 확률 변환
    probs = F.softmax(logits, dim=1).cpu().numpy()[0]

    # 확률 높은 순서대로 인덱스 정렬
    ranked_indices = np.argsort(probs)[::-1]

    # 상위 4개 클래스 이름과 확률을 딕셔너리로 저장
    top_4_probs = {}
    for i in range(min(4, NUM_CLASSES)):
        idx = ranked_indices[i]
        class_name = LABELS[idx]
        top_4_probs[class_name] = probs[idx]

    # 최종 예측 (highest confidence)
    prediction = LABELS[ranked_indices[0]]
    confidence = probs[ranked_indices[0]]

    return prediction, confidence, top_4_probs


# ==============================================================================
# [2] Gradio 로직 함수들
# ==============================================================================
def analyze_csv(file_obj):
    if file_obj is None:
        return None

    df = None

    encodings_to_try = ["utf-8", "cp949", "euc-kr"]

    for enc in encodings_to_try:
        try:
            print(f"📡 파일 읽기 시도 (인코딩: {enc})...")
            df = pd.read_csv(file_obj.name, encoding=enc)
            print(f"✅ 성공! (인코딩: {enc})")
            break  # 성공했으면 반복문 탈출
        except Exception as e:
            print(f"⚠️ {enc} 방식으로 읽기 실패.. 다음 방식 시도.")
            continue

    if df is None:
        return pd.DataFrame(
            [{"Error": "❌ 파일 형식을 알 수 없습니다. (UTF-8, CP949 모두 실패)"}]
        )

    try:
        # 컬럼 이름 소문자로 통일 (title, Title, TITLE -> title)
        df.columns = [str(c).strip().lower() for c in df.columns]

        # 필수 컬럼 확인
        if "title" not in df.columns:
            # 혹시 콤마(,) 구분자가 아니라 세미콜론(;) 등으로 된 CSV일 수도 있음
            return pd.DataFrame(
                [
                    {
                        "Error": f"CSV 파일 형식이 이상합니다. 컬럼이 하나로 뭉쳤나요? 현재 인식된 컬럼: {list(df.columns)}"
                    }
                ]
            )

        # 나머지 컬럼 채우기
        for col in ["location", "author"]:
            if col not in df.columns:
                df[col] = ""

    except Exception as e:
        return pd.DataFrame([{"Error": f"데이터 전처리 실패: {str(e)}"}])

    processed_rows = []

    # 예측 루프
    for idx, row in df.iterrows():
        title = str(row["title"])

        if not title.strip() or title.lower() == "nan":
            prediction, confidence, top_probs = "미분류", 0.0, {}
        else:
            prediction, confidence, top_probs = predict_genre(title)

        conf_display = f"{confidence:.4f}"
        if confidence <= 0.85:
            conf_display = f"<span style='color: red; font-weight: bold;'>{confidence:.4f} (Low)</span>"

        probs_str = ", ".join([f"{k}: {v:.2f}" for k, v in top_probs.items()])

        processed_rows.append(
            {
                "location": row.get("location", ""),
                "title": row["title"],
                "author": row.get("author", ""),
                "subject": prediction,
                "Confidence (Ref)": conf_display,
                "Top Candidates (Ref)": probs_str,
            }
        )

    return pd.DataFrame(processed_rows)


def save_csv(data):
    if data is None or data.empty:
        return None

    output_columns = ["location", "title", "author", "subject"]

    valid_cols = [c for c in output_columns if c in data.columns]
    final_df = data[valid_cols].copy()

    output_filename = "classified_results.csv"
    save_path = os.path.join(os.getcwd(), output_filename)
    final_df.to_csv(save_path, index=False, encoding="utf-8-sig")

    return save_path


# ==============================================================================
# [3] Gradio UI 구성 (Blocks 사용)
# ==============================================================================

with gr.Blocks(title="도서 분야 분류기") as demo:
    gr.Markdown("📚 도서 분야 분류 및 검수 시스템 📚")
    gr.Markdown(
        "CSV 파일을 업로드하면 AI가 분야(subject)를 추천합니다. confidence를 보고 직접 선택 후 다운로드 하세요."
    )
    gr.Markdown(
        "CSV 파일의 column명은 반드시 title,author,location을 포함하고 있어야 합니다."
    )

    with gr.Row():
        # [Step 1] 파일 업로드
        file_input = gr.File(
            label="CSV 파일 업로드 (location, title, author)", file_types=[".csv"]
        )
        analyze_btn = gr.Button("🔍 분석 시작", variant="primary")

    # [Step 2] 결과 확인 및 수정 (인터랙티브 테이블)
    gr.Markdown("### 분석 결과 (내용을 클릭하여 직접 수정 가능)")

    # interactive=True로 설정하여 사용자가 직접 셀을 수정할 수 있게 함
    # datatype: 각 컬럼의 형식 지정 ('markdown'을 쓰면 HTML 태그가 렌더링됨 -> 빨간글씨 가능)
    result_table = gr.Dataframe(
        label="분류 결과 (subject 컬럼을 클릭하여 수정하세요)",
        headers=[
            "location",
            "title",
            "author",
            "subject",
            "Confidence (Ref)",
            "Top Candidates (Ref)",
        ],
        datatype=["str", "str", "str", "str", "markdown", "str"],
        interactive=True,
        wrap=True,
    )

    with gr.Row():
        # [Step 3] 최종 다운로드
        save_btn = gr.Button("💾 수정사항 저장 및 CSV 생성", variant="primary")
        output_file = gr.File(label="최종 결과 다운로드", interactive=False)

    # 이벤트 연결
    # 1. 분석 버튼 클릭 -> analyze_csv 실행 -> 결과를 표에 표시
    analyze_btn.click(fn=analyze_csv, inputs=file_input, outputs=result_table)

    # 2. 저장 버튼 클릭 -> save_csv 실행 -> 최종 파일 다운로드
    save_btn.click(fn=save_csv, inputs=result_table, outputs=output_file)

# 실행
if __name__ == "__main__":
    demo.launch(share=False)
