import streamlit as st
import google.generativeai as genai
import pandas as pd
from io import BytesIO

# 1. 페이지 설정
st.set_page_config(page_title="AI 전문 심사역 시스템", layout="wide")
st.title("🚀 다중 제안서 AI 심사 & 엑셀 리포트 생성기")

# 2. 사이드바 API 키 입력
api_key = st.sidebar.text_input("Google API Key를 입력하세요", type="password")

if api_key:
    try:
        genai.configure(api_key=api_key)
        # 가장 안정적으로 작동하는 모델 이름으로 설정했습니다.
        model = genai.GenerativeModel('gemini-1.5-flash') 
        
        # 3. 입력 화면 구성
        col1, col2 = st.columns(2)
        with col1:
            eval_criteria = st.text_area("심사 기준을 입력하세요 (엑셀 내용을 복사해서 붙여넣으세요)", height=200)
        with col2:
            uploaded_files = st.file_uploader("제안서 파일들을 선택하세요 (PDF, TXT 등)", accept_multiple_files=True)

        if st.button("심사 시작 및 엑셀 생성"):
            if not uploaded_files or not eval_criteria:
                st.error("심사 기준과 제안서 파일을 모두 넣어주세요.")
            else:
                results = []
                individual_reports = {}
                progress_bar = st.progress(0)
                
                for i, uploaded_file in enumerate(uploaded_files):
                    st.write(f"분석 중: {uploaded_file.name}...")
                    
                    # 파일 읽기
                    content = uploaded_file.read().decode("utf-8", errors="ignore") 
                    
                    prompt = f"""
                    당신은 냉철한 전문 심사역입니다. 다음 심사 기준에 따라 제안서를 분석하세요.
                    [심사 기준]
                    {eval_criteria}
                    [제안서 내용]
                    {content}
                    
                    [요구사항]
                    1. 첫 줄에 '점수: 숫자, 요약: 내용' 형식으로 적어주세요.
                    2. 그 아래에 상세 리포트(리스크 및 불성실 탐지 포함)를 써주세요.
                    """
                    
                    try:
                        response = model.generate_content(prompt)
                        full_text = response.text
                        
                        # 간단한 데이터 추출
                        first_line = full_text.split('\n')[0]
                        score = first_line.split('점수:')[1].split(',')[0].strip() if '점수:' in first_line else "N/A"
                        summary = first_line.split('요약:')[1].strip() if '요약:' in first_line else "요약 없음"
                        
                        results.append({"파일명": uploaded_file.name, "점수": score, "요약": summary})
                        individual_reports[uploaded_file.name] = full_text
                    except Exception as e:
                        st.error(f"{uploaded_file.name} 처리 중 오류 발생: {e}")
                    
                    progress_bar.progress((i + 1) / len(uploaded_files))

                # 4. 엑셀 생성
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    pd.DataFrame(results).to_excel(writer, index=False, sheet_name='종합분석표')
                    for name, report in individual_reports.items():
                        pd.DataFrame([{"상세리포트": report}]).to_excel(writer, index=False, sheet_name=name[:30])
                
                st.success("심사 완료!")
                st.download_button(label="📁 엑셀 다운로드", data=output.getvalue(), file_name="AI_심사리포트.xlsx")
                
    except Exception as e:
        st.error(f"시스템 오류: {e}")
else:
    st.info("왼쪽 사이드바에 Google API Key를 입력해 주세요.")
