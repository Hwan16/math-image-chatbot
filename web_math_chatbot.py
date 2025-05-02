import streamlit as st
import google.generativeai as genai
import os
import PIL.Image # 이미지 처리를 위한 Pillow 라이브러리 가져오기

# --- 비밀번호 확인 함수 ---
def check_password():
    """비밀번호 입력창을 표시하고 입력된 비밀번호가 secrets에 저장된 것과 일치하는지 확인"""
    try:
        # 로컬 테스트 시에는 secrets 파일이 없을 수 있으므로, 임시 비밀번호 사용 또는 에러 처리
        # 실제 배포 시에는 Streamlit Cloud의 secrets에 APP_PASSWORD 설정 필요
        correct_password = st.secrets.get("APP_PASSWORD", "test1234") # secrets에 없으면 임시 비밀번호 'test1234' 사용
    except Exception:
        # st.secrets 사용 불가 시 (예: 로컬에서 secrets 파일 미설정) 임시 비밀번호 사용
        correct_password = "test1234" # 로컬 테스트용 임시 비밀번호 (배포 시 무의미)
        # 로컬 테스트 시 경고 메시지를 한 번만 표시하기 위한 로직 (선택 사항)
        if "password_warning_shown" not in st.session_state:
             st.warning("⚠️ 로컬 테스트 모드: 임시 비밀번호 'test1234'를 사용합니다. 배포 시에는 Streamlit Secrets에 'APP_PASSWORD'를 설정해야 합니다.")
             st.session_state.password_warning_shown = True

    # 페이지 상단에 비밀번호 입력 필드 표시
    password_placeholder = st.empty() # 입력 필드를 위한 공간 확보
    password = password_placeholder.text_input("🔑 비밀번호를 입력하세요:", type="password", key="password_input") # key 추가로 상태 유지 도움

    if not password: # 비밀번호를 아직 입력하지 않았으면 아무것도 안 함 (입력 대기)
        st.info("챗봇을 사용하려면 비밀번호가 필요합니다.")
        st.stop() # 메인 앱 로딩 중지

    elif password == correct_password:
        # 비밀번호가 맞으면 입력 필드를 숨기고 True 반환
        password_placeholder.empty() # 비밀번호 입력창 숨기기
        return True
    else:
        # 비밀번호가 틀리면 오류 메시지 표시
        st.error("❌ 비밀번호가 잘못되었습니다.")
        st.stop() # 메인 앱 로딩 중지
        return False

# --- 페이지 시작 시 비밀번호 확인 ---
# st.set_page_config는 스크립트 최상단에 딱 한 번만 호출되어야 함
st.set_page_config(page_title="수학 문제 풀이 셔틀", page_icon="🚀")

