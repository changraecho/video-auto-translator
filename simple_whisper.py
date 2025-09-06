#!/usr/bin/env python3
"""
간단한 Whisper 음성 추출 함수
웹 애플리케이션에서 사용하기 위한 독립적인 모듈
"""

import os
import whisper
import srt
from datetime import timedelta
import ssl
import urllib.request

# SSL 인증서 문제 해결
ssl._create_default_https_context = ssl._create_unverified_context

# ffmpeg 경로를 PATH에 추가 (웹 앱 환경용)
if '/opt/homebrew/bin' not in os.environ.get('PATH', ''):
    os.environ['PATH'] = '/opt/homebrew/bin:' + os.environ.get('PATH', '')

def extract_audio_with_whisper(video_path, output_dir, model_size="base"):
    """
    Whisper를 사용해 비디오에서 음성을 추출하고 SRT 파일로 저장
    
    Args:
        video_path (str): 입력 비디오 파일 경로
        output_dir (str): 출력 디렉토리
        model_size (str): Whisper 모델 크기 ('tiny', 'base', 'small', 'medium', 'large')
    
    Returns:
        str: 생성된 SRT 파일 경로
    """
    print(f"🎤 Starting Whisper transcription with {model_size} model...")
    
    try:
        # Whisper 모델 로드 (처음에는 다운로드 시간이 걸림)
        print(f"📥 Loading Whisper {model_size} model...")
        model = whisper.load_model(model_size)
        
        # 음성 추출
        print(f"🔍 Transcribing: {os.path.basename(video_path)}")
        result = model.transcribe(
            video_path,
            language='ko',  # 한국어로 설정
            verbose=True,
            fp16=False  # CPU 호환성을 위해 False로 설정
        )
    except FileNotFoundError as e:
        if 'ffmpeg' in str(e):
            print("❌ ffmpeg가 설치되어 있지 않습니다.")
            print("💡 해결 방법:")
            print("   1. Homebrew 설치: /bin/bash -c \"$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\"")
            print("   2. ffmpeg 설치: brew install ffmpeg")
            print("   또는 직접 다운로드: https://ffmpeg.org/download.html")
            
            # 더미 결과 반환
            print("⚠️  ffmpeg 없이는 실제 처리할 수 없어 더미 데이터를 반환합니다.")
            base_name = os.path.splitext(os.path.basename(video_path))[0]
            srt_path = os.path.join(output_dir, f"{base_name}_korean.srt")
            
            # 더미 SRT 파일 생성
            dummy_srt_content = """1
00:00:00,000 --> 00:00:05,000
ffmpeg가 설치되지 않아 실제 음성 인식을 할 수 없습니다.

2
00:00:05,000 --> 00:00:10,000
ffmpeg를 설치한 후 다시 시도해주세요.

3
00:00:10,000 --> 00:00:15,000
이것은 테스트용 더미 자막입니다.
"""
            with open(srt_path, 'w', encoding='utf-8') as f:
                f.write(dummy_srt_content)
            
            return srt_path
        else:
            raise e
    
    # SRT 형식으로 변환
    subtitles = []
    for i, segment in enumerate(result['segments']):
        subtitle = srt.Subtitle(
            index=i + 1,
            start=timedelta(seconds=segment['start']),
            end=timedelta(seconds=segment['end']),
            content=segment['text'].strip()
        )
        subtitles.append(subtitle)
    
    # SRT 파일 저장
    base_name = os.path.splitext(os.path.basename(video_path))[0]
    srt_path = os.path.join(output_dir, f"{base_name}_korean.srt")
    
    with open(srt_path, 'w', encoding='utf-8') as f:
        f.write(srt.compose(subtitles))
    
    print(f"✅ SRT file saved: {srt_path}")
    print(f"📊 Total segments: {len(subtitles)}")
    
    return srt_path

def improve_text_with_claude(text, api_key):
    """Claude API를 사용하여 Whisper 텍스트의 오타와 인식 오류를 수정"""
    import requests
    
    print("🧠 Claude API로 텍스트 정확도 개선 중...")
    
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    
    prompt = f"""다음은 Whisper AI가 한국어 음성을 인식한 결과입니다. 문맥상 어색하거나 잘못 인식된 단어들을 자연스럽게 수정해주세요.

원본 텍스트:
{text}

수정 가이드라인:
1. 문맥에 맞지 않는 단어를 자연스러운 한국어로 수정
2. 음성인식 특유의 오타 수정 (예: "그�nen" → "그는", "불러떨어졌죠" → "굴러떨어졌죠", "두내" → "두뇌")
3. 전체적인 문맥과 흐름을 자연스럽게 유지
4. 원본의 의미와 뉘앙스를 최대한 보존
5. 수정이 불필요한 부분은 그대로 유지

수정된 텍스트만 출력해주세요:"""
    
    payload = {
        "model": "claude-3-haiku-20240307",
        "max_tokens": 2000,
        "messages": [{"role": "user", "content": prompt}]
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            if "content" in data and len(data["content"]) > 0:
                improved_text = data["content"][0]["text"].strip()
                print("✅ Claude API로 텍스트 개선 완료")
                print(f"원본 길이: {len(text)} → 수정 길이: {len(improved_text)}")
                return improved_text
            else:
                print("⚠️  Claude API 응답 구조 오류, 원본 텍스트 반환")
                return text
        else:
            print(f"⚠️  Claude API 오류 (status: {response.status_code}), 원본 텍스트 반환")
            if response.status_code == 429:
                print("   → API 호출 한도 초과")
            elif response.status_code == 401:
                print("   → API 키 인증 오류")
            return text
            
    except requests.exceptions.Timeout:
        print("⚠️  Claude API 타임아웃, 원본 텍스트 반환")
        return text
    except Exception as e:
        print(f"⚠️  Claude API 호출 실패: {e}, 원본 텍스트 반환")
        return text

def get_text_from_srt(srt_path, improve_with_claude=True, claude_api_key=None):
    """SRT 파일에서 텍스트만 추출하고 선택적으로 Claude로 개선"""
    try:
        with open(srt_path, 'r', encoding='utf-8') as f:
            subtitles = list(srt.parse(f.read()))
        
        text_lines = [sub.content for sub in subtitles]
        original_text = '\n'.join(text_lines)
        
        # Claude API로 텍스트 개선 (옵션)
        if improve_with_claude and claude_api_key:
            improved_text = improve_text_with_claude(original_text, claude_api_key)
            return improved_text
        else:
            return original_text
        
    except Exception as e:
        print(f"❌ Error reading SRT file: {e}")
        return ""

if __name__ == "__main__":
    # 테스트용
    import sys
    if len(sys.argv) < 2:
        print("Usage: python simple_whisper.py <video_file>")
        sys.exit(1)
    
    video_file = sys.argv[1]
    output_dir = os.path.dirname(video_file) or '.'
    
    srt_file = extract_audio_with_whisper(video_file, output_dir)
    text = get_text_from_srt(srt_file)
    
    print("\n" + "="*50)
    print("추출된 텍스트:")
    print("="*50)
    print(text)