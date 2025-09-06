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
from color_selector import select_background_colors


from config import CLAUDE_API_KEY, OPENAI_API_KEY, INPUT_DIR, OUTPUT_BASE_DIR, FONT_PATH, FONTS, TITLE_FONTS, SUBTITLE_FONTS, AVAILABLE_LANGUAGES


os.makedirs(INPUT_DIR, exist_ok=True)
os.makedirs(OUTPUT_BASE_DIR, exist_ok=True)


# === 다국어 폰트 자동 다운로드 ===
def download_fonts():
    """필요한 폰트들을 자동으로 다운로드"""
    # 시스템 폰트 사용을 위한 폴백 체인
    print("📝 시스템 폰트 사용으로 변경합니다.")
    return
    
    for font_file, url in font_urls.items():
        if not os.path.exists(font_file):
            try:
                print(f"[폰트 다운로드] {font_file} 가져오는 중...")
                response = requests.get(url, timeout=30)
                with open(font_file, "wb") as f:
                    f.write(response.content)
                print(f"✅ {font_file} 다운로드 완료")
            except Exception as e:
                print(f"⚠️  {font_file} 다운로드 실패: {e}")

# 폰트 다운로드 실행
download_fonts()


# === 언어별 폰트 선택 함수 ===
def get_title_font_for_language(language):
    """언어에 맞는 타이틀 폰트 파일 경로 반환"""
    language_lower = language.lower()
    
    if language_lower in TITLE_FONTS:
        return TITLE_FONTS[language_lower]
    elif language_lower in ["chinese", "chinese simplified", "chinese traditional"]:
        return TITLE_FONTS["chinese"]
    else:
        return TITLE_FONTS["default"]

def wrap_text_to_lines(text, font, max_width, draw):
    """텍스트를 주어진 폭에 맞게 여러 줄로 나누기"""
    words = text.split(' ')
    lines = []
    current_line = ""
    
    for word in words:
        test_line = current_line + " " + word if current_line else word
        bbox = draw.textbbox((0, 0), test_line, font=font)
        line_width = bbox[2] - bbox[0]
        
        if line_width <= max_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
                current_line = word
            else:
                # 단어가 너무 길면 강제로 추가
                lines.append(word)
    
    if current_line:
        lines.append(current_line)
    
    return lines

def get_subtitle_font_for_language(language):
    """언어에 맞는 자막 폰트 파일 경로 반환"""
    language_lower = language.lower()
    
    if language_lower in SUBTITLE_FONTS:
        return SUBTITLE_FONTS[language_lower]
    elif language_lower in ["chinese", "chinese simplified", "chinese traditional"]:
        return SUBTITLE_FONTS["chinese"]
    else:
        return SUBTITLE_FONTS["default"]

# 하위 호환성을 위한 기존 함수 (타이틀 폰트로 매핑)
def get_font_for_language(language):
    """언어에 맞는 폰트 파일 경로 반환 (타이틀용)"""
    return get_title_font_for_language(language)

def get_font_fallback_chain(language):
    """언어별 폰트 폴백 체인 반환"""
    primary_font = get_font_for_language(language)
    return [primary_font, FONTS["default"], "Arial", "DejaVu Sans"]

