import streamlit as st
import google.generativeai as genai
import pandas as pd
from io import BytesIO
from pypdf import PdfReader

# 1. 페이지 설정
st.set_page_config(page_title="AI 전문 심사역", layout="wide")
st.title("⚖️ AI 다중 제안서 심사 시스템 (무적 버전)")

# 2. 사이드바 API 키
api_key = st.sidebar.text_input("Google API Key 입력", type="password")

def extract_text_from_pdf(pdf_file):
    reader = PdfReader(pdf_file)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"
    return text

if api_key:
    try:
        genai.configure(api_key=api_key)
        
        # [핵심] 사용 가능한 모델 목록을 가져와서 가장 적합한 모델을 자동으로 선택합니다.
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        # 'flash'가 들어간 모델을 먼저 찾고, 없으면 첫 번째 모델을 선택합니다.
        selected_model_name = next((m for m in available_models if 'flash' in m), available_models[0])
        st.sidebar.info(f"사용 중인 모델: {selected_model_name}")
        
        model = genai.GenerativeModel(selected_model_name)
        
        col1, col2 = st.columns(2)
        with col1:
            eval_criteria = st.text_area("심사 기준 (엑셀 내용을 붙여넣으세요)", height=200)
        with col2:
            uploaded_files = st.file_uploader("제안서 PDF 업로드", type=['pdf'], accept_multiple_files=True)

        if st.button("🚀 심사 시작"):
            if not uploaded_files or not eval_criteria:
                st.warning("심사 기준과 파일을 모두 확인해 주세요.")
            else:
                results = []
                individual_reports = {}
                progress_bar = st.progress(0)
                
                for i, file in enumerate(uploaded_files):
                    st.write(f"🔍 {file.name} 분석 중...")
                    try:
                        pdf_text = extract_text_from_pdf(file)
                        prompt = f"심사 기준:\n{eval_criteria}\n\n제안서 내용:\n{pdf_text}\n\n위 기준에 따라 '점수: 00점, 요약: 내용' 형식으로 리포트를 작성해줘."
                        
                        response = model.generate_content(prompt)
                        full_text = response.text
                        
                        try:
                            summary_line = full_text.split('\n')[0]
                            score = summary_line.split('점수:')[1].split(',')[0].strip()
                            summary = summary_line.split('요약:')[1].strip()
                        except:
                            score = "확인필요"
                            summary = "요약 파싱 오류"

                        results.append({"기업명": file.name, "점수": score, "요약": summary})
                        individual_reports[file.name] = full_text
                    except Exception as e:
                        st.error(f"{file.name} 처리 중 오류: {str(e)}")
                    
                    progress_bar.progress((i + 1) / len(uploaded_files))

                # 엑셀 파일 생성
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    pd.DataFrame(results).to_excel(writer, index=False, sheet_name='종합분석표')
                    for name, report in individual_reports.items():
                        pd.DataFrame([{"리포트": report}]).to_excel(writer, index=False, sheet_name=name[:25])
                
                st.success("✅ 심사 완료!")
                st.download_button(label="📁 엑셀 다운로드", data=output.getvalue(), file_name="AI_심사보고서.xlsx")
                
    except Exception as e:
        st.error(f"⚠️ 설정 오류: {e}")
else:
    st.info("💡 API Key를 입력하면 시작할 수 있습니다.")
