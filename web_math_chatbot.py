import streamlit as st
import google.generativeai as genai
import os
import PIL.Image # 이미지 처리를 위한 Pillow 라이브러리 가져오기

# --- 모델 설정 ---
# 사용 가능한 모델 목록 (표시 이름: 실제 모델 ID)
AVAILABLE_MODELS = {
    "⚡️ Gemini 2.0 Flash (빠름, 효율적)": "gemini-2.0-flash",
    "🚀 Gemini 2.5 Pro Exp (실험용, 고성능)": "gemini-2.5-pro-exp-03-25",
}
DEFAULT_MODEL_NAME = "⚡️ Gemini 2.0 Flash (빠름, 효율적)"

# --- 비밀번호 확인 함수 ---
def check_password():
    """비밀번호 입력창을 표시하고 입력된 비밀번호가 secrets에 저장된 것과 일치하는지 확인"""
    try:
        correct_password = st.secrets.get("APP_PASSWORD", "test1234")
    except Exception:
        correct_password = "test1234"
        if "password_warning_shown" not in st.session_state:
             st.warning("⚠️ 로컬 테스트 모드: 임시 비밀번호 'test1234'를 사용합니다. 배포 시에는 Streamlit Secrets에 'APP_PASSWORD'를 설정해야 합니다.")
             st.session_state.password_warning_shown = True

    password_placeholder = st.empty()
    password = password_placeholder.text_input("🔑 비밀번호를 입력하세요:", type="password", key="password_input")

    if not password:
        st.info("챗봇을 사용하려면 비밀번호가 필요합니다.")
        st.stop()

    elif password == correct_password:
        password_placeholder.empty()
        return True
    else:
        st.error("❌ 비밀번호가 잘못되었습니다.")
        st.stop()
        return False

# --- 페이지 기본 설정 (스크립트 최상단) ---
st.set_page_config(page_title="수학 문제 풀이 셔틀", page_icon="🚀")

# --- 페이지 시작 시 비밀번호 확인 ---
if check_password():
    # --- 비밀번호 인증 성공 후 앱 로직 시작 ---

    # --- 웹페이지 제목 및 설명 ---
    st.title("🔢 수학 문제 풀이 셔틀 🚀")
    st.caption("Gemini AI가 이미지 속 수학 문제를 풀어드립니다.")

    # --- 모델 선택 UI (메인 화면으로 이동) ---
    st.markdown("---") # 구분선 추가
    st.subheader("⚙️ 모델 설정") # st.sidebar 제거
    selected_model_display_name = st.selectbox( # st.sidebar 제거
        "사용할 Gemini 모델을 선택하세요:",
        options=list(AVAILABLE_MODELS.keys()),
        index=list(AVAILABLE_MODELS.keys()).index(DEFAULT_MODEL_NAME),
        key="selected_model"
    )
    selected_model_id = AVAILABLE_MODELS[selected_model_display_name]
    st.caption(f"현재 선택된 모델 ID: `{selected_model_id}`") # st.sidebar 제거
    st.markdown("---") # 구분선 추가

    # --- Gemini API 설정 ---
    API_KEY = st.secrets.get("GEMINI_API_KEY", None)

    if not API_KEY:
        st.error("⚠️ 중요: Streamlit Secrets 또는 환경 변수에 'GEMINI_API_KEY'가 설정되지 않았습니다.")
        st.stop()

    try:
        genai.configure(api_key=API_KEY)
        model = genai.GenerativeModel(selected_model_id)
    except Exception as e:
        st.error(f"앗! Gemini 모델({selected_model_id})을 불러오는 중 문제가 발생했어요: {e}")
        st.warning("선택한 모델 이름이 정확한지, API 키에 해당 모델 접근 권한이 있는지 확인해주세요.")
        st.stop()


    # --- Streamlit 웹 앱 인터페이스 ---
    # (채팅 기록, 이미지 업로드, 사용자 입력 처리 로직은 이전과 동일)

    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "uploaded_image" not in st.session_state:
        st.session_state.uploaded_image = None

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    uploaded_file = st.file_uploader("여기에 수학 문제 이미지를 업로드하세요 (PNG, JPG)", type=["png", "jpg", "jpeg"])

    if uploaded_file is not None:
        st.image(uploaded_file, caption="업로드된 문제 이미지", width=300)
        st.session_state.uploaded_image = uploaded_file
        if st.session_state.get("image_processed", False) is False:
          st.info("이미지가 업로드되었습니다. 아래 채팅창에 풀이를 요청하세요 (예: '이 문제 풀어줘')")
          st.session_state.image_processed = True

    if user_input := st.chat_input(f"{selected_model_display_name}에게 질문하기..."):
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        prompt_parts = []
        gemini_response_text = ""
        current_image_to_process = st.session_state.get("uploaded_image", None)

        if current_image_to_process is not None:
            st.info(f"업로드된 이미지를 포함하여 {selected_model_display_name}에게 질문합니다...")
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
            st.info(f"텍스트 질문으로 {selected_model_display_name}에게 질문합니다...")
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
                with st.spinner(f"{selected_model_display_name}가 열심히 풀고 있어요... 🤔"):
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
                        st.error(f"Gemini API ({selected_model_id}) 호출 중 오류 발생: {e}")
                        gemini_response_text = "오류가 발생하여 답변을 가져올 수 없습니다."

                message_placeholder.markdown(gemini_response_text)

        if gemini_response_text:
             st.session_state.messages.append({"role": "assistant", "content": gemini_response_text})