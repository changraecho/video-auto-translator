# Video Auto Translator - Web Application

A Flask-based web application that automatically translates Korean videos into multiple languages using AI.

## Features

- **Drag & Drop Upload**: Easy file upload with support for MP4, AVI, MOV, MKV formats
- **Multi-language Support**: Translate to English, Spanish, Japanese, Chinese, French, German, Vietnamese, Thai
- **Interactive Setup**: Visual region selection for titles and subtitles
- **AI-powered Processing**: Uses Whisper for audio extraction and Claude for translation
- **Real-time Progress**: Live progress tracking during processing
- **Batch Processing**: Handle multiple videos simultaneously
- **Professional UI**: Modern, responsive design with step-by-step workflow

## Installation

1. Install required dependencies:
```bash
pip install flask opencv-python pillow anthropic srt
```

2. Set up environment variables:
```bash
export ANTHROPIC_API_KEY="your_anthropic_api_key"
```

3. Run the application:
```bash
python app.py
```

4. Open your browser to `http://localhost:5000`

## Workflow

### Step 1: Upload Videos
- Drag and drop video files or click to browse
- Supports multiple files up to 1GB each
- Only Korean video content is supported as source

### Step 2: Select Languages  
- Choose target languages for translation
- Multiple languages can be selected
- Each language uses optimized fonts for best rendering

### Step 3: Setup Videos
For each video:
- **Left Panel**: Video thumbnail with draggable region selection
  - Set title region (red box) for video titles
  - Set subtitle region (blue box) for dialogue subtitles
  - Drag and resize regions as needed

- **Right Panel**: Content input
  - Enter Korean title for the video
  - Extract Korean dialogue using Whisper AI
  - Edit extracted text as needed

### Step 4: Processing
- Real-time progress tracking for all videos
- Individual video status monitoring
- Language-specific processing indicators
- Download processed videos when complete

## Technical Details

### Font System
- **Title Fonts**: Located in `Fonts/` directory
- **Subtitle Fonts**: Located in `SubtitleFonts/` directory
- Language-specific font selection for optimal rendering

### Supported Languages & Fonts
- **Japanese**: Noto Sans JP (subtitles), M PLUS 1p ExtraBold (titles)  
- **Chinese**: Noto Sans SC
- **Korean**: DoHyeon-Regular
- **Western Languages** (English/Spanish/German/French): Roboto/NotoSans-Regular
- **Vietnamese**: Roboto
- **Thai**: Kanit-regular

### Processing Pipeline
1. Audio extraction using Whisper
2. Text translation using Claude AI
3. Font rendering with PIL for accurate text display
4. Video composition with OpenCV
5. Multiple language outputs generated

## File Structure
```
/web_uploads/          # Uploaded video files
/web_processed/        # Processed output videos  
/templates/           # HTML templates
/static/temp/         # Temporary files and thumbnails
/SubtitleFonts/       # Language-specific subtitle fonts
/Fonts/              # Language-specific title fonts
```

## API Endpoints

- `POST /upload` - File upload handling
- `GET /select_languages` - Language selection page
- `POST /save_languages` - Save selected languages
- `GET /setup_video/<index>` - Individual video setup
- `POST /save_video_settings` - Save video configuration  
- `POST /extract_audio` - Whisper audio processing
- `GET /process_videos` - Processing status page
- `POST /start_processing` - Begin video processing
- `GET /progress/<session_id>` - Real-time progress updates
- `GET /download_all` - Download processed videos

## Browser Compatibility

- Chrome/Edge 90+
- Firefox 88+  
- Safari 14+

Requires JavaScript enabled for full functionality.

## Development

The application uses:
- **Flask** for web framework
- **Bootstrap 5** for responsive UI
- **jQuery** for client-side interactions
- **OpenCV** for video processing
- **PIL/Pillow** for text rendering
- **Whisper** for audio transcription
- **Claude API** for translation

## Production Deployment

For production use:
1. Change the Flask secret key in `app.py`
2. Set `debug=False`
3. Use a production WSGI server (gunicorn, uwsgi)
4. Configure proper file upload limits
5. Set up SSL/HTTPS
6. Configure database for session storage

## Troubleshooting

- **File upload fails**: Check file size limits and format support
- **Font rendering issues**: Verify font files exist in correct directories
- **Processing errors**: Check API keys and network connectivity
- **Browser compatibility**: Ensure JavaScript is enabled

## Support

For issues and feature requests, refer to the main project documentation.