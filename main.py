import os
import cv2
import srt
import numpy as np
import requests
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from tkinter import Tk, Label, Button, Checkbutton, IntVar
from concurrent.futures import ThreadPoolExecutor
from openai import OpenAI
from tqdm import tqdm


from config import CLAUDE_API_KEY, OPENAI_API_KEY, INPUT_DIR, OUTPUT_BASE_DIR, FONT_PATH, AVAILABLE_LANGUAGES


os.makedirs(INPUT_DIR, exist_ok=True)
os.makedirs(OUTPUT_BASE_DIR, exist_ok=True)


# === 폰트 자동 다운로드 ===
if not os.path.exists(FONT_PATH):
    print("[폰트 다운로드] NotoSans-Regular.ttf 가져오는 중...")
    url = "https://github.com/google/fonts/raw/main/ofl/notosans/NotoSans-Regular.ttf"
    with open(FONT_PATH, "wb") as f:
        f.write(requests.get(url).content)


# === [0] 입력 비디오 선택 ===
def select_input_video():
    video_files = [f for f in os.listdir(INPUT_DIR) if f.lower().endswith(('.mp4', '.avi', '.mov', '.mkv'))]
    if not video_files:
        raise Exception(f"{INPUT_DIR} 폴더에 비디오 파일이 없습니다.")
    
    if len(video_files) == 1:
        return os.path.join(INPUT_DIR, video_files[0])
    
    print("비디오 파일 선택:")
    for i, file in enumerate(video_files):
        print(f"{i+1}. {file}")
    
    while True:
        try:
            choice = int(input("번호를 선택하세요: ")) - 1
            if 0 <= choice < len(video_files):
                return os.path.join(INPUT_DIR, video_files[choice])
            else:
                print("잘못된 번호입니다.")
        except ValueError:
            print("숫자를 입력하세요.")


# === [1] 번역 언어 선택 GUI ===
selected_languages = []


def select_languages_gui():
    def on_submit():
        global selected_languages
        selected_languages = [lang for lang, var in zip(AVAILABLE_LANGUAGES, vars_) if var.get() == 1]
        root.destroy()

    root = Tk()
    root.title("번역할 언어 선택")
    Label(root, text="번역할 언어를 선택하세요:", font=("Arial", 14)).pack(pady=10)

    vars_ = []
    for lang in AVAILABLE_LANGUAGES:
        var = IntVar()
        Checkbutton(root, text=lang, variable=var, font=("Arial", 12)).pack(anchor="w", padx=20)
        vars_.append(var)

    Button(root, text="확인", command=on_submit, font=("Arial", 12)).pack(pady=10)
    root.mainloop()


# === [2] 자막 영역 GUI 선택 ===
def select_blur_region(video_path):
    cap = cv2.VideoCapture(video_path)
    ret, frame = cap.read()
    cap.release()

    if not ret:
        raise Exception("영상 첫 프레임을 불러올 수 없습니다.")

    roi = cv2.selectROI("자막 영역 선택 (드래그 후 Enter)", frame, showCrosshair=True)
    cv2.destroyAllWindows()
    x, y, w, h = roi
    return (x, y, x + w, y + h)


# === [3] Whisper로 원문 자막 추출 ===
def transcribe_video(video_path, output_dir):
    # 비디오에서 오디오 추출
    print("비디오에서 오디오 추출 중...")
    audio_path = os.path.join(output_dir, "temp_audio.wav")
    
    try:
        # OpenCV로 비디오에서 오디오 추출 (ffmpeg 필요없이)
        import subprocess
        result = subprocess.run([
            'ffmpeg', '-i', video_path, '-vn', '-acodec', 'pcm_s16le', 
            '-ar', '16000', '-ac', '1', audio_path, '-y'
        ], capture_output=True, text=True, timeout=300)
        
        if result.returncode != 0:
            # ffmpeg가 없거나 실패한 경우, 대안 방법
            raise Exception("ffmpeg를 사용한 오디오 추출 실패")
            
    except:
        # 대안: 비디오 파일을 직접 사용하되 확장자 확인
        print("오디오 추출 실패, 원본 파일 직접 사용...")
        audio_path = video_path
    
    # 파일 크기 체크
    file_size = os.path.getsize(audio_path) / (1024 * 1024)  # MB
    if file_size > 25:
        raise Exception(f"파일 크기가 {file_size:.1f}MB로 Whisper API 제한(25MB)을 초과합니다. 파일을 압축하거나 짧게 나누어 주세요.")
    
    client = OpenAI(api_key=OPENAI_API_KEY)
    try:
        with open(audio_path, "rb") as f:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=f,
                response_format="srt",
                language="ko"
            )
        
        # 임시 오디오 파일 삭제
        if audio_path != video_path and os.path.exists(audio_path):
            os.remove(audio_path)
        
        # 원본 자막을 output 폴더에 저장
        srt_path = os.path.join(output_dir, "original_korean.srt")
        with open(srt_path, "w", encoding="utf-8") as f:
            f.write(transcript)
        
        # 텍스트만 추출해서 별도 저장
        import srt
        subs = list(srt.parse(transcript))
        text_content = "\n".join([sub.content for sub in subs])
        
        txt_path = os.path.join(output_dir, "original_korean.txt")
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(text_content)
        
        return srt_path
    except Exception as e:
        # 임시 파일 정리
        if audio_path != video_path and os.path.exists(audio_path):
            os.remove(audio_path)
        raise Exception(f"Whisper API 오류: {str(e)}. 오디오 형식을 확인하거나 파일을 다른 형식으로 변환해주세요.")


