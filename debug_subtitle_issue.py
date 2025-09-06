#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import cv2
import numpy as np
from main import translate_subtitle_claude, render_subtitle_text

def debug_subtitle_rendering():
    """자막 렌더링 문제 디버깅"""
    print("=== 자막 렌더링 문제 디버깅 ===")
    
    # 테스트할 언어와 원본 한국어 텍스트
    test_cases = [
        ("japanese", "안녕하세요. 이것은 테스트 자막입니다."),
        ("thai", "안녕하세요. 태국어 번역 테스트입니다."),
        ("vietnamese", "안녕하세요. 베트남어 번역 테스트입니다."),
        ("english", "안녕하세요. 영어 번역 테스트입니다.")  # 비교용
    ]
    
    for language, korean_text in test_cases:
        print(f"\n🌍 {language.upper()} 테스트")
        print(f"원본 한국어: '{korean_text}'")
        
        # 1. 번역 테스트
        try:
            translated = translate_subtitle_claude(korean_text, language)
            print(f"번역 결과: '{translated}'")
            
            # 번역 결과 분석
            if "???" in translated or not translated.strip():
                print(f"❌ 번역 문제 발견: 빈 텍스트 또는 ??? 포함")
                continue
            
            # 2. 렌더링 테스트
            print(f"\n📹 {language} 렌더링 테스트")
            
            # 테스트 프레임 생성
            test_frame = np.zeros((400, 800, 3), dtype=np.uint8)
            test_frame[:] = (50, 50, 50)
            
            # 자막 영역
            subtitle_region = (50, 200, 750, 350)
            cv2.rectangle(test_frame, (subtitle_region[0], subtitle_region[1]), 
                         (subtitle_region[2], subtitle_region[3]), (120, 120, 120), -1)
            
            # 렌더링 수행
            render_subtitle_text(test_frame, translated, subtitle_region, language)
            
            # 결과 저장
            output_path = f"/Users/Gandalf/Desktop/video_auto_translater/debug_{language}.jpg"
            cv2.imwrite(output_path, test_frame)
            print(f"✅ 디버그 이미지 저장: {output_path}")
            
        except Exception as e:
            print(f"❌ {language} 테스트 실패: {e}")
            import traceback
            traceback.print_exc()

def test_direct_text_rendering():
    """직접 텍스트 렌더링 테스트 (번역 없이)"""
    print(f"\n=== 직접 텍스트 렌더링 테스트 ===")
    
    direct_texts = {
        "japanese": "これは日本語のテストです",
        "thai": "นี่คือการทดสอบภาษาไทย", 
        "vietnamese": "Đây là bài kiểm tra tiếng Việt",
        "english": "This is an English test"
    }
    
    for language, text in direct_texts.items():
        print(f"\n🎨 {language} 직접 렌더링")
        print(f"텍스트: '{text}'")
        
        # 테스트 프레임 생성
        test_frame = np.zeros((400, 800, 3), dtype=np.uint8)
        test_frame[:] = (30, 30, 30)
        
        # 자막 영역
        subtitle_region = (50, 200, 750, 350)
        cv2.rectangle(test_frame, (subtitle_region[0], subtitle_region[1]), 
                     (subtitle_region[2], subtitle_region[3]), (100, 100, 100), -1)
        
        try:
            # 직접 렌더링
            render_subtitle_text(test_frame, text, subtitle_region, language)
            
            # 결과 저장
            output_path = f"/Users/Gandalf/Desktop/video_auto_translater/direct_{language}.jpg"
            cv2.imwrite(output_path, test_frame)
            print(f"✅ 직접 렌더링 저장: {output_path}")
            
        except Exception as e:
            print(f"❌ {language} 직접 렌더링 실패: {e}")

if __name__ == "__main__":
    # 직접 텍스트 렌더링 먼저 테스트 (번역 API 없이)
    test_direct_text_rendering()
    
    # 번역 포함 전체 테스트
    debug_subtitle_rendering()