def render_title_text(frame, title_text, title_region, language, bg_color=(0, 0, 0)):
    """타이틀 텍스트를 영역에 2줄로 나누어 최대 크기로 렌더링"""
    if not title_text or not title_region:
        return
    
    tx1, ty1, tx2, ty2 = title_region
    if ty2 <= ty1 or tx2 <= tx1:
        return
    
    # 지정된 색상으로 타이틀 영역 덮기
    cv2.rectangle(frame, (tx1, ty1), (tx2, ty2), bg_color, -1)
    
    # 타이틀 영역 크기
    region_width = tx2 - tx1
    region_height = ty2 - ty1
    
    # 여백 설정 (더 작게 설정하여 더 큰 폰트 사용)
    margin_x = int(region_width * 0.03)  # 3% 여백
    margin_y = int(region_height * 0.05)  # 5% 여백
    text_width = region_width - (margin_x * 2)
    text_height = region_height - (margin_y * 2)
    
    # 2줄로 나누기 위한 폰트 설정
    font_thickness = 4
    outline_thickness = 8
    target_lines = 2  # 항상 2줄로 표시
    
    # 텍스트를 2줄로 나누기
    words = title_text.split()
    if len(words) == 1:
        # 단어가 하나면 그대로
        lines = [words[0]]
    elif len(words) == 2:
        # 단어가 두 개면 각각 한 줄씩
        lines = words
    else:
        # 단어가 3개 이상이면 균등하게 2줄로 나누기
        mid_point = len(words) // 2
        line1 = " ".join(words[:mid_point])
        line2 = " ".join(words[mid_point:])
        lines = [line1, line2]
    
    # PIL 폰트를 사용하여 정확한 크기 계산
    print(f"  📏 타이틀 영역 크기: {region_width}x{region_height}, 텍스트 영역: {text_width}x{text_height}")
    
    # 언어에 맞는 폰트 경로 가져오기
    font_path = get_title_font_for_language(language)
    print(f"  🔤 타이틀 폰트 경로: {font_path}")
    
    # PIL 폰트로 최적 크기 찾기
    best_pil_font_size = 20
    line_spacing = 15  # 줄 간격
    
    # PIL 폰트 크기를 큰 것부터 테스트
    for pil_size in range(80, 15, -5):  # 80부터 20까지 5씩 감소
        try:
            test_font = ImageFont.truetype(font_path, pil_size)
            
            # 임시 이미지에서 텍스트 크기 측정
            temp_img = Image.new('RGB', (1, 1))
            temp_draw = ImageDraw.Draw(temp_img)
            
            # 각 줄의 최대 너비와 전체 높이 계산
            max_line_width = 0
            total_height = 0
            
            for i, line in enumerate(lines):
                bbox = temp_draw.textbbox((0, 0), line, font=test_font)
                line_width = bbox[2] - bbox[0]
                line_height = bbox[3] - bbox[1]
                max_line_width = max(max_line_width, line_width)
                
                if i == 0:  # 첫 번째 줄
                    total_height = line_height
                else:  # 추가 줄들
                    total_height += line_height + line_spacing
            
            # 영역에 맞는지 확인
            if max_line_width <= text_width and total_height <= text_height:
                best_pil_font_size = pil_size
                print(f"  ✅ 최적 폰트 크기 발견: {pil_size}px, 텍스트 크기: {max_line_width}x{total_height}")
                break
                
        except Exception as e:
            print(f"  ⚠️  폰트 크기 {pil_size} 테스트 실패: {e}")
            continue
    
    print(f"  📐 최종 선택된 폰트 크기: {best_pil_font_size}px")
    
    print(f"🎨 타이틀 렌더링: '{title_text}' → {len(lines)}줄 (PIL 폰트 크기: {best_pil_font_size}px)")
    print(f"   영역: ({tx1},{ty1})-({tx2},{ty2}), 크기: {region_width}x{region_height}px")
    print(f"   텍스트 영역: {text_width}x{text_height}px, 여백: {margin_x}x{margin_y}px")
    
    # PIL 이미지로 변환하여 렌더링 시작
    pil_image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(pil_image)
    
    # 최종 폰트 로드
    try:
        pil_font = ImageFont.truetype(font_path, best_pil_font_size)
        print(f"  ✅ 타이틀 폰트 로드 성공: {font_path} (크기: {best_pil_font_size})")
    except Exception as e:
        print(f"  ❌ 타이틀 폰트 로드 실패, 기본 폰트 사용: {e}")
        pil_font = ImageFont.load_default()
    
    # 각 줄의 높이와 전체 높이 계산
    line_heights = []
    total_text_height = 0
    
    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=pil_font)
        line_height = bbox[3] - bbox[1]
        line_heights.append(line_height)
        
        if i == 0:
            total_text_height = line_height
        else:
            total_text_height += line_height + line_spacing
    
    # 수직 중앙 정렬을 위한 시작 Y 좌표
    start_y = ty1 + margin_y + (text_height - total_text_height) // 2
    
    # 각 줄을 렌더링
    current_y = start_y
    
    for i, line in enumerate(lines):
        if not line.strip():
            continue
        
        # 현재 줄의 높이
        line_height = line_heights[i]
        
        # 영역을 벗어나지 않도록 확인
        if current_y + line_height > ty2 - margin_y:
            print(f"  ⚠️  {i+1}번째 줄이 영역을 벗어남, 스킵")
            break
        
        # 수평 중앙 정렬을 위한 X 좌표 계산
        bbox = draw.textbbox((0, 0), line, font=pil_font)
        line_width = bbox[2] - bbox[0]
        text_x = tx1 + margin_x + (text_width - line_width) // 2
        text_y = current_y
        
        print(f"  📍 {i+1}번째 줄 렌더링: '{line}' at ({text_x}, {text_y})")
        
        # 외곽선 효과 (검은색)
        for dx in [-3, -2, -1, 0, 1, 2, 3]:
            for dy in [-3, -2, -1, 0, 1, 2, 3]:
                if dx != 0 or dy != 0:
                    draw.text((text_x + dx, text_y + dy), line, font=pil_font, fill=(0, 0, 0))
        
        # 메인 텍스트 (흰색)
        draw.text((text_x, text_y), line, font=pil_font, fill=(255, 255, 255))
        
        # 다음 줄 위치 계산
        current_y += line_height + line_spacing
    
    # PIL에서 OpenCV로 변환
    frame[:] = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
    print(f"  🎬 타이틀 렌더링 완료")