# === [4] Claude API 번역 ===
def translate_text_claude(text, target_lang):
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": CLAUDE_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    payload = {
        "model": "claude-3-haiku-20240307",
        "max_tokens": 1000,
        "messages": [
            {"role": "user", "content": f"Translate this Korean text to {target_lang}. Only provide the translation, no explanations or additional text:\n{text}"}
        ]
    }
    
    try:
        res = requests.post(url, json=payload, headers=headers)
        data = res.json()
        
        # API 응답 구조 확인
        if "content" in data and len(data["content"]) > 0:
            translated_text = data["content"][0]["text"].strip()
            
            # Claude의 설명 텍스트 제거
            lines = translated_text.split('\n')
            for line in lines:
                line = line.strip()
                if line and not line.lower().startswith(('the translation', 'here is', 'the korean text', 'translated to', 'translation:')):
                    # 따옴표로 감싸진 텍스트면 따옴표 제거
                    if line.startswith('"') and line.endswith('"'):
                        return line[1:-1]
                    else:
                        return line
            
            # 만약 위 조건에 맞는 라인이 없으면 전체 텍스트 반환
            return translated_text
        elif "error" in data:
            print(f"Claude API 오류: {data['error']}")
            return f"[번역 실패: {target_lang}] {text}"
        else:
            print(f"예상치 못한 응답 구조: {data}")
            return f"[번역 실패: {target_lang}] {text}"
            
    except Exception as e:
        print(f"번역 요청 오류: {e}")
        return f"[번역 실패: {target_lang}] {text}"


# === [5] 병렬 번역 처리 + 진행률 ===
def create_translations_parallel(srt_file, languages, output_dir):
    with open(srt_file, "r", encoding="utf-8") as f:
        subs = list(srt.parse(f.read()))

    translations = {lang: [] for lang in languages}

    def translate_for_lang(lang):
        lang_translations = []
        lang_timing_data = []
        
        for sub in tqdm(subs, desc=f"번역 중 ({lang})", unit="문장"):
            translated = translate_text_claude(sub.content, lang)
            lang_timing_data.append((sub.start.total_seconds(), sub.end.total_seconds(), translated))
            lang_translations.append(translated)
        
        # 각 언어별 번역 텍스트 저장
        txt_path = os.path.join(output_dir, f"translated_{lang}.txt")
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lang_translations))
        
        return lang, lang_timing_data

    # 병렬 처리 후 결과 수집
    with ThreadPoolExecutor(max_workers=len(languages)) as executor:
        results = executor.map(translate_for_lang, languages)
        for lang, timing_data in results:
            translations[lang] = timing_data

    return translations


