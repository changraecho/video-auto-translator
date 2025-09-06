#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Flask, render_template, request, jsonify, send_from_directory, session, redirect
from werkzeug.utils import secure_filename
import os

# ffmpeg 경로를 PATH에 추가 (웹 앱 시작시)
if '/opt/homebrew/bin' not in os.environ.get('PATH', ''):
    os.environ['PATH'] = '/opt/homebrew/bin:' + os.environ.get('PATH', '')
import cv2
import uuid
import json
from datetime import datetime
import threading
import time
import srt

# 기존 모듈 import
from main import (
    transcribe_video, translate_title_claude, translate_subtitle_claude,
    get_title_font_for_language, get_subtitle_font_for_language,
    render_title_text, render_subtitle_text
)
from config import AVAILABLE_LANGUAGES

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this'  # 실제 배포시 변경 필요

# 업로드 크기 제한 설정
app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024 * 1024  # 1GB

# 설정
UPLOAD_FOLDER = 'web_uploads'
PROCESSED_FOLDER = 'web_processed'
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# 폴더 생성
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)
os.makedirs('static/temp', exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_video_thumbnail(video_path, output_path):
    """비디오 첫 프레임을 썸네일로 추출"""
    cap = cv2.VideoCapture(video_path)
    ret, frame = cap.read()
    cap.release()
    
    if ret:
        # 웹에서 표시하기 적절한 크기로 리사이즈
        height, width = frame.shape[:2]
        max_width = 800
        if width > max_width:
            ratio = max_width / width
            new_width = max_width
            new_height = int(height * ratio)
            frame = cv2.resize(frame, (new_width, new_height))
        
        cv2.imwrite(output_path, frame)
        return True
    return False

@app.route('/')
def index():
    """메인 페이지 - 파일 업로드"""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_files():
    """파일 업로드 처리"""
    try:
        print("📤 Upload request received")
        
        if 'files[]' not in request.files:
            print("❌ No files in request")
            return jsonify({'error': '파일이 선택되지 않았습니다.'}), 400
        
        files = request.files.getlist('files[]')
        print(f"📁 Processing {len(files)} files")
        
        uploaded_files = []
        session_id = str(uuid.uuid4())
        session['session_id'] = session_id
        
        session_folder = os.path.join(UPLOAD_FOLDER, session_id)
        os.makedirs(session_folder, exist_ok=True)
        print(f"📂 Created session folder: {session_folder}")
        
        for i, file in enumerate(files):
            if file and file.filename and allowed_file(file.filename):
                print(f"📄 Processing file {i+1}: {file.filename}")
                filename = secure_filename(file.filename)
                
                # 중복 파일명 방지
                base, ext = os.path.splitext(filename)
                counter = 1
                while os.path.exists(os.path.join(session_folder, filename)):
                    filename = f"{base}_{counter}{ext}"
                    counter += 1
                
                filepath = os.path.join(session_folder, filename)
                file.save(filepath)
                print(f"💾 Saved file: {filepath}")
                
                # 파일 정보 저장
                file_info = {
                    'filename': filename,
                    'original_filename': file.filename,
                    'size': os.path.getsize(filepath),
                    'path': filepath
                }
                uploaded_files.append(file_info)
            else:
                print(f"❌ Skipped invalid file: {file.filename if file else 'None'}")
        
        # 세션에 파일 정보 저장
        session['uploaded_files'] = uploaded_files
        print(f"✅ Upload completed. Total files: {len(uploaded_files)}")
        
        response = jsonify({
            'success': True,
            'files': uploaded_files,
            'session_id': session_id
        })
        print("📤 Sending response")
        return response
        
    except Exception as e:
        print(f"❌ Upload error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'업로드 중 오류가 발생했습니다: {str(e)}'}), 500

@app.route('/select_source_language')
def select_source_language():
    """출발 언어 선택 페이지"""
    if 'uploaded_files' not in session:
        return redirect('/')
    
    return render_template('select_source_language.html', 
                         available_languages=AVAILABLE_LANGUAGES,
                         uploaded_files=session['uploaded_files'])

@app.route('/save_source_language', methods=['POST'])
def save_source_language():
    """선택된 출발 언어 저장"""
    data = request.get_json()
    source_language = data.get('source_language')
    
    if not source_language:
        return jsonify({'error': '출발 언어를 선택해주세요.'}), 400
    
    session['source_language'] = source_language
    print(f"🌐 Source language set to: {source_language}")
    return jsonify({'success': True})

@app.route('/select_target_languages')
def select_target_languages():
    """타겟 언어 선택 페이지"""
    if 'uploaded_files' not in session or 'source_language' not in session:
        return redirect('/')
    
    source_language = session['source_language']
    
    # 출발 언어 제외한 나머지 언어들
    available_target_languages = [lang for lang in AVAILABLE_LANGUAGES 
                                if lang.lower() != source_language.lower()]
    
    return render_template('select_target_languages.html', 
                         available_target_languages=available_target_languages,
                         source_language=source_language,
                         uploaded_files=session['uploaded_files'])

@app.route('/save_target_languages', methods=['POST'])
def save_target_languages():
    """선택된 타겟 언어 저장"""
    data = request.get_json()
    target_languages = data.get('target_languages', [])
    
    if not target_languages:
        return jsonify({'error': '최소 하나의 타겟 언어를 선택해주세요.'}), 400
    
    session['target_languages'] = target_languages
    # 하위 호환성을 위해 기존 키도 유지
    session['selected_languages'] = target_languages
    print(f"🎯 Target languages set to: {target_languages}")
    return jsonify({'success': True})

# 하위 호환성을 위한 기존 라우트 유지
@app.route('/select_languages')
def select_languages():
    """언어 선택 페이지 (하위 호환성)"""
    return redirect('/select_source_language')

@app.route('/save_languages', methods=['POST'])
def save_languages():
    """선택된 언어 저장"""
    data = request.get_json()
    selected_languages = data.get('languages', [])
    
    if not selected_languages:
        return jsonify({'error': '최소 하나의 언어를 선택해주세요.'}), 400
    
    session['selected_languages'] = selected_languages
    return jsonify({'success': True})

@app.route('/video_preview/<int:video_index>')
def video_preview(video_index):
    """비디오 파일을 스트리밍으로 제공"""
    if 'session_id' not in session:
        return redirect('/')
    
    session_id = session['session_id']
    uploaded_files = session.get('uploaded_files', [])
    
    if video_index >= len(uploaded_files):
        return jsonify({'error': '잘못된 비디오 인덱스입니다.'}), 404
    
    video_file = uploaded_files[video_index]
    video_path = video_file['path']
    
    if not os.path.exists(video_path):
        return jsonify({'error': '비디오 파일을 찾을 수 없습니다.'}), 404
    
    return send_from_directory(os.path.dirname(video_path), os.path.basename(video_path))

@app.route('/setup_video/<int:video_index>')
def setup_video(video_index):
    """개별 비디오 설정 페이지"""
    required_keys = ['uploaded_files', 'selected_languages', 'source_language']
    if not all(key in session for key in required_keys):
        return redirect('/')
    
    uploaded_files = session['uploaded_files']
    if video_index >= len(uploaded_files):
        return redirect('/')
    
    current_file = uploaded_files[video_index]
    
    # 비디오 썸네일 생성
    thumbnail_filename = f"thumb_{video_index}_{session['session_id']}.jpg"
    thumbnail_path = os.path.join('static/temp', thumbnail_filename)
    
    if not os.path.exists(thumbnail_path):
        get_video_thumbnail(current_file['path'], thumbnail_path)
    
    return render_template('setup_video.html',
                         current_file=current_file,
                         video_index=video_index,
                         total_videos=len(uploaded_files),
                         thumbnail_url=f'/static/temp/{thumbnail_filename}',
                         selected_languages=session['selected_languages'],
                         source_language=session['source_language'])

@app.route('/extract_audio', methods=['POST'])
def extract_audio():
    """음성에서 텍스트 추출"""
    try:
        print("🎤 Audio extraction request received")
        
        data = request.get_json()
        video_index = data.get('video_index')
        print(f"📍 Video index: {video_index}")
        
        if 'uploaded_files' not in session:
            print("❌ No uploaded files in session")
            return jsonify({'error': '세션이 만료되었습니다.'}), 400
        
        uploaded_files = session['uploaded_files']
        if video_index >= len(uploaded_files):
            print(f"❌ Invalid video index: {video_index} >= {len(uploaded_files)}")
            return jsonify({'error': '잘못된 비디오 인덱스입니다.'}), 400
        
        video_file = uploaded_files[video_index]
        print(f"🎥 Processing video: {video_file['original_filename']}")
        print(f"📁 Video path: {video_file['path']}")
        
        # 파일 존재 확인
        if not os.path.exists(video_file['path']):
            print(f"❌ Video file not found: {video_file['path']}")
            return jsonify({'error': '비디오 파일을 찾을 수 없습니다.'}), 400
        
        # 임시 출력 폴더
        temp_output = os.path.join('static/temp', session['session_id'])
        os.makedirs(temp_output, exist_ok=True)
        print(f"📂 Temp output folder: {temp_output}")
        
        # Whisper가 설치되어 있는지 확인
        try:
            print("🔍 Checking Whisper availability...")
            import whisper
            print("✅ Whisper module found")
        except ImportError:
            print("❌ Whisper module not found")
            return jsonify({'error': 'Whisper가 설치되어 있지 않습니다. pip install openai-whisper로 설치해주세요.'}), 500
        
        # 실제 Whisper 또는 더미 텍스트 선택
        use_real_whisper = os.getenv('USE_REAL_WHISPER', 'true').lower() == 'true'  # 기본값을 true로 변경
        
        if use_real_whisper:
            print("🚀 Using real Whisper transcription...")
            try:
                from simple_whisper import extract_audio_with_whisper, get_text_from_srt
                
                # 실제 Whisper 처리
                srt_path = extract_audio_with_whisper(video_file['path'], temp_output, model_size='base')
                # Claude API로 텍스트 개선
                from config import CLAUDE_API_KEY
                extracted_text = get_text_from_srt(srt_path, improve_with_claude=True, claude_api_key=CLAUDE_API_KEY)
                
                print(f"✅ Real transcription completed: {len(extracted_text)} characters")
                
            except Exception as whisper_error:
                print(f"❌ Whisper failed: {whisper_error}")
                # Whisper 실패 시 더미 텍스트로 fallback
                use_real_whisper = False
        
        if not use_real_whisper:
            print("⚡ Using dummy transcription for testing...")
            
            source_lang = session.get('source_language', 'korean')
            
            # 언어별 더미 텍스트
            dummy_texts = {
                'korean': f"""안녕하세요. 이것은 테스트용 더미 자막입니다.

{video_file['original_filename']} 파일에서 추출된 내용처럼 보이게 하기 위한 예시 텍스트입니다.

실제 Whisper 처리를 원하시면 환경변수를 설정해주세요:
export USE_REAL_WHISPER=true

여러 줄로 구성되어 있어서
사용자가 편집할 수 있습니다.

이 텍스트를 수정하고 저장하시면 번역 과정에서 사용됩니다.""",
                
                'english': f"""Hello everyone. This is a test dummy subtitle.

This is sample text to make it look like content extracted from {video_file['original_filename']}.

If you want real Whisper processing, please set the environment variable:
export USE_REAL_WHISPER=true

It consists of multiple lines
so users can edit it.

If you modify and save this text, it will be used in the translation process.""",
                
                'japanese': f"""こんにちは。これはテスト用のダミー字幕です。

これは{video_file['original_filename']}から抽出された内容のように見せるためのサンプルテキストです。

実際のWhisper処理をご希望の場合は、環境変数を設定してください：
export USE_REAL_WHISPER=true

複数行で構成されているので
ユーザーが編集できます。

このテキストを修正して保存すると、翻訳プロセスで使用されます。""",

                'chinese': f"""大家好。这是测试用的虚拟字幕。

这是为了让它看起来像从{video_file['original_filename']}中提取的内容而制作的示例文本。

如果您想要真正的Whisper处理，请设置环境变量：
export USE_REAL_WHISPER=true

由多行组成
用户可以编辑。

如果您修改并保存此文本，它将在翻译过程中使用。""",

                'spanish': f"""Hola a todos. Este es un subtítulo ficticio de prueba.

Este es un texto de ejemplo para que parezca contenido extraído de {video_file['original_filename']}.

Si desea el procesamiento real de Whisper, configure la variable de entorno:
export USE_REAL_WHISPER=true

Consiste en múltiples líneas
para que los usuarios puedan editarlo.

Si modifica y guarda este texto, se usará en el proceso de traducción.""",

                'french': f"""Bonjour tout le monde. Ceci est un sous-titre factice de test.

Ceci est un exemple de texte pour faire paraître le contenu extrait de {video_file['original_filename']}.

Si vous voulez un vrai traitement Whisper, veuillez définir la variable d'environnement :
export USE_REAL_WHISPER=true

Il se compose de plusieurs lignes
pour que les utilisateurs puissent l'éditer.

Si vous modifiez et enregistrez ce texte, il sera utilisé dans le processus de traduction.""",

                'german': f"""Hallo zusammen. Dies ist ein Test-Dummy-Untertitel.

Dies ist ein Beispieltext, um es wie aus {video_file['original_filename']} extrahierten Inhalt aussehen zu lassen.

Wenn Sie echte Whisper-Verarbeitung möchten, setzen Sie bitte die Umgebungsvariable:
export USE_REAL_WHISPER=true

Es besteht aus mehreren Zeilen
damit Benutzer es bearbeiten können.

Wenn Sie diesen Text ändern und speichern, wird er im Übersetzungsprozess verwendet.""",

                'vietnamese': f"""Xin chào mọi người. Đây là phụ đề giả để thử nghiệm.

Đây là văn bản mẫu để làm cho nó trông giống như nội dung được trích xuất từ {video_file['original_filename']}.

Nếu bạn muốn xử lý Whisper thực sự, vui lòng đặt biến môi trường:
export USE_REAL_WHISPER=true

Nó bao gồm nhiều dòng
để người dùng có thể chỉnh sửa.

Nếu bạn sửa đổi và lưu văn bản này, nó sẽ được sử dụng trong quá trình dịch.""",

                'thai': f"""สวัสดีทุกคน นี่เป็นคำบรรยายจำลองสำหรับทดสอบ

นี่คือข้อความตัวอย่างเพื่อให้ดูเหมือนเนื้อหาที่แยกออกมาจาก {video_file['original_filename']}

หากคุณต้องการการประมวลผล Whisper จริง โปรดตั้งค่าตัวแปรสภาพแวดล้อม:
export USE_REAL_WHISPER=true

ประกอบด้วยหลายบรรทัด
เพื่อให้ผู้ใช้สามารถแก้ไขได้

หากคุณแก้ไขและบันทึกข้อความนี้ มันจะถูกใช้ในกระบวนการแปล"""
            }
            
            extracted_text = dummy_texts.get(source_lang, dummy_texts['english'])
            print(f"✅ Dummy text ({source_lang}) length: {len(extracted_text)} characters")
        
        # TODO: 나중에 실제 Whisper 처리로 교체
        # transcribe_video 함수 확인
        # try:
        #     print("🔍 Checking transcribe_video function...")
        #     from main import transcribe_video
        #     print("✅ transcribe_video function imported")
        # except ImportError as e:
        #     print(f"❌ Failed to import transcribe_video: {e}")
        #     return jsonify({'error': f'transcribe_video 함수를 가져올 수 없습니다: {str(e)}'}), 500
        # 
        # print("🚀 Starting Whisper transcription...")
        # # Whisper로 음성 추출
        # srt_path = transcribe_video(video_file['path'], temp_output)
        # print(f"📄 SRT file created: {srt_path}")
        # 
        # # SRT 파일 존재 확인
        # if not os.path.exists(srt_path):
        #     print(f"❌ SRT file not created: {srt_path}")
        #     return jsonify({'error': 'SRT 파일이 생성되지 않았습니다.'}), 500
        # 
        # # SRT 파일에서 텍스트 추출
        # print("📝 Parsing SRT file...")
        # with open(srt_path, 'r', encoding='utf-8') as f:
        #     srt_content = f.read()
        #     print(f"📊 SRT content length: {len(srt_content)} characters")
        #     subtitles = list(srt.parse(srt_content))
        # 
        # print(f"🎯 Found {len(subtitles)} subtitle segments")
        # 
        # # 자막 텍스트만 추출
        # extracted_text = '\n'.join([sub.content for sub in subtitles])
        # print(f"✅ Extracted text length: {len(extracted_text)} characters")
        
        return jsonify({
            'success': True,
            'extracted_text': extracted_text,
            'srt_path': 'dummy_path.srt'  # 테스트용
        })
        
    except Exception as e:
        print(f"❌ Audio extraction error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'음성 추출 실패: {str(e)}'}), 500

@app.route('/save_video_settings', methods=['POST'])
def save_video_settings():
    """비디오 설정 저장"""
    data = request.get_json()
    video_index = data.get('video_index')
    
    # 세션에 설정 저장
    if 'video_settings' not in session:
        session['video_settings'] = {}
    
    session['video_settings'][str(video_index)] = {
        'title_region': data.get('title_region'),
        'subtitle_region': data.get('subtitle_region'), 
        'korean_title': data.get('korean_title'),
        'korean_subtitles': data.get('korean_subtitles'),
        'timestamp': datetime.now().isoformat()
    }
    
    return jsonify({'success': True})

@app.route('/process_videos')
def process_videos():
    """비디오 처리 시작 페이지"""
    if not all(key in session for key in ['uploaded_files', 'selected_languages', 'video_settings']):
        return redirect('/')
    
    return render_template('process_videos.html',
                         uploaded_files=session['uploaded_files'],
                         selected_languages=session['selected_languages'])

@app.route('/start_processing', methods=['POST'])
def start_processing():
    """비디오 처리 시작"""
    if not all(key in session for key in ['uploaded_files', 'selected_languages', 'video_settings']):
        return jsonify({'error': '필요한 세션 데이터가 없습니다.'}), 400
    
    # 세션 데이터를 파일에 저장 (백그라운드 처리용)
    session_id = session['session_id']
    session_file = os.path.join('static/temp', f'session_{session_id}.json')
    
    session_data = {
        'uploaded_files': session.get('uploaded_files', []),
        'selected_languages': session.get('selected_languages', []),
        'video_settings': session.get('video_settings', {}),
        'source_language': session.get('source_language', 'korean')
    }
    
    with open(session_file, 'w', encoding='utf-8') as f:
        json.dump(session_data, f, ensure_ascii=False, indent=2)
    
    def process_in_background():
        try:
            process_all_videos(session_id)
        except Exception as e:
            print(f"처리 중 오류: {e}")
    
    thread = threading.Thread(target=process_in_background)
    thread.daemon = True
    thread.start()
    
    return jsonify({'success': True, 'message': '처리가 시작되었습니다.'})

def parse_srt_timing(srt_path):
    """SRT 파일에서 타이밍 정보 추출"""
    try:
        with open(srt_path, 'r', encoding='utf-8') as f:
            subtitles = list(srt.parse(f.read()))
        
        timing_data = []
        for sub in subtitles:
            start_seconds = sub.start.total_seconds()
            end_seconds = sub.end.total_seconds()
            timing_data.append((start_seconds, end_seconds, sub.content))
        
        print(f"📊 SRT 타이밍 추출: {len(timing_data)}개 구간")
        return timing_data
    except Exception as e:
        print(f"⚠️ SRT 타이밍 추출 실패: {e}")
        return []

def create_timed_subtitle_data(original_srt_path, translated_text):
    """원본 SRT 타이밍을 사용하여 번역된 텍스트를 시간에 맞게 분할"""
    timing_data = parse_srt_timing(original_srt_path)
    
    if not timing_data:
        print("⚠️ 타이밍 데이터가 없어 기본 타이밍 사용")
        # 폴백: 간단한 타이밍 생성
        lines = [line.strip() for line in translated_text.split('\n') if line.strip()]
        subtitle_data = []
        for i, line in enumerate(lines[:10]):
            start_time = i * 2.5
            end_time = start_time + 2.5
            subtitle_data.append((start_time, end_time, line))
        return subtitle_data
    
    # 번역된 텍스트를 줄 단위로 분할
    translated_lines = [line.strip() for line in translated_text.split('\n') if line.strip()]
    subtitle_data = []
    
    print(f"📝 원본 구간: {len(timing_data)}개, 번역 줄: {len(translated_lines)}개")
    
    # 원본 타이밍 개수와 번역된 줄 수를 맞춤
    for i, (start_time, end_time, original_content) in enumerate(timing_data):
        if i < len(translated_lines):
            translated_line = translated_lines[i]
        else:
            # 번역된 줄이 부족한 경우 빈 문자열
            translated_line = ""
        
        if translated_line:  # 빈 줄이 아닌 경우만 추가
            subtitle_data.append((start_time, end_time, translated_line))
    
    print(f"✅ 타이밍 동기화 완료: {len(subtitle_data)}개 구간")
    return subtitle_data

def generate_video_with_overlay(video_path, subtitle_data, output_path, title_text='', title_region=None, subtitle_region=None):
    """자막과 타이틀이 오버레이된 비디오 생성 - 적절한 폰트 사용"""
    import cv2
    from PIL import Image, ImageDraw, ImageFont
    import numpy as np
    
    print(f"🎬 비디오 오버레이 생성: {output_path}")
    print(f"📊 자막 데이터: {len(subtitle_data)}개 구간")
    
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    # 코덱 설정
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (w, h))
    
    # 타이틀 폰트 로드 (더 큰 사이즈)
    try:
        title_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 48)
        subtitle_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 32)
        print("✅ 시스템 폰트 로드 성공")
    except:
        title_font = ImageFont.load_default()
        subtitle_font = ImageFont.load_default()
        print("⚠️ 기본 폰트 사용")
    
    frame_idx = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        current_time = frame_idx / fps
        current_subtitle = ""
        
        # 현재 시간에 해당하는 자막 찾기
        for start_time, end_time, text in subtitle_data:
            if start_time <= current_time <= end_time:
                current_subtitle = text
                break
        
        # PIL 이미지로 변환 (폰트 렌더링을 위해)
        pil_image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(pil_image)
        
        # 타이틀 오버레이 (항상 표시)
        if title_text and title_region:
            tx1, ty1, tx2, ty2 = title_region
            if tx2 > tx1 and ty2 > ty1:
                # 타이틀 배경 박스 (어두운 회색)
                draw.rectangle([tx1, ty1, tx2, ty2], fill=(60, 60, 60))
                
                # 타이틀 텍스트 (중앙 정렬)
                bbox = draw.textbbox((0, 0), title_text, font=title_font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                
                text_x = tx1 + (tx2 - tx1 - text_width) // 2
                text_y = ty1 + (ty2 - ty1 - text_height) // 2
                
                # 외곽선 효과 (검은색)
                for dx in [-2, -1, 0, 1, 2]:
                    for dy in [-2, -1, 0, 1, 2]:
                        if dx != 0 or dy != 0:
                            draw.text((text_x + dx, text_y + dy), title_text, font=title_font, fill=(0, 0, 0))
                
                # 메인 텍스트 (흰색)
                draw.text((text_x, text_y), title_text, font=title_font, fill=(255, 255, 255))
        
        # 자막 오버레이 (자막이 있을 때만)
        if current_subtitle and subtitle_region:
            sx1, sy1, sx2, sy2 = subtitle_region
            if sx2 > sx1 and sy2 > sy1:
                # 자막 배경 박스 (회색)
                draw.rectangle([sx1, sy1, sx2, sy2], fill=(80, 80, 80))
                
                # 자막 텍스트 (왼쪽 정렬, 약간 들여쓰기)
                text_x = sx1 + 15
                text_y = sy1 + 15
                
                # 외곽선 효과 (검은색)
                for dx in [-2, -1, 0, 1, 2]:
                    for dy in [-2, -1, 0, 1, 2]:
                        if dx != 0 or dy != 0:
                            draw.text((text_x + dx, text_y + dy), current_subtitle, font=subtitle_font, fill=(0, 0, 0))
                
                # 메인 텍스트 (흰색)
                draw.text((text_x, text_y), current_subtitle, font=subtitle_font, fill=(255, 255, 255))
        
        # PIL에서 OpenCV로 다시 변환
        frame[:] = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
        
        out.write(frame)
        frame_idx += 1
        
        # 진행 상황 출력 (100프레임마다)
        if frame_idx % 100 == 0:
            print(f"  처리 중... {frame_idx} 프레임")
    
    cap.release()
    out.release()
    print(f"✅ 비디오 생성 완료: {frame_idx} 프레임")

def process_all_videos(session_id):
    """모든 비디오 실제 처리"""
    try:
        progress_file = os.path.join('static/temp', f'progress_{session_id}.json')
        
        # 세션 정보 파일에서 가져오기
        session_file = os.path.join('static/temp', f'session_{session_id}.json')
        
        # 세션 파일에서 정보 로드
        if os.path.exists(session_file):
            with open(session_file, 'r', encoding='utf-8') as f:
                session_data = json.load(f)
            uploaded_files = session_data.get('uploaded_files', [])
            selected_languages = session_data.get('selected_languages', [])
            video_settings = session_data.get('video_settings', {})
            source_language = session_data.get('source_language', 'korean')
        else:
            print(f"❌ 세션 파일을 찾을 수 없습니다: {session_file}")
            return
        
        # 초기 진행상황 설정
        videos_status = []
        for i, file_info in enumerate(uploaded_files):
            video_langs = {}
            for lang in selected_languages:
                video_langs[lang] = 'waiting'  # waiting, processing, completed, error
            
            videos_status.append({
                'filename': file_info['original_filename'],
                'status': 'waiting',
                'progress': 0,
                'current_task': '대기 중...',
                'languages': video_langs
            })
        
        progress_data = {
            'current_step': '처리 시작...',
            'progress': 0,
            'completed_videos': 0,
            'processing_videos': 0,
            'total_videos': len(uploaded_files),
            'status': 'processing',
            'videos': videos_status
        }
        
        # 진행상황 파일에 저장
        with open(progress_file, 'w', encoding='utf-8') as f:
            json.dump(progress_data, f, ensure_ascii=False, indent=2)
        
        print(f"🚀 Starting processing for {len(uploaded_files)} videos")
        
        # 실제 비디오 처리
        for video_idx, file_info in enumerate(uploaded_files):
            print(f"🎥 Processing video {video_idx + 1}: {file_info['original_filename']}")
            
            try:
                # 비디오 상태를 processing으로 업데이트
                progress_data['videos'][video_idx]['status'] = 'processing'
                progress_data['videos'][video_idx]['current_task'] = '음성 추출 중...'
                progress_data['processing_videos'] = 1
                progress_data['current_step'] = f'비디오 {video_idx + 1}/{len(uploaded_files)} 처리 중...'
                
                with open(progress_file, 'w', encoding='utf-8') as f:
                    json.dump(progress_data, f, ensure_ascii=False, indent=2)
                
                # 비디오 설정 가져오기
                video_setting = video_settings.get(str(video_idx), {})
                source_title = video_setting.get('source_title', '')
                source_subtitles = video_setting.get('source_subtitles', '')
                title_region = video_setting.get('title_region')
                subtitle_region = video_setting.get('subtitle_region')
                
                if not source_subtitles:
                    # 음성 추출 (Whisper + Claude 개선)
                    from simple_whisper import extract_audio_with_whisper, get_text_from_srt
                    from config import CLAUDE_API_KEY
                    
                    temp_output = os.path.join('static/temp', session_id)
                    os.makedirs(temp_output, exist_ok=True)
                    
                    srt_path = extract_audio_with_whisper(file_info['path'], temp_output, model_size='base')
                    source_subtitles = get_text_from_srt(srt_path, improve_with_claude=True, claude_api_key=CLAUDE_API_KEY)
                
                # 번역 처리
                from main import translate_title_claude, translate_subtitle_claude
                
                title_translations = {}
                subtitle_translations = {}
                
                # 타이틀 번역
                if source_title:
                    for lang in selected_languages:
                        progress_data['videos'][video_idx]['current_task'] = f'{lang.title()} 타이틀 번역 중...'
                        progress_data['videos'][video_idx]['languages'][lang] = 'processing'
                        
                        with open(progress_file, 'w', encoding='utf-8') as f:
                            json.dump(progress_data, f, ensure_ascii=False, indent=2)
                        
                        title_translations[lang] = translate_title_claude(source_title, lang)
                
                # 자막 번역 
                for lang in selected_languages:
                    progress_data['videos'][video_idx]['current_task'] = f'{lang.title()} 자막 번역 중...'
                    
                    with open(progress_file, 'w', encoding='utf-8') as f:
                        json.dump(progress_data, f, ensure_ascii=False, indent=2)
                    
                    print(f"🌍 자막 번역 시작: {lang}")
                    subtitle_translations[lang] = translate_subtitle_claude(source_subtitles, lang)
                    print(f"✅ 자막 번역 완료: {lang} - {len(subtitle_translations[lang])} 글자")
                
                # 비디오 생성
                output_dir = os.path.join(PROCESSED_FOLDER, session_id)
                os.makedirs(output_dir, exist_ok=True)
                
                for lang in selected_languages:
                    progress_data['videos'][video_idx]['current_task'] = f'{lang.title()} 비디오 생성 중...'
                    
                    with open(progress_file, 'w', encoding='utf-8') as f:
                        json.dump(progress_data, f, ensure_ascii=False, indent=2)
                    
                    try:
                        # 실제 자막 오버레이가 적용된 비디오 생성
                        base_name = os.path.splitext(file_info['original_filename'])[0]
                        output_filename = f"{base_name}_{lang}.mp4"
                        output_path = os.path.join(output_dir, output_filename)
                        
                        print(f"🎬 {lang} 비디오 생성 중... 자막 길이: {len(subtitle_translations.get(lang, ''))}")
                        
                        # 자막 타이밍 데이터 생성 - 원본 SRT 파일의 타이밍 사용
                        subtitle_timing_data = []
                        if source_subtitles and subtitle_translations.get(lang):
                            # 원본 SRT 파일 경로 찾기
                            temp_output = os.path.join('static/temp', session_id)
                            base_name = os.path.splitext(file_info['original_filename'])[0]
                            original_srt_path = os.path.join(temp_output, f"{base_name}_korean.srt")
                            
                            if os.path.exists(original_srt_path):
                                print(f"📍 원본 SRT 파일 발견: {original_srt_path}")
                                subtitle_timing_data = create_timed_subtitle_data(
                                    original_srt_path, 
                                    subtitle_translations[lang]
                                )
                            else:
                                print(f"⚠️ 원본 SRT 파일 없음, 기본 타이밍 사용: {original_srt_path}")
                                # 폴백: 간단한 타이밍 생성 
                                translated_text = subtitle_translations[lang]
                                lines = [line.strip() for line in translated_text.split('\n') if line.strip()]
                                
                                for i, line in enumerate(lines[:10]):  # 최대 10줄 처리
                                    start_time = i * 2.5  # 2.5초씩 간격
                                    end_time = start_time + 2.5
                                    subtitle_timing_data.append((start_time, end_time, line))
                        
                        # Region 데이터를 픽셀 좌표로 변환
                        video_cap = cv2.VideoCapture(file_info['path'])
                        video_width = int(video_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                        video_height = int(video_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                        video_cap.release()
                        
                        title_coords = None
                        subtitle_coords = None
                        
                        if title_region:
                            title_coords = (
                                int(title_region['x'] * video_width),
                                int(title_region['y'] * video_height), 
                                int((title_region['x'] + title_region['width']) * video_width),
                                int((title_region['y'] + title_region['height']) * video_height)
                            )
                        
                        if subtitle_region:
                            subtitle_coords = (
                                int(subtitle_region['x'] * video_width),
                                int(subtitle_region['y'] * video_height),
                                int((subtitle_region['x'] + subtitle_region['width']) * video_width),
                                int((subtitle_region['y'] + subtitle_region['height']) * video_height)
                            )
                        
                        # 실제 비디오 생성 (자막 오버레이 포함)
                        try:
                            generate_video_with_overlay(
                                video_path=file_info['path'],
                                subtitle_data=subtitle_timing_data,
                                output_path=output_path,
                                title_text=title_translations.get(lang, ''),
                                title_region=title_coords,
                                subtitle_region=subtitle_coords
                            )
                            print(f"✅ {lang} 비디오 생성 완료: {output_path}")
                        except Exception as video_error:
                            print(f"⚠️ {lang} 비디오 생성 실패, 원본 복사: {video_error}")
                            import traceback
                            traceback.print_exc()
                            # 비디오 생성 실패 시 원본 복사
                            import shutil
                            shutil.copy2(file_info['path'], output_path)
                        
                        # 번역된 텍스트 파일도 저장
                        txt_path = os.path.join(output_dir, f"{base_name}_{lang}.txt")
                        translated_subtitle = subtitle_translations.get(lang, '번역 실패')
                        print(f"📝 {lang} 번역 저장 중... 길이: {len(translated_subtitle)}")
                        
                        with open(txt_path, 'w', encoding='utf-8') as f:
                            f.write(f"Title: {title_translations.get(lang, source_title)}\n\n")
                            f.write(f"Subtitles:\n{translated_subtitle}")
                            
                        print(f"💾 {lang} 번역 파일 저장됨: {txt_path}")
                        
                        progress_data['videos'][video_idx]['languages'][lang] = 'completed'
                        
                    except Exception as e:
                        print(f"❌ 언어 {lang} 처리 실패: {e}")
                        progress_data['videos'][video_idx]['languages'][lang] = 'error'
                
                # 비디오 완료 처리
                progress_data['videos'][video_idx]['status'] = 'completed'
                progress_data['videos'][video_idx]['current_task'] = '완료됨'
                progress_data['videos'][video_idx]['progress'] = 100
                progress_data['completed_videos'] += 1
                progress_data['processing_videos'] = 0
                
                print(f"✅ 비디오 {video_idx + 1} 처리 완료")
                
            except Exception as e:
                print(f"❌ 비디오 {video_idx + 1} 처리 실패: {e}")
                progress_data['videos'][video_idx]['status'] = 'error'
                progress_data['videos'][video_idx]['current_task'] = f'오류: {str(e)}'
                progress_data['processing_videos'] = 0
        
        # 전체 처리 완료
        progress_data['current_step'] = '모든 비디오 처리 완료'
        progress_data['progress'] = 100
        progress_data['status'] = 'completed'
        
        with open(progress_file, 'w', encoding='utf-8') as f:
            json.dump(progress_data, f, ensure_ascii=False, indent=2)
        
        print("🎉 모든 비디오 처리 완료!")
        
    except Exception as e:
        print(f"❌ 전체 처리 오류: {e}")
        # 오류 상태 저장
        progress_data = {
            'current_step': f'처리 중 오류 발생: {str(e)}',
            'progress': 0,
            'status': 'error',
            'error': str(e)
        }
        
        with open(progress_file, 'w', encoding='utf-8') as f:
            json.dump(progress_data, f, ensure_ascii=False, indent=2)

@app.route('/progress/<session_id>')
def get_progress(session_id):
    """처리 진행상황 조회"""
    progress_file = os.path.join('static/temp', f'progress_{session_id}.json')
    
    try:
        if os.path.exists(progress_file):
            with open(progress_file, 'r', encoding='utf-8') as f:
                progress_data = json.load(f)
        else:
            # 기본 진행상황
            progress_data = {
                'current_step': '준비 중...',
                'progress': 0,
                'completed_videos': 0,
                'total_videos': 0,
                'status': 'waiting'
            }
        
        return jsonify(progress_data)
        
    except Exception as e:
        return jsonify({
            'current_step': '상태 조회 오류',
            'progress': 0,
            'status': 'error',
            'error': str(e)
        })

@app.route('/download/<session_id>/<filename>')
def download_file(session_id, filename):
    """처리된 파일 다운로드"""
    download_folder = os.path.join(PROCESSED_FOLDER, session_id)
    return send_from_directory(download_folder, filename)

@app.route('/download_all')
def download_all():
    """모든 처리된 파일을 ZIP으로 다운로드"""
    if 'session_id' not in session:
        return redirect('/')
    
    session_id = session['session_id']
    download_folder = os.path.join(PROCESSED_FOLDER, session_id)
    
    if not os.path.exists(download_folder):
        # 테스트용 더미 파일 생성
        print(f"📁 Creating test files in: {download_folder}")
        os.makedirs(download_folder, exist_ok=True)
        
        # 업로드된 파일 목록 가져오기
        uploaded_files = session.get('uploaded_files', [])
        selected_languages = session.get('selected_languages', ['english', 'japanese'])
        
        # 더미 번역 파일 생성
        for file_info in uploaded_files:
            base_name = os.path.splitext(file_info['original_filename'])[0]
            
            for lang in selected_languages:
                dummy_filename = f"{base_name}_{lang}.mp4"
                dummy_path = os.path.join(download_folder, dummy_filename)
                
                # 더미 텍스트 파일 생성 (실제로는 번역된 비디오 파일이어야 함)
                with open(dummy_path.replace('.mp4', '.txt'), 'w', encoding='utf-8') as f:
                    f.write(f"""테스트용 번역 결과 파일

원본 파일: {file_info['original_filename']}
번역 언어: {lang}
생성 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

실제 번역 처리가 완료되면 이 파일은 번역된 비디오 파일(.mp4)로 대체됩니다.

이 텍스트 파일은 웹 애플리케이션 테스트 목적으로 생성되었습니다.""")
        
        print(f"✅ Created {len(uploaded_files) * len(selected_languages)} test files")
    
    # ZIP 파일 생성 로직 (실제 구현 필요)
    import zipfile
    import tempfile
    
    temp_zip = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
    
    with zipfile.ZipFile(temp_zip.name, 'w') as zf:
        for root, dirs, files in os.walk(download_folder):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, download_folder)
                zf.write(file_path, arcname)
    
    return send_from_directory(os.path.dirname(temp_zip.name), 
                             os.path.basename(temp_zip.name),
                             as_attachment=True,
                             download_name=f'translated_videos_{session_id}.zip')

@app.route('/download_individual/<int:video_index>/<language>')
def download_individual(video_index, language):
    """개별 비디오 파일 다운로드"""
    if 'session_id' not in session:
        return redirect('/')
    
    session_id = session['session_id']
    
    # 업로드된 파일 정보 가져오기
    uploaded_files = session.get('uploaded_files', [])
    if video_index >= len(uploaded_files):
        return jsonify({'error': '잘못된 비디오 인덱스입니다.'}), 404
    
    original_file = uploaded_files[video_index]
    base_name = os.path.splitext(original_file['original_filename'])[0]
    
    # 처리된 파일 경로
    processed_folder = os.path.join(PROCESSED_FOLDER, session_id)
    translated_filename = f"{base_name}_{language}.mp4"
    file_path = os.path.join(processed_folder, translated_filename)
    
    # 파일이 없으면 테스트용 더미 파일 생성
    if not os.path.exists(file_path):
        os.makedirs(processed_folder, exist_ok=True)
        
        # 더미 텍스트 파일 생성
        dummy_file = file_path.replace('.mp4', '.txt')
        with open(dummy_file, 'w', encoding='utf-8') as f:
            f.write(f"""번역된 비디오 파일: {translated_filename}

원본 파일: {original_file['original_filename']}
번역 언어: {language}
생성 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

실제 운영 시에는 이 파일이 번역된 비디오(.mp4) 파일로 대체됩니다.
현재는 테스트 목적으로 텍스트 파일을 제공합니다.""")
        
        file_path = dummy_file
        translated_filename = translated_filename.replace('.mp4', '.txt')
    
    return send_from_directory(
        processed_folder,
        translated_filename,
        as_attachment=True,
        download_name=translated_filename
    )

@app.route('/download_video_all/<int:video_index>')
def download_video_all(video_index):
    """특정 비디오의 모든 언어 버전을 ZIP으로 다운로드"""
    if 'session_id' not in session:
        return redirect('/')
    
    session_id = session['session_id']
    
    # 업로드된 파일 정보 가져오기
    uploaded_files = session.get('uploaded_files', [])
    if video_index >= len(uploaded_files):
        return jsonify({'error': '잘못된 비디오 인덱스입니다.'}), 404
    
    original_file = uploaded_files[video_index]
    base_name = os.path.splitext(original_file['original_filename'])[0]
    selected_languages = session.get('selected_languages', ['english', 'japanese'])
    
    # 처리된 파일 폴더
    processed_folder = os.path.join(PROCESSED_FOLDER, session_id)
    os.makedirs(processed_folder, exist_ok=True)
    
    # 각 언어별 파일 생성 (테스트용)
    files_to_zip = []
    for lang in selected_languages:
        filename = f"{base_name}_{lang}.txt"
        file_path = os.path.join(processed_folder, filename)
        
        if not os.path.exists(file_path):
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(f"""번역된 비디오: {base_name}_{lang}.mp4

원본 파일: {original_file['original_filename']}
번역 언어: {lang}
생성 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

실제 처리 완료 시 이 파일은 번역된 비디오로 대체됩니다.""")
        
        files_to_zip.append((file_path, filename))
    
    # ZIP 파일 생성
    import zipfile
    import tempfile
    
    temp_zip = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
    
    with zipfile.ZipFile(temp_zip.name, 'w') as zf:
        for file_path, arcname in files_to_zip:
            zf.write(file_path, arcname)
    
    return send_from_directory(
        os.path.dirname(temp_zip.name),
        os.path.basename(temp_zip.name),
        as_attachment=True,
        download_name=f"{base_name}_all_languages.zip"
    )

@app.route('/cancel_processing', methods=['POST'])
def cancel_processing():
    """처리 중단"""
    if 'session_id' not in session:
        return jsonify({'error': '세션이 없습니다.'}), 400
    
    session_id = session['session_id']
    progress_file = os.path.join('static/temp', f'progress_{session_id}.json')
    
    # 취소 상태로 업데이트
    progress_data = {
        'current_step': '사용자에 의해 중단됨',
        'progress': 0,
        'status': 'cancelled'
    }
    
    try:
        with open(progress_file, 'w', encoding='utf-8') as f:
            json.dump(progress_data, f, ensure_ascii=False, indent=2)
        
        return jsonify({'success': True, 'message': '처리가 중단되었습니다.'})
    except Exception as e:
        return jsonify({'error': f'중단 처리 실패: {str(e)}'}), 500

@app.errorhandler(413)
def too_large(e):
    """파일 크기 초과 에러 처리"""
    return jsonify({'error': '파일 크기가 너무 큽니다. 1GB 이하의 파일을 업로드해주세요.'}), 413

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)