def render_subtitle_text(frame, subtitle_text, subtitle_region, language, bg_color=(220, 220, 220)):
    """자막 텍스트를 다국어 폰트로 렌더링 (PIL 기반)"""
    if not subtitle_text or not subtitle_region:
        return
    
    # 텍스트 인코딩 확인 및 정규화
    if isinstance(subtitle_text, bytes):
        try:
            subtitle_text = subtitle_text.decode('utf-8')
        except UnicodeDecodeError:
            subtitle_text = subtitle_text.decode('utf-8', errors='replace')
    
    # 텍스트 내용 디버깅
    print(f"  🔍 자막 텍스트 분석:")
    print(f"     원본: '{subtitle_text}'")
    print(f"     타입: {type(subtitle_text)}")
    print(f"     길이: {len(subtitle_text)}")
    print(f"     언어: {language}")
    
    # 빈 텍스트나 ??? 텍스트 확인
    if not subtitle_text.strip() or subtitle_text.strip() == "???":
        print(f"  ⚠️  빈 텍스트이거나 ??? 텍스트입니다: '{subtitle_text}'")
        return
    
    sx1, sy1, sx2, sy2 = subtitle_region
    if sy2 <= sy1 or sx2 <= sx1:
        return
    
    # 지정된 색상으로 자막 영역 덮기
    cv2.rectangle(frame, (sx1, sy1), (sx2, sy2), bg_color, -1)
    
    # 자막 영역 크기
    region_width = sx2 - sx1
    region_height = sy2 - sy1
    
    # 여백 설정
    margin_x = 20
    margin_y = 15
    text_width = region_width - (margin_x * 2)
    text_height = region_height - (margin_y * 2)
    
    print(f"  📏 자막 영역 크기: {region_width}x{region_height}, 텍스트 영역: {text_width}x{text_height}")
    
    # 언어에 맞는 자막 폰트 경로 가져오기
    subtitle_font_path = get_subtitle_font_for_language(language)
    print(f"  🔤 자막 폰트 경로: {subtitle_font_path}")
    
    # PIL 이미지로 변환
    pil_image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(pil_image)
    
    # 적절한 폰트 크기 찾기
    best_font_size = 25
    line_spacing = 10
    
    for font_size in range(40, 15, -2):  # 40부터 16까지 2씩 감소
        try:
            test_font = ImageFont.truetype(subtitle_font_path, font_size)
            
            # 텍스트를 줄별로 나누기 테스트
            test_lines = wrap_text_to_lines(subtitle_text, test_font, text_width, draw)
            
            # 전체 높이 계산
            total_height = 0
            for i, line in enumerate(test_lines):
                bbox = draw.textbbox((0, 0), line, font=test_font)
                line_height = bbox[3] - bbox[1]
                if i == 0:
                    total_height = line_height
                else:
                    total_height += line_height + line_spacing
            
            # 영역에 맞는지 확인
            if total_height <= text_height:
                best_font_size = font_size
                print(f"  ✅ 자막 최적 폰트 크기: {font_size}px, 예상 줄 수: {len(test_lines)}")
                break
                
        except Exception as e:
            continue
    
    # 최종 폰트 로드 (폴백 체인 사용)
    subtitle_font = None
    font_attempts = [
        subtitle_font_path,
        SUBTITLE_FONTS.get("default", "/Library/Fonts/Arial Unicode.ttf"),
        "/System/Library/Fonts/Arial Unicode.ttf",
        "/Library/Fonts/Arial.ttf"
    ]
    
    for attempt_path in font_attempts:
        try:
            subtitle_font = ImageFont.truetype(attempt_path, best_font_size)
            print(f"  ✅ 자막 폰트 로드 성공: {attempt_path} (크기: {best_font_size})")
            
            # 폰트가 특정 문자를 지원하는지 테스트
            test_chars = subtitle_text[:5] if len(subtitle_text) > 5 else subtitle_text
            try:
                # 테스트 렌더링을 시도해서 폰트가 문자를 지원하는지 확인
                temp_img = Image.new('RGB', (100, 50))
                temp_draw = ImageDraw.Draw(temp_img)
                temp_draw.text((10, 10), test_chars, font=subtitle_font, fill=(255, 255, 255))
                print(f"  ✅ 폰트 문자 지원 확인: '{test_chars}' 렌더링 성공")
                break
            except Exception as font_test_error:
                print(f"  ⚠️  폰트 문자 지원 실패: {font_test_error}")
                subtitle_font = None
                continue
                
        except Exception as e:
            print(f"  ❌ 폰트 로드 실패: {attempt_path} - {e}")
            continue
    
    if subtitle_font is None:
        print(f"  ⚠️  모든 폰트 로드 실패, 기본 폰트 사용")
        subtitle_font = ImageFont.load_default()
    
    # 텍스트를 여러 줄로 분할
    lines = wrap_text_to_lines(subtitle_text, subtitle_font, text_width, draw)
    print(f"  📝 자막 텍스트 분할: {len(lines)}줄")
    
    # 각 줄 높이 계산
    line_heights = []
    total_text_height = 0
    
    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=subtitle_font)
        line_height = bbox[3] - bbox[1]
        line_heights.append(line_height)
        
        if i == 0:
            total_text_height = line_height
        else:
            total_text_height += line_height + line_spacing
    
    # 수직 시작 위치 (상단 정렬)
    start_y = sy1 + margin_y
    
    # 각 줄 렌더링
    current_y = start_y
    
    for i, line in enumerate(lines):
        if not line.strip():
            continue
        
        # 현재 줄의 높이
        line_height = line_heights[i]
        
        # 영역을 벗어나지 않도록 확인
        if current_y + line_height > sy2 - margin_y:
            print(f"  ⚠️  자막 {i+1}번째 줄이 영역을 벗어남, 스킵")
            break
        
        # X 좌표 (왼쪽 정렬)
        text_x = sx1 + margin_x
        text_y = current_y
        
        print(f"  📍 자막 {i+1}번째 줄 렌더링: '{line}' at ({text_x}, {text_y})")
        
        # 외곽선 효과 (검은색)
        for dx in [-2, -1, 0, 1, 2]:
            for dy in [-2, -1, 0, 1, 2]:
                if dx != 0 or dy != 0:
                    draw.text((text_x + dx, text_y + dy), line, font=subtitle_font, fill=(0, 0, 0))
        
        # 메인 텍스트 (흰색)
        draw.text((text_x, text_y), line, font=subtitle_font, fill=(255, 255, 255))
        
        # 다음 줄 위치 계산
        current_y += line_height + line_spacing
    
    # PIL에서 OpenCV로 변환
    frame[:] = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
    print(f"  🎬 자막 렌더링 완료: {len(lines)}줄")