# === [6] 영상 처리 + 진행률 ===
def generate_video(video_path, translations, lang, blur_region, output_dir):
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    out_path = os.path.join(output_dir, f"{lang}.mp4")
    # 더 호환성 좋은 코덱 사용
    fourcc = cv2.VideoWriter_fourcc(*'avc1')  # H.264 코덱
    out = cv2.VideoWriter(out_path, fourcc, fps, (w, h))

    frame_idx = 0
    try:
        font = ImageFont.truetype(FONT_PATH, 50)  # 폰트 크기 증가
    except:
        # 폰트 로드 실패시 기본 폰트 사용
        font = ImageFont.load_default()
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    pbar = tqdm(total=total_frames, desc=f"{lang} 영상 처리", unit="프레임")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        current_time = frame_idx / fps
        current_text = ""
        
        # SRT 타이밍 기반으로 텍스트 찾기
        for start, end, text in translations:
            if start <= current_time <= end:
                # 번역된 텍스트에서 불필요한 부분 제거
                clean_text = text.strip()
                if clean_text.startswith("Here is the") or clean_text.startswith("The translation"):
                    # 여러 줄에서 실제 번역 부분만 추출
                    lines = clean_text.split('\n')
                    for line in lines:
                        line = line.strip()
                        if line and not line.startswith(("Here is", "The translation", "Here's")):
                            if line.startswith('"') and line.endswith('"'):
                                current_text = line[1:-1]  # 따옴표 제거
                            else:
                                current_text = line
                            break
                else:
                    current_text = clean_text
                break

        # 회색 박스 처리 (블러 대신)
        x1, y1, x2, y2 = blur_region
        if y2 > y1 and x2 > x1:  # 올바른 좌표인지 확인
            # 회색 박스로 덮기 (RGB: 80, 80, 80 - 어두운 회색)
            cv2.rectangle(frame, (x1, y1), (x2, y2), (80, 80, 80), -1)

        # 번역 텍스트 추가 - OpenCV를 사용하여 직접 렌더링
        if current_text:
            # 텍스트를 블러 영역 중앙에 배치
            text_x = x1 + 15
            text_y = y1 + 60
            
            # 더 큰 폰트 설정
            font_scale = 1.8  # 폰트 크기 증가 (1.2 → 1.8)
            font_thickness = 3  # 텍스트 두께 증가 (2 → 3)
            outline_thickness = 6  # 외곽선 두께 증가 (4 → 6)
            line_spacing = 55  # 줄 간격 증가 (40 → 55)
            
            # 텍스트 길이에 따라 여러 줄로 분할
            max_width = (x2 - x1) - 30  # 좌우 여백 줄임
            words = current_text.split(' ')
            lines = []
            current_line = ""
            
            for word in words:
                test_line = current_line + " " + word if current_line else word
                text_size = cv2.getTextSize(test_line, cv2.FONT_HERSHEY_DUPLEX, font_scale, font_thickness)[0]
                if text_size[0] <= max_width:
                    current_line = test_line
                else:
                    if current_line:
                        lines.append(current_line)
                        current_line = word
                    else:
                        lines.append(word)  # 단어가 너무 길면 강제로 추가
            
            if current_line:
                lines.append(current_line)
            
            # 각 줄을 렌더링
            for i, line in enumerate(lines):
                y_pos = text_y + (i * line_spacing)
                if y_pos < y2 - 30:  # 블러 영역을 벗어나지 않도록
                    # 더 두꺼운 검은색 외곽선으로 가독성 극대화
                    cv2.putText(frame, line, (text_x, y_pos), cv2.FONT_HERSHEY_DUPLEX, font_scale, (0, 0, 0), outline_thickness)
                    # 흰색 텍스트를 더 두껍게
                    cv2.putText(frame, line, (text_x, y_pos), cv2.FONT_HERSHEY_DUPLEX, font_scale, (255, 255, 255), font_thickness)

        out.write(frame)
        frame_idx += 1
        pbar.update(1)

    pbar.close()
    out.release()
    cap.release()


# === 실행 ===
if __name__ == "__main__":
    print("[0/6] 입력 비디오 선택")
    input_video_path = select_input_video()
    video_name = os.path.splitext(os.path.basename(input_video_path))[0]
    output_dir = os.path.join(OUTPUT_BASE_DIR, f"{video_name}_translated")
    os.makedirs(output_dir, exist_ok=True)
    print(f"선택된 비디오: {input_video_path}")

    print("[1/6] 번역 언어 선택")
    select_languages_gui()
    print(f"선택된 언어: {selected_languages}")

    print("[2/6] 자막 영역 선택")
    blur_coords = select_blur_region(input_video_path)

    print("[3/6] 원문 자막 생성 중...")
    srt_path = transcribe_video(input_video_path, output_dir)

    print("[4/6] 번역 생성 중 (병렬 처리)")
    translations_dict = create_translations_parallel(srt_path, selected_languages, output_dir)

    print("[5/6] 영상 생성 중...")
    for lang in selected_languages:
        generate_video(input_video_path, translations_dict[lang], lang, blur_coords, output_dir)

    print(f"[완료] 모든 영상이 {output_dir} 폴더에 저장됨 ✅")