# === API 키 설정 ===
import os

# 환경변수에서 API 키를 먼저 확인, 없으면 로컬 파일 확인
CLAUDE_API_KEY = os.getenv('ANTHROPIC_API_KEY')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

if CLAUDE_API_KEY and OPENAI_API_KEY:
    print("✅ 환경변수에서 API 키를 성공적으로 불러왔습니다.")
else:
    try:
        from config_local import CLAUDE_API_KEY as LOCAL_CLAUDE, OPENAI_API_KEY as LOCAL_OPENAI
        CLAUDE_API_KEY = CLAUDE_API_KEY or LOCAL_CLAUDE
        OPENAI_API_KEY = OPENAI_API_KEY or LOCAL_OPENAI
        print("✅ 로컬 API 키 파일을 성공적으로 불러왔습니다.")
    except ImportError:
        # 둘 다 없는 경우 기본값
        CLAUDE_API_KEY = CLAUDE_API_KEY or "YOUR_CLAUDE_API_KEY_HERE"
        OPENAI_API_KEY = OPENAI_API_KEY or "YOUR_OPENAI_API_KEY_HERE"
        print("⚠️  API 키가 설정되지 않았습니다. 환경변수나 config_local.py를 설정해주세요.")

# === 기본 설정 ===
INPUT_DIR = "input_videos"
OUTPUT_BASE_DIR = "outputs"

# === 다국어 폰트 설정 ===
import os

# 프로젝트 루트 디렉토리
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
FONTS_DIR = os.path.join(PROJECT_ROOT, "fonts")

def get_font_path(language, style="bold"):
    """언어별 폰트 경로 반환"""
    lang_dir = os.path.join(FONTS_DIR, language.lower())
    
    if os.path.exists(lang_dir):
        # Bold 폰트 우선 찾기
        for file in os.listdir(lang_dir):
            if file.endswith(('.ttf', '.otf')):
                if style.lower() == "bold" and ("Bold" in file or "bold" in file):
                    return os.path.join(lang_dir, file)
                elif style.lower() == "regular" and ("Regular" in file or "regular" in file):
                    return os.path.join(lang_dir, file)
        
        # 스타일 관계없이 첫 번째 폰트 반환
        for file in os.listdir(lang_dir):
            if file.endswith(('.ttf', '.otf')):
                return os.path.join(lang_dir, file)
    
    # 기본 폰트 반환
    return "/Library/Fonts/Arial Unicode.ttf"

# 타이틀용 폰트 (굵고 임팩트 있는 폰트)
TITLE_FONTS = {
    "korean": os.path.join(PROJECT_ROOT, "Fonts/Korean/DoHyeon-Regular.ttf"),
    "english": os.path.join(PROJECT_ROOT, "Fonts/English/BebasNeue-Regular.ttf"), 
    "spanish": os.path.join(PROJECT_ROOT, "Fonts/Spanish/Anton-Regular.ttf"),
    "german": os.path.join(PROJECT_ROOT, "Fonts/German/Anton-Regular.ttf"),
    "vietnamese": os.path.join(PROJECT_ROOT, "Fonts/Vietnamese/BeVietnamPro-ExtraBold.ttf"),
    "thai": os.path.join(PROJECT_ROOT, "Fonts/Thai/Kanit-ExtraBold.ttf"),
    "japanese": os.path.join(PROJECT_ROOT, "Fonts/Japanese/MPLUS1p-ExtraBold.ttf"),
    "chinese": os.path.join(PROJECT_ROOT, "Fonts/Chinese/ZCOOLKuaiLe-Regular.ttf"),
    "french": os.path.join(PROJECT_ROOT, "Fonts/French/Anton-Regular.ttf"),
    "default": "/Library/Fonts/Arial Unicode.ttf"
}

# 자막용 폰트 (읽기 쉽고 깔끔한 폰트)
SUBTITLE_FONTS = {
    "korean": os.path.join(PROJECT_ROOT, "SubtitleFonts/Korean/DoHyeon-Regular.ttf"),
    "english": os.path.join(PROJECT_ROOT, "SubtitleFonts/Western/NotoSans-Regular.ttf"),
    "spanish": os.path.join(PROJECT_ROOT, "SubtitleFonts/Western/NotoSans-Regular.ttf"),
    "german": os.path.join(PROJECT_ROOT, "SubtitleFonts/Western/NotoSans-Regular.ttf"),
    "french": os.path.join(PROJECT_ROOT, "SubtitleFonts/Western/NotoSans-Regular.ttf"),
    "vietnamese": os.path.join(PROJECT_ROOT, "SubtitleFonts/Vietnamese/BeVietnamPro-Regular.ttf"),
    "thai": os.path.join(PROJECT_ROOT, "SubtitleFonts/Thai/Kanit-Regular.ttf"),
    "japanese": os.path.join(PROJECT_ROOT, "SubtitleFonts/Japanese/MPLUS1p-Regular.ttf"),
    "chinese": os.path.join(PROJECT_ROOT, "SubtitleFonts/Chinese/ZCOOLKuaiLe-Regular.ttf"),
    "default": "/Library/Fonts/Arial Unicode.ttf"
}

# 하위 호환성을 위한 기존 FONTS 변수 (타이틀 폰트로 매핑)
FONTS = TITLE_FONTS

# 기본 폰트 경로 (하위 호환성)
FONT_PATH = FONTS["default"]

# === 번역 언어 목록 ===
AVAILABLE_LANGUAGES = ["Korean", "English", "Spanish", "Vietnamese", "Japanese", "Chinese", "French", "German", "Thai"]