if check_password():
    # --- 비밀번호 인증 성공 후 앱 로직 시작 ---
    st.success("🔑 인증 성공! 챗봇을 시작합니다.", icon="✅") # 성공 메시지 (선택 사항)

    # --- 웹페이지 제목 및 설명 (인증 후 표시) ---
    st.title("🔢 수학 문제 풀이 셔틀 🚀")
    st.caption("Gemini AI가 이미지 속 수학 문제를 풀어드립니다.")

    # --- Gemini API 설정 ---
    # st.secrets를 사용하면 Streamlit 배포 시 API 키를 안전하게 관리할 수 있습니다.
    # !!! 중요: 절대로 코드에 실제 API 키를 남기면 안 됩니다! 배포 시 Secrets 사용 필수!
    API_KEY = st.secrets.get("GEMINI_API_KEY", None) # Secrets에서 API 키 가져오기 시도

    # 로컬 테스트용: Secrets에 키가 없을 경우 환경 변수 또는 직접 입력 (주의!)
    if not API_KEY:
        # 로컬에서 환경변수 사용을 권장하나, 여기서는 임시 방편으로 직접 입력 예시 포함 (배포 전 삭제/수정 필수!)
        # API_KEY = "여기에_새로_만든_API_키를_붙여넣으세요" # <<< 실제 배포 시 이 줄은 삭제하거나 Secrets 방식으로만 사용해야 함!
        # 위 줄 대신 경고 표시
        st.error("⚠️ 중요: Streamlit Secrets 또는 환경 변수에 'GEMINI_API_KEY'가 설정되지 않았습니다. 로컬 테스트가 제한될 수 있습니다.")
        # API 키가 없으면 여기서 멈추도록 처리
        st.stop()


    try:
        # API 키로 Gemini 라이브러리 설정
        genai.configure(api_key=API_KEY)

        # 사용할 Gemini 모델 선택 (실험용 모델 시도)
        model = genai.GenerativeModel('gemini-2.5-pro-exp-03-25')

        # 모델 로드 확인 (터미널에 메시지가 보이면 성공, 앱에서는 제거해도 무방)
        # print("✨ Gemini 모델이 성공적으로 연결되었습니다! ✨")

    except Exception as e:
        # 설정 과정에서 오류가 발생하면 웹페이지에 에러 메시지 표시
        st.error(f"앗! Gemini 설정 중 문제가 발생했어요: {e}")
        st.stop() # 설정 실패 시 앱 실행 중지


    # --- Streamlit 웹 앱 인터페이스 (인증 후 표시) ---

    # 이전 대화 기록 및 업로드된 이미지 저장을 위한 공간 만들기
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "uploaded_image" not in st.session_state:
        st.session_state.uploaded_image = None # 이미지 저장 공간 초기화

    # 이전 대화 기록 출력
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # --- 이미지 업로드 및 처리 ---
    uploaded_file = st.file_uploader("여기에 수학 문제 이미지를 업로드하세요 (PNG, JPG)", type=["png", "jpg", "jpeg"])

    if uploaded_file is not None:
        # 새 이미지가 업로드되면, 화면에 표시하고 session_state에 저장
        st.image(uploaded_file, caption="업로드된 문제 이미지", width=300)
        st.session_state.uploaded_image = uploaded_file # 현재 업로드된 이미지를 기억
        if st.session_state.get("image_processed", False) is False:
          st.info("이미지가 업로드되었습니다. 아래 채팅창에 풀이를 요청하세요 (예: '이 문제 풀어줘')")
          st.session_state.image_processed = True

    # --- 사용자 입력 및 Gemini 호출 ---
    if user_input := st.chat_input("이미지를 올렸다면 풀이를 요청하거나, 질문을 입력하세요..."):
        # 사용자 메시지 표시 및 기록
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        # Gemini에게 보낼 요청 준비 (이미지 + 텍스트 또는 텍스트만)
        prompt_parts = []
        gemini_response_text = ""

        current_image_to_process = st.session_state.get("uploaded_image", None)

        if current_image_to_process is not None:
            st.info("업로드된 이미지를 포함하여 Gemini에게 질문합니다...")
            try:
                img = PIL.Image.open(current_image_to_process)
                prompt_parts = [
                    f"""당신은 한국 고등학생 수준의 수학 문제 풀이 전문가입니다.
                    주어진 이미지 속의 수학 문제를 단계별로 상세하게 풀이하고, 최종 답을 명확하게 제시해주세요.
                    수식은 LaTeX 형식($$...$$ 또는 $$ ... $$)으로 작성해주세요.

                    사용자 추가 요청/질문: {user_input}
                    """,
                    img
                ]
            except Exception as e:
                st.error(f"이미지 처리 중 오류 발생: {e}")
                gemini_response_text = "이미지를 처리하는 데 문제가 발생했습니다."
                st.session_state.messages.append({"role": "assistant", "content": gemini_response_text})

        else:
            st.info("텍스트 질문으로 Gemini에게 질문합니다...")
            prompt_parts = [
                 f"""당신은 한국 고등학생 수준의 수학 문제 풀이 전문가입니다.
                 다음 질문에 답해주세요. 수학 관련 질문이 아니면 관련 없다고 답변해주세요.
                 수식은 LaTeX 형식($$...$$ 또는 $$ ... $$)으로 작성해주세요.

                 질문: {user_input}
                 """
            ]

        if not gemini_response_text and prompt_parts:
            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                with st.spinner("Gemini가 열심히 풀고 있어요... 잠시만 기다려주세요! 🤔"):
                    try:
                        response = model.generate_content(prompt_parts, stream=False)
                        if hasattr(response, 'text'):
                             gemini_response_text = response.text
                        elif response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
                             gemini_response_text = "".join(part.text for part in response.candidates[0].content.parts if hasattr(part, 'text'))
                        else:
                             safety_feedback = response.prompt_feedback
                             block_reason = safety_feedback.block_reason if hasattr(safety_feedback, 'block_reason') else "알 수 없음"
                             gemini_response_text = f"죄송합니다. 답변 내용을 가져올 수 없습니다. (이유: {block_reason})"
                    except Exception as e:
                        st.error(f"Gemini API 호출 중 오류 발생: {e}")
                        gemini_response_text = "오류가 발생하여 답변을 가져올 수 없습니다."

                message_placeholder.markdown(gemini_response_text)

        if gemini_response_text:
             st.session_state.messages.append({"role": "assistant", "content": gemini_response_text})