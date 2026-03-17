import streamlit as st
import google.generativeai as genai
import pandas as pd
from io import BytesIO

# 1. 환경 설정 (페이지 타이틀)
st.set_page_config(page_title="AI 전문 심사역 시스템", layout="wide")
st.title("🚀 다중 제안서 AI 심사 & 엑셀 리포트 생성기")

# 2. API 키 입력 (나중에 본인의 키를 넣으세요)
api_key = st.sidebar.text_input("Google API Key를 입력하세요", type="password")

if api_key:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash') # 속도가 빠른 플래시 모델 추천

    # 3. 파일 업로드 및 심사 기준 입력
    col1, col2 = st.columns(2)
    with col1:
        eval_criteria = st.text_area("심사 기준을 입력하세요 (엑셀 내용을 복사해서 붙여넣어도 됩니다)", height=200)
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
                
                # 파일 내용 읽기 (간단화를 위해 텍스트 추출 방식 사용)
                content = uploaded_file.read().decode("utf-8", errors="ignore") 
                
                # AI에게 전달할 프롬프트 (까칠한 심사역 모드)
                prompt = f"""
                당신은 냉철한 전문 심사역입니다. 다음 심사 기준에 따라 제안서를 분석하세요.
                
                [심사 기준]
                {eval_criteria}
                
                [제안서 내용]
                {content}
                
                [요구사항]
                1. 먼저 '종합 점수(100점 만점)'와 '핵심 요약(한 줄)'을 '점수: 숫자, 요약: 내용' 형식으로 한 줄 적어주세요.
                2. 그 아래에는 상세 리포트를 작성하세요. (지능형 리서치, 리포트 자동화, 불성실 탐지 포함)
                """
                
                response = model.generate_content(prompt)
                full_text = response.text
                
                # 데이터 분리 (요약표용 데이터 추출 시도)
                try:
                    score_line = full_text.split('\n')[0]
                    score = score_line.split('점수:')[1].split(',')[0].strip()
                    summary = score_line.split('요약:')[1].strip()
                except:
                    score = "N/A"
                    summary = "요약 추출 실패"

                results.append({"기업/파일명": uploaded_file.name, "점수": score, "핵심 요약": summary})
                individual_reports[uploaded_file.name] = full_text
                
                progress_bar.progress((i + 1) / len(uploaded_files))

            # 4. 엑셀 파일 생성
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                # 시트 1: 종합 분석표
                df_summary = pd.DataFrame(results)
                df_summary.to_excel(writer, index=False, sheet_name='종합분석표')
                
                # 기업별 개별 시트 추가
                for name, report in individual_reports.items():
                    # 시트 이름 제한(31자) 대응
                    clean_name = name[:30].replace("[", "").replace("]", "")
                    df_report = pd.DataFrame([{"상세 리포트": report}])
                    df_report.to_excel(writer, index=False, sheet_name=clean_name)
            
            st.success("모든 심사가 완료되었습니다!")
            
            # 5. 다운로드 버튼
            st.download_button(
                label="📁 심사 결과 엑셀 다운로드",
                data=output.getvalue(),
                file_name="AI_심사_결과보고서.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

else:
    st.info("왼쪽 사이드바에 Google API Key를 입력하면 시작할 수 있습니다.")
