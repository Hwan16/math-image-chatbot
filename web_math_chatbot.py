import streamlit as st
import google.generativeai as genai
import os
import io # BytesIO 사용을 위해 추가
import PIL.Image # 이미지 처리를 위한 Pillow 라이브러리 가져오기

# --- 모델 설정 ---
AVAILABLE_MODELS = {
    "⚡️ Gemini 2.0 Flash (빠름, 효율적)": "gemini-2.0-flash",
    "🚀 Gemini 2.5 Pro Exp (실험용, 고성능)": "gemini-2.5-pro-exp-03-25",
}
DEFAULT_MODEL_NAME = "⚡️ Gemini 2.0 Flash (빠름, 효율적)"

# --- 비밀번호 확인 함수 ---
def check_password():
    # (비밀번호 확인 로직은 이전과 동일)
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

# --- Gemini API 호출 함수 ---
def get_gemini_response(prompt_parts, model_display_name, model_object):
    """주어진 프롬프트와 모델 객체로 Gemini API를 호출하고 결과를 반환"""
    gemini_response_text = ""
    try:
        response = model_object.generate_content(prompt_parts, stream=False)
        if hasattr(response, 'text'):
             gemini_response_text = response.text
        elif response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
             gemini_response_text = "".join(part.text for part in response.candidates[0].content.parts if hasattr(part, 'text'))
        else:
             safety_feedback = response.prompt_feedback
             block_reason = safety_feedback.block_reason if hasattr(safety_feedback, 'block_reason') else "알 수 없음"
             gemini_response_text = f"죄송합니다. 답변 내용을 가져올 수 없습니다. (이유: {block_reason})"
    except Exception as e:
        st.error(f"Gemini API ({model_object.model_name}) 호출 중 오류 발생: {e}")
        gemini_response_text = "오류가 발생하여 답변을 가져올 수 없습니다."
    return gemini_response_text

# --- 페이지 기본 설정 ---
st.set_page_config(page_title="수학 문제 풀이 셔틀", page_icon="🚀")