# === [0] 입력 비디오 파일 목록 가져오기 ===
def get_input_videos():
    """입력 폴더의 모든 비디오 파일 목록을 반환"""
    video_files = [f for f in os.listdir(INPUT_DIR) if f.lower().endswith(('.mp4', '.avi', '.mov', '.mkv'))]
    if not video_files:
        raise Exception(f"{INPUT_DIR} 폴더에 비디오 파일이 없습니다.")
    
    # mp4 파일을 우선적으로 정렬 (Whisper API 호환성)
    video_files.sort(key=lambda x: (not x.lower().endswith('.mp4'), x.lower()))
    
    print(f"📁 발견된 비디오 파일: {len(video_files)}개")
    for i, file in enumerate(video_files, 1):
        print(f"   {i}. {file}")
    
    return [os.path.join(INPUT_DIR, f) for f in video_files]

# === [0-1] 단일 비디오 선택 (기존 호환성) ===
def select_input_video():
    """단일 비디오 선택 (기존 함수 호환성 유지)"""
    video_paths = get_input_videos()
    selected_file = os.path.basename(video_paths[0])
    print(f"🎯 자동 선택: {selected_file}")
    return video_paths[0]


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


# === [2] 타이틀 영역 GUI 선택 ===
def select_title_region(video_path):
    cap = cv2.VideoCapture(video_path)
    ret, frame = cap.read()
    cap.release()

    if not ret:
        raise Exception("영상 첫 프레임을 불러올 수 없습니다.")

    print("🎯 1단계: 타이틀 영역을 선택해주세요")
    print("   - 영상 상단의 제목/타이틀이 있는 영역을 드래그하세요")
    print("   - 드래그 완료 후 Enter 또는 Space를 누르세요")
    
    roi = cv2.selectROI("1단계: 타이틀 영역 선택 (제목/타이틀 영역을 드래그)", frame, showCrosshair=True)
    cv2.destroyAllWindows()
    x, y, w, h = roi
    return (x, y, x + w, y + h)

# === [3] 자막 영역 GUI 선택 ===
def select_subtitle_region(video_path):
    cap = cv2.VideoCapture(video_path)
    ret, frame = cap.read()
    cap.release()

    if not ret:
        raise Exception("영상 첫 프레임을 불러올 수 없습니다.")

    print("🎯 2단계: 자막 영역을 선택해주세요")
    print("   - 영상 하단의 자막이 표시되는 영역을 드래그하세요")
    print("   - 드래그 완료 후 Enter 또는 Space를 누르세요")
    
    roi = cv2.selectROI("2단계: 자막 영역 선택 (자막이 표시되는 영역을 드래그)", frame, showCrosshair=True)
    cv2.destroyAllWindows()
    x, y, w, h = roi
    return (x, y, x + w, y + h)


# === [3-1] 배치 처리용 영역 수집 ===
def collect_regions_for_batch(video_paths):
    """모든 비디오에 대해 타이틀/자막 영역을 미리 수집"""
    regions_data = {}
    
    print(f"\n🎯 {len(video_paths)}개 영상의 영역 설정을 진행합니다.")
    print("=" * 60)
    
    for i, video_path in enumerate(video_paths, 1):
        video_name = os.path.basename(video_path)
        print(f"\n[{i}/{len(video_paths)}] {video_name}")
        print("-" * 40)
        
        print("📍 타이틀 영역 선택")
        title_coords = select_title_region(video_path)
        print(f"✅ 타이틀 영역: {title_coords}")
        
        print("📍 자막 영역 선택") 
        subtitle_coords = select_subtitle_region(video_path)
        print(f"✅ 자막 영역: {subtitle_coords}")
        
        regions_data[video_path] = {
            'title_region': title_coords,
            'subtitle_region': subtitle_coords
        }
        
        if i < len(video_paths):
            print(f"\n⏭️  다음 영상으로 이동: {os.path.basename(video_paths[i])}")
        else:
            print(f"\n🎉 모든 영역 설정 완료!")
    
    return regions_data

# === [4] 파일명에서 타이틀 추출 ===
def extract_title_from_filename(video_path):
    """비디오 파일명에서 타이틀 추출"""
    filename = os.path.basename(video_path)
    # 확장자 제거
    title = os.path.splitext(filename)[0]
    print(f"📝 파일명에서 추출된 타이틀: '{title}'")
    return title


# === [5-1] 타이틀 번역 (기존 방식) ===
def translate_title(title_text, target_languages):
    """타이틀을 여러 언어로 번역"""
    translations = {}
    
    print(f"🌍 타이틀 번역 중: '{title_text}'")
    
    for lang in target_languages:
        try:
            translated = translate_title_claude(title_text, lang)
            translations[lang] = translated
            print(f"  ✅ {lang}: '{translated}'")
        except Exception as e:
            print(f"  ❌ {lang} 번역 실패: {e}")
            translations[lang] = title_text  # 실패시 원문 사용
    
    return translations


