# 비디오 자동 번역기

비디오에서 한국어 음성을 추출해 여러 언어로 번역하고, 원본 자막을 블러 처리하여 번역된 자막이 포함된 새 비디오를 생성합니다.

## 실행 방법

### 1. 의존성 설치
```bash
pip install -r requirements.txt
```

### 2. API 키 설정
`config.py` 파일에서 다음 값들을 설정하세요:
```python
CLAUDE_API_KEY = "your_claude_api_key_here"
OPENAI_API_KEY = "your_openai_api_key_here"
```

### 3. 입력 비디오 준비
`input_videos/` 폴더에 처리할 비디오 파일들을 넣으세요.

### 4. 프로그램 실행
```bash
python main.py
```

## 실행 과정

1. **입력 비디오 선택**: `input_videos/` 폴더의 비디오 파일 선택
2. **언어 선택**: GUI에서 번역할 언어들을 선택  
3. **블러 영역 선택**: 원본 자막 영역을 드래그로 선택
4. **음성 인식**: Whisper로 한국어 자막 추출
5. **번역**: 선택한 언어들로 병렬 번역
6. **비디오 생성**: 블러 처리 + 번역 자막이 포함된 비디오 생성

## 출력

`outputs/[비디오이름]_translated/` 폴더에 각 언어별 비디오 파일이 생성됩니다:
- `English.mp4`
- `Spanish.mp4` 
- `Japanese.mp4`
- 등등...

## 필요한 API

- **OpenAI API**: Whisper 음성 인식용
- **Claude API**: 텍스트 번역용