# --- 페이지 시작 시 비밀번호 확인 ---
if check_password():
    # --- 세션 상태 초기화 ---
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "current_image_bytes" not in st.session_state: # 이미지 데이터를 bytes로 저장
        st.session_state.current_image_bytes = None
    if "last_processed_image_id" not in st.session_state: # 마지막 자동 처리된 이미지 ID
        st.session_state.last_processed_image_id = None

    # --- 웹페이지 UI ---
    st.title("🔢 수학 문제 풀이 셔틀 🚀")
    st.caption("Gemini AI가 이미지 속 수학 문제를 풀어드립니다.")

    st.markdown("---")
    st.subheader("⚙️ 모델 설정")
    selected_model_display_name = st.selectbox(
        "사용할 Gemini 모델을 선택하세요:",
        options=list(AVAILABLE_MODELS.keys()),
        index=list(AVAILABLE_MODELS.keys()).index(DEFAULT_MODEL_NAME),
        key="selected_model"
    )
    selected_model_id = AVAILABLE_MODELS[selected_model_display_name]
    st.caption(f"현재 선택된 모델 ID: `{selected_model_id}`")
    st.markdown("---")

    # --- Gemini API 설정 ---
    API_KEY = st.secrets.get("GEMINI_API_KEY", None)
    if not API_KEY:
        st.error("⚠️ 중요: Streamlit Secrets에 'GEMINI_API_KEY'가 설정되지 않았습니다.")
        st.stop()
    try:
        genai.configure(api_key=API_KEY)
        model = genai.GenerativeModel(selected_model_id)
    except Exception as e:
        st.error(f"앗! Gemini 모델({selected_model_id})을 불러오는 중 문제가 발생했어요: {e}")
        st.warning("선택한 모델 이름이 정확한지, API 키에 해당 모델 접근 권한이 있는지 확인해주세요.")
        st.stop()

    # --- 이미지 업로드 처리 ---
    uploaded_file = st.file_uploader(
        "여기에 수학 문제 이미지를 업로드하세요 (PNG, JPG)",
        type=["png", "jpg", "jpeg"],
        key="file_uploader" # key를 지정하여 상태 추적 용이
    )

    # 새 이미지 업로드 감지 및 자동 처리
    if uploaded_file is not None:
        # 세션에 현재 이미지 저장 (bytes 형태로)
        current_bytes = uploaded_file.getvalue()
        st.session_state.current_image_bytes = current_bytes
        current_image_id = uploaded_file.id # 파일 업로더는 고유 ID 제공

        # 화면에 이미지 표시 (이전에 표시된 이미지와 다를 경우에만)
        # (주의: Streamlit은 스크립트 재실행 시 위젯 상태 유지하므로, 항상 이미지 표시 필요)
        st.image(current_bytes, caption="업로드된 문제 이미지", width=300)

        # 이 이미지가 이전에 자동 처리되지 않았다면 처리 시작
        if current_image_id != st.session_state.get("last_processed_image_id"):
            st.info(f"새 이미지가 감지되었습니다. {selected_model_display_name}에게 자동 풀이를 요청합니다...")
            st.session_state.messages = [] # 새 이미지이므로 이전 대화 기록 초기화 (선택사항)

            try:
                img = PIL.Image.open(io.BytesIO(current_bytes)) # bytes에서 이미지 로드

                # 자동 풀이용 프롬프트
                auto_solve_prompt = [
                    f"""당신은 한국 고등학생 수준의 수학 문제 풀이 전문가입니다.
                    최대한 자세한 풀이를 제공하여서, 첨부한 이미지 내의 수학문제를 풀어줘.
                    만약 여러 개의 문제가 있으면 첫번째로 보이는 문제를 풀어줘.
                    수식은 LaTeX 형식($$...$$ 또는 $$ ... $$)으로 작성해주세요.
                    """,
                    img
                ]

                with st.chat_message("assistant"):
                    message_placeholder = st.empty()
                    with st.spinner(f"{selected_model_display_name}가 자동 풀이 중... 🤔"):
                        # API 호출 함수 사용
                        gemini_response_text = get_gemini_response(
                            auto_solve_prompt,
                            selected_model_display_name,
                            model # 현재 선택된 모델 객체 전달
                        )
                    message_placeholder.markdown(gemini_response_text)

                # 자동 풀이 결과 메시지 저장
                st.session_state.messages.append({"role": "assistant", "content": gemini_response_text})
                # 처리된 이미지 ID 저장 (중복 실행 방지)
                st.session_state.last_processed_image_id = current_image_id

            except Exception as e:
                st.error(f"이미지 처리 또는 자동 풀이 중 오류 발생: {e}")
                # 오류 메시지도 채팅 기록에 추가 가능
                st.session_state.messages.append({"role": "assistant", "content": f"오류 발생: {e}"})
                st.session_state.last_processed_image_id = current_image_id # 오류가 나도 일단 처리된 걸로 간주

    # --- 채팅 기록 출력 ---
    # (자동 풀이 결과도 여기에 포함되어 출력됨)
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # --- 채팅 입력 처리 (추가 질문 또는 텍스트 질문) ---
    if user_input := st.chat_input(f"{selected_model_display_name}에게 질문하기..."):
        # 사용자 입력 메시지 추가 및 표시
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        prompt_parts = []
        gemini_response_text = ""

        # 현재 이미지가 있는지 확인 (추가 질문용)
        if st.session_state.current_image_bytes is not None:
            st.info(f"업로드된 이미지에 대해 {selected_model_display_name}에게 추가 질문합니다...")
            try:
                img = PIL.Image.open(io.BytesIO(st.session_state.current_image_bytes))
                prompt_parts = [
                    f"""당신은 한국 고등학생 수준의 수학 문제 풀이 전문가입니다.
                    이전에 제시된 이미지와 풀이에 대해 다음 추가 질문에 답해주세요.
                    수식은 LaTeX 형식($$...$$ 또는 $$ ... $$)으로 작성해주세요.

                    추가 질문: {user_input}
                    """,
                    img
                ]
            except Exception as e:
                 st.error(f"이미지 로딩 중 오류 발생: {e}")
                 gemini_response_text = "이미지를 다시 로드하는 데 문제가 발생했습니다."

        # 이미지가 없다면 텍스트 질문으로 처리
        else:
            st.info(f"텍스트 질문으로 {selected_model_display_name}에게 질문합니다...")
            prompt_parts = [
                 f"""당신은 한국 고등학생 수준의 수학 문제 풀이 전문가입니다.
                 다음 질문에 답해주세요. 수학 관련 질문이 아니면 관련 없다고 답변해주세요.
                 수식은 LaTeX 형식($$...$$ 또는 $$ ... $$)으로 작성해주세요.

                 질문: {user_input}
                 """
            ]

        # API 호출 및 응답 처리
        if not gemini_response_text and prompt_parts:
            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                with st.spinner(f"{selected_model_display_name}가 답변 준비 중... 🤔"):
                    # API 호출 함수 사용
                    gemini_response_text = get_gemini_response(
                        prompt_parts,
                        selected_model_display_name,
                        model
                    )
                message_placeholder.markdown(gemini_response_text)

        # 응답 메시지 저장
        if gemini_response_text:
             st.session_state.messages.append({"role": "assistant", "content": gemini_response_text})