# === [6] Whisper로 원문 자막 추출 ===
def transcribe_video(video_path, output_dir):
    # Whisper API 지원 형식 확인 및 변환
    supported_formats = ['.flac', '.m4a', '.mp3', '.mp4', '.mpeg', '.mpga', '.oga', '.ogg', '.wav', '.webm']
    file_ext = os.path.splitext(video_path)[1].lower()
    
    # 지원되지 않는 형식인 경우 오디오만 추출해서 사용
    if file_ext not in supported_formats:
        print(f"⚠️  {file_ext} 형식은 Whisper API에서 지원되지 않습니다.")
        print("💡 오디오를 WAV 형식으로 추출하여 처리합니다...")
    
    # 비디오에서 오디오 추출
    print("비디오에서 오디오 추출 중...")
    audio_path = os.path.join(output_dir, "temp_audio.wav")
    
    # OpenCV를 사용해서 오디오 추출 시도
    try:
        import subprocess
        # 시스템에 ffmpeg가 있는지 확인
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        
        # ffmpeg로 오디오 추출
        result = subprocess.run([
            'ffmpeg', '-i', video_path, '-vn', '-acodec', 'pcm_s16le', 
            '-ar', '16000', '-ac', '1', audio_path, '-y'
        ], capture_output=True, text=True, timeout=300)
        
        if result.returncode != 0:
            raise Exception("ffmpeg 오디오 추출 실패")
        else:
            print("✅ 오디오 추출 완료!")
            
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ ffmpeg를 찾을 수 없습니다.")
        
        # 지원되는 형식이면 원본 파일 직접 사용
        if file_ext in supported_formats:
            print("💡 원본 파일을 직접 사용합니다...")
            audio_path = video_path
        else:
            # 지원되지 않는 형식이면 사용자에게 안내
            raise Exception(f"""
❌ {file_ext} 형식은 Whisper API에서 지원되지 않습니다.

해결 방법:
1. 비디오를 mp4 형식으로 변환해서 다시 업로드하거나
2. 시스템에 ffmpeg를 설치해주세요:
   - macOS: brew install ffmpeg
   - Windows: https://ffmpeg.org/download.html
   
지원되는 형식: {', '.join(supported_formats)}
            """)
            
    except Exception as e:
        print(f"❌ 오디오 추출 실패: {e}")
        
        # 지원되는 형식이면 원본 파일 직접 사용
        if file_ext in supported_formats:
            print("💡 원본 파일을 직접 사용합니다...")
            audio_path = video_path
        else:
            raise Exception(f"오디오 추출에 실패했고, {file_ext} 형식은 직접 지원되지 않습니다.")
    
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
        
        # 불필요한 크레딧 텍스트 필터링
        filtered_subs = []
        for sub in subs:
            # UpTitle 크레딧이나 기타 불필요한 텍스트 제거
            content = sub.content.strip()
            if any(keyword in content.lower() for keyword in [
                'uptitle', 'http', 'www', '.co.kr', '.com', 
                '자막제작', 'by ', 'subtitle', 'caption'
            ]):
                print(f"🚫 필터링된 크레딧 텍스트: '{content}'")
                continue
            
            # 빈 내용이나 너무 짧은 텍스트 제거
            if len(content) < 2:
                continue
                
            filtered_subs.append(sub)
        
        # 필터링된 자막으로 SRT 파일 다시 생성
        filtered_transcript = srt.compose(filtered_subs)
        with open(srt_path, "w", encoding="utf-8") as f:
            f.write(filtered_transcript)
        
        # 필터링된 텍스트 내용 저장
        text_content = "\n".join([sub.content for sub in filtered_subs])
        
        txt_path = os.path.join(output_dir, "original_korean.txt")
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(text_content)
        
        print(f"✅ 자막 추출 완료 ({len(filtered_subs)}개 문장, 크레딧 필터링 적용)")
        
        return srt_path
    except Exception as e:
        # 임시 파일 정리
        if audio_path != video_path and os.path.exists(audio_path):
            os.remove(audio_path)
        raise Exception(f"Whisper API 오류: {str(e)}. 오디오 형식을 확인하거나 파일을 다른 형식으로 변환해주세요.")


# === [4] Claude API 번역 ===
def translate_title_claude(text, target_lang, source_lang="Korean"):
    """타이틀 전용 번역 - 짧고 임팩트 있게"""
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
            {"role": "user", "content": f"Translate this {source_lang} video title to {target_lang}. Make it SHORT, CATCHY and suitable for a video title. Keep it under 6 words if possible. Do NOT transliterate - translate the meaning. Provide only the translated title:\n{text}"}
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

def translate_subtitle_claude(text, target_lang, source_lang="Korean"):
    """자막 전용 번역 - 자연스럽고 구어체로"""
    print(f"  🌍 자막 번역 시작: '{text}' ({source_lang} -> {target_lang})")
    
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
            {"role": "user", "content": f"Translate this {source_lang} video subtitle to natural, conversational {target_lang}. Make it sound like how people actually speak in videos - casual and natural. Do NOT transliterate pronunciation - translate the meaning. Provide only the translated subtitle:\n{text}"}
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
        print(f"자막 번역 요청 오류: {e}")
        return f"[번역 실패: {target_lang}] {text}"

# 하위 호환성을 위한 기존 함수 (자막 번역으로 리다이렉트)
def translate_text_claude(text, target_lang):
    """하위 호환성을 위한 함수 - 자막 번역 사용"""
    return translate_subtitle_claude(text, target_lang)


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


# === [8] 영상 처리 + 타이틀 + 자막 ===
def generate_video(video_path, translations, lang, subtitle_region, output_dir, title_region=None, title_translations=None):
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # 출력 파일명을 "국가명_번역된타이틀.mp4" 형식으로 생성
    if title_translations and lang in title_translations:
        translated_title = title_translations[lang]
        # 파일명에서 사용할 수 없는 문자 제거
        safe_title = "".join(c for c in translated_title if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_title = safe_title.replace(' ', '_')
        filename = f"{lang.lower()}_{safe_title}.mp4"
    else:
        filename = f"{lang}.mp4"
    
    out_path = os.path.join(output_dir, filename)
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

        # 1. 타이틀 영역 처리 (자동 줄바꿈 및 크기 조정)
        if title_region and title_translations and lang in title_translations:
            title_text = title_translations[lang]
            if title_text:
                render_title_text(frame, title_text, title_region, lang)

        # 2. 자막 영역 처리 (자막이 있을 때만 회색 박스 표시)
        sx1, sy1, sx2, sy2 = subtitle_region
        
        # 3. 자막 텍스트 추가 - 텍스트가 있을 때만 박스와 텍스트 모두 표시
        if current_text and sy2 > sy1 and sx2 > sx1:  # 텍스트가 있고 올바른 좌표인지 확인
            # 자막이 있을 때만 회색 박스로 덮기 (RGB: 80, 80, 80 - 어두운 회색)
            cv2.rectangle(frame, (sx1, sy1), (sx2, sy2), (80, 80, 80), -1)
            # 텍스트를 자막 영역 중앙에 배치
            text_x = sx1 + 15
            text_y = sy1 + 60
            
            # 더 큰 폰트 설정
            font_scale = 1.8  # 폰트 크기 증가 (1.2 → 1.8)
            font_thickness = 3  # 텍스트 두께 증가 (2 → 3)
            outline_thickness = 6  # 외곽선 두께 증가 (4 → 6)
            line_spacing = 55  # 줄 간격 증가 (40 → 55)
            
            # 텍스트 길이에 따라 여러 줄로 분할
            max_width = (sx2 - sx1) - 30  # 좌우 여백 줄임
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
                if y_pos < sy2 - 30:  # 자막 영역을 벗어나지 않도록
                    # 더 두꺼운 검은색 외곽선으로 가독성 극대화
                    cv2.putText(frame, line, (text_x, y_pos), cv2.FONT_HERSHEY_DUPLEX, font_scale, (0, 0, 0), outline_thickness)
                    # 흰색 텍스트를 더 두껍게
                    cv2.putText(frame, line, (text_x, y_pos), cv2.FONT_HERSHEY_DUPLEX, font_scale, (255, 255, 255), font_thickness)
        
        # 자막이 없는 구간: 자막 박스를 표시하지 않음 (원본 영상 그대로)

        out.write(frame)
        frame_idx += 1
        pbar.update(1)

    pbar.close()
    out.release()
    cap.release()


# === [9] 배치 처리 메인 함수 ===
def process_single_video(video_path, regions_data, selected_languages, video_index, total_videos):
    """단일 비디오 처리"""
    video_name = os.path.splitext(os.path.basename(video_path))[0]
    output_dir = os.path.join(OUTPUT_BASE_DIR, f"{video_name}_translated")
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"\n📹 [{video_index}/{total_videos}] {os.path.basename(video_path)} 처리 중...")
    print("=" * 60)
    
    regions = regions_data[video_path]
    title_coords = regions['title_region']
    subtitle_coords = regions['subtitle_region']
    
    # 타이틀 추출 및 번역 (파일명 기반)
    print("🏷️  타이틀 추출 및 번역 (파일명 기반)...")
    try:
        # 파일명에서 타이틀 추출
        title_text = extract_title_from_filename(video_path)
        
        # 타이틀 번역
        title_translations = translate_title(title_text, selected_languages)
        
        # 타이틀 번역 결과 저장
        title_file = os.path.join(output_dir, "title_translations.txt")
        with open(title_file, "w", encoding="utf-8") as f:
            f.write(f"원본 타이틀: {title_text}\n\n")
            for lang, translated in title_translations.items():
                f.write(f"{lang}: {translated}\n")
        print("  ✅ 타이틀 번역 완료")
    except Exception as e:
        print(f"  ⚠️  타이틀 처리 실패: {e}")
        title_text = "제목 추출 실패"
        title_translations = None

    # 음성 인식 (자막 추출)
    print("🎙️  음성 인식 (자막 추출)...")
    srt_path = transcribe_video(video_path, output_dir)

    # 자막 번역 (병렬 처리)
    print("🌍 자막 번역 (병렬 처리)...")
    translations_dict = create_translations_parallel(srt_path, selected_languages, output_dir)

    # 최종 영상 생성 (타이틀 + 자막)
    print("🎬 최종 영상 생성...")
    for lang in selected_languages:
        print(f"  🎥 {lang} 영상 생성 중...")
        generate_video(
            video_path=video_path,
            translations=translations_dict[lang], 
            lang=lang, 
            subtitle_region=subtitle_coords, 
            output_dir=output_dir,
            title_region=title_coords,
            title_translations=title_translations
        )

    print(f"✅ [{video_index}/{total_videos}] {os.path.basename(video_path)} 처리 완료!")
    return output_dir

def process_batch_videos():
    """배치 처리 메인 함수"""
    print("🎬 비디오 자동 번역기 v3.0 (배치 처리)")
    print("=" * 60)
    
    # 1단계: 비디오 파일 목록 가져오기
    print("\n[1/4] 비디오 파일 스캔")
    video_paths = get_input_videos()
    
    if len(video_paths) == 1:
        print("📌 단일 파일 모드로 실행합니다.")
        return process_single_mode()
    
    # 2단계: 언어 선택 (모든 영상에 공통 적용)
    print("\n[2/4] 번역 언어 선택 (모든 영상 공통)")
    select_languages_gui()
    print(f"✅ 선택된 언어: {selected_languages}")
    
    # 3단계: 모든 영상의 영역 설정
    print("\n[3/4] 영역 설정 단계")
    regions_data = collect_regions_for_batch(video_paths)
    
    # 4단계: 순차 처리
    print("\n[4/4] 배치 처리 시작")
    print("🚀 모든 준비가 완료되었습니다. 순차 처리를 시작합니다!")
    print("=" * 60)
    
    completed_videos = []
    total_videos = len(video_paths)
    
    for i, video_path in enumerate(video_paths, 1):
        try:
            output_dir = process_single_video(video_path, regions_data, selected_languages, i, total_videos)
            completed_videos.append((video_path, output_dir))
        except Exception as e:
            print(f"❌ {os.path.basename(video_path)} 처리 실패: {e}")
            continue
    
    # 최종 결과 요약
    print("\n" + "=" * 60)
    print("🎉 배치 처리 완료!")
    print(f"📊 처리 결과: {len(completed_videos)}/{total_videos}개 성공")
    print("\n📁 생성된 폴더:")
    for video_path, output_dir in completed_videos:
        video_name = os.path.basename(video_path)
        print(f"   • {video_name} → {output_dir}")

def process_single_mode():
    """단일 파일 처리 모드 (기존 방식)"""
    print("\n📌 단일 파일 모드")
    input_video_path = select_input_video()
    video_name = os.path.splitext(os.path.basename(input_video_path))[0]
    output_dir = os.path.join(OUTPUT_BASE_DIR, f"{video_name}_translated")
    os.makedirs(output_dir, exist_ok=True)
    print(f"✅ 선택된 비디오: {input_video_path}")

    print("\n[2/8] 번역 언어 선택")
    select_languages_gui()
    print(f"✅ 선택된 언어: {selected_languages}")

    print("\n[3/8] 타이틀 영역 선택")
    title_coords = select_title_region(input_video_path)
    print(f"✅ 타이틀 영역: {title_coords}")

    print("\n[4/8] 자막 영역 선택")
    subtitle_coords = select_subtitle_region(input_video_path)
    print(f"✅ 자막 영역: {subtitle_coords}")

    print("\n[5/8] 타이틀 추출 및 번역 (파일명 기반)")
    try:
        # 파일명에서 타이틀 추출
        title_text = extract_title_from_filename(input_video_path)
        
        # 타이틀 번역
        title_translations = translate_title(title_text, selected_languages)
        
        title_file = os.path.join(output_dir, "title_translations.txt")
        with open(title_file, "w", encoding="utf-8") as f:
            f.write(f"원본 타이틀: {title_text}\n\n")
            for lang, translated in title_translations.items():
                f.write(f"{lang}: {translated}\n")
        print("✅ 타이틀 번역 완료")
    except Exception as e:
        print(f"⚠️  타이틀 처리 실패: {e}")
        title_text = "제목 추출 실패"
        title_translations = None

    print("\n[6/8] 음성 인식 (자막 추출)")
    srt_path = transcribe_video(input_video_path, output_dir)

    print("\n[7/8] 자막 번역 (병렬 처리)")
    translations_dict = create_translations_parallel(srt_path, selected_languages, output_dir)

    print("\n[8/8] 최종 영상 생성 (타이틀 + 자막)")
    for lang in selected_languages:
        print(f"  🎥 {lang} 영상 생성 중...")
        generate_video(
            video_path=input_video_path,
            translations=translations_dict[lang], 
            lang=lang, 
            subtitle_region=subtitle_coords, 
            output_dir=output_dir,
            title_region=title_coords,
            title_translations=title_translations
        )

    print(f"\n🎉 완료! 모든 영상이 {output_dir} 폴더에 저장되었습니다!")
    print("📁 생성된 파일:")
    print(f"   • 원본 자막: original_korean.srt/.txt")
    print(f"   • 타이틀 번역: title_translations.txt")
    print(f"   • 번역 텍스트: translated_[언어].txt")
    print(f"   • 최종 영상: [언어소문자]_[번역된타이틀].mp4")

# === 실행 ===
if __name__ == "__main__":
    process_batch_videos()