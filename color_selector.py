#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import cv2
import numpy as np
import tkinter as tk
from tkinter import ttk, colorchooser
from PIL import Image, ImageTk

class ColorSelector:
    def __init__(self, video_path, title_region=None, subtitle_region=None):
        self.video_path = video_path
        self.title_region = title_region or (100, 200, 980, 500)
        self.subtitle_region = subtitle_region or (50, 1600, 1030, 1800)
        
        # 기본 색상 (검정색)
        self.title_color = (0, 0, 0)  # 검정색 (BGR)
        self.subtitle_color = (220, 220, 220)  # 연한 회색 (BGR)
        
        # 비디오 프레임 로드
        cap = cv2.VideoCapture(video_path)
        ret, self.original_frame = cap.read()
        cap.release()
        
        if not ret:
            raise Exception("비디오를 읽을 수 없습니다.")
        
        self.current_frame = self.original_frame.copy()
        self.setup_gui()
        self.update_preview()
    
    def setup_gui(self):
        """GUI 설정"""
        self.root = tk.Tk()
        self.root.title("배경색 선택기")
        self.root.geometry("800x700")
        
        # 메인 프레임
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 제목
        title_label = ttk.Label(main_frame, text="타이틀 및 자막 배경색 설정", 
                               font=("Arial", 16, "bold"))
        title_label.pack(pady=(0, 20))
        
        # 색상 선택 섹션
        color_frame = ttk.LabelFrame(main_frame, text="색상 선택", padding=10)
        color_frame.pack(fill=tk.X, pady=(0, 20))
        
        # 타이틀 색상
        title_color_frame = ttk.Frame(color_frame)
        title_color_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(title_color_frame, text="타이틀 배경색:", width=15).pack(side=tk.LEFT)
        
        self.title_color_canvas = tk.Canvas(title_color_frame, width=50, height=30, 
                                           bg=self.bgr_to_hex(self.title_color))
        self.title_color_canvas.pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(title_color_frame, text="색상 선택", 
                  command=self.select_title_color).pack(side=tk.LEFT)
        
        # 자막 색상  
        subtitle_color_frame = ttk.Frame(color_frame)
        subtitle_color_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(subtitle_color_frame, text="자막 배경색:", width=15).pack(side=tk.LEFT)
        
        self.subtitle_color_canvas = tk.Canvas(subtitle_color_frame, width=50, height=30,
                                              bg=self.bgr_to_hex(self.subtitle_color))
        self.subtitle_color_canvas.pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(subtitle_color_frame, text="색상 선택", 
                  command=self.select_subtitle_color).pack(side=tk.LEFT)
        
        # 미리보기 섹션
        preview_frame = ttk.LabelFrame(main_frame, text="미리보기", padding=10)
        preview_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        # 이미지 라벨
        self.preview_label = ttk.Label(preview_frame)
        self.preview_label.pack()
        
        # 버튼 섹션
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        
        ttk.Button(button_frame, text="확인", 
                  command=self.confirm_colors).pack(side=tk.RIGHT, padx=(10, 0))
        ttk.Button(button_frame, text="취소", 
                  command=self.cancel).pack(side=tk.RIGHT)
        ttk.Button(button_frame, text="기본값 복원", 
                  command=self.reset_colors).pack(side=tk.LEFT)
        
        self.result = None
    
    def bgr_to_hex(self, bgr_color):
        """BGR 색상을 HEX로 변환"""
        b, g, r = bgr_color
        return f"#{r:02x}{g:02x}{b:02x}"
    
    def hex_to_bgr(self, hex_color):
        """HEX 색상을 BGR로 변환"""
        hex_color = hex_color.lstrip('#')
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        return (b, g, r)
    
    def select_title_color(self):
        """타이틀 색상 선택"""
        current_hex = self.bgr_to_hex(self.title_color)
        color = colorchooser.askcolor(color=current_hex, title="타이틀 배경색 선택")
        
        if color[1]:  # 색상이 선택되었으면
            self.title_color = self.hex_to_bgr(color[1])
            self.title_color_canvas.configure(bg=color[1])
            self.update_preview()
    
    def select_subtitle_color(self):
        """자막 색상 선택"""
        current_hex = self.bgr_to_hex(self.subtitle_color)
        color = colorchooser.askcolor(color=current_hex, title="자막 배경색 선택")
        
        if color[1]:  # 색상이 선택되었으면
            self.subtitle_color = self.hex_to_bgr(color[1])
            self.subtitle_color_canvas.configure(bg=color[1])
            self.update_preview()
    
    def reset_colors(self):
        """기본 색상으로 복원"""
        self.title_color = (0, 0, 0)  # 검정색
        self.subtitle_color = (220, 220, 220)  # 연한 회색
        
        self.title_color_canvas.configure(bg=self.bgr_to_hex(self.title_color))
        self.subtitle_color_canvas.configure(bg=self.bgr_to_hex(self.subtitle_color))
        self.update_preview()
    
    def update_preview(self):
        """미리보기 업데이트"""
        # 프레임 복사
        preview_frame = self.original_frame.copy()
        
        # 타이틀 영역에 색상 적용
        tx1, ty1, tx2, ty2 = self.title_region
        cv2.rectangle(preview_frame, (tx1, ty1), (tx2, ty2), self.title_color, -1)
        cv2.rectangle(preview_frame, (tx1, ty1), (tx2, ty2), (0, 0, 255), 2)  # 빨간 테두리
        
        # 자막 영역에 색상 적용
        sx1, sy1, sx2, sy2 = self.subtitle_region
        cv2.rectangle(preview_frame, (sx1, sy1), (sx2, sy2), self.subtitle_color, -1)
        cv2.rectangle(preview_frame, (sx1, sy1), (sx2, sy2), (0, 255, 0), 2)  # 초록 테두리
        
        # 라벨 추가
        cv2.putText(preview_frame, "Title Area", (tx1, ty1-10), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        cv2.putText(preview_frame, "Subtitle Area", (sx1, sy1-10), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        # 이미지 크기 조정 (GUI에 맞게)
        height, width = preview_frame.shape[:2]
        max_width = 600
        max_height = 400
        
        scale = min(max_width/width, max_height/height)
        new_width = int(width * scale)
        new_height = int(height * scale)
        
        resized_frame = cv2.resize(preview_frame, (new_width, new_height))
        
        # OpenCV BGR을 RGB로 변환
        rgb_frame = cv2.cvtColor(resized_frame, cv2.COLOR_BGR2RGB)
        
        # PIL 이미지로 변환
        pil_image = Image.fromarray(rgb_frame)
        photo = ImageTk.PhotoImage(pil_image)
        
        # 라벨 업데이트
        self.preview_label.configure(image=photo)
        self.preview_label.image = photo  # 참조 유지
    
    def confirm_colors(self):
        """색상 확인"""
        self.result = {
            'title_color': self.title_color,
            'subtitle_color': self.subtitle_color
        }
        self.root.quit()
        self.root.destroy()
    
    def cancel(self):
        """취소"""
        self.result = None
        self.root.quit()
        self.root.destroy()
    
    def show(self):
        """색상 선택기 표시"""
        self.root.mainloop()
        return self.result

def select_background_colors(video_path, title_region=None, subtitle_region=None):
    """배경색 선택 함수"""
    try:
        selector = ColorSelector(video_path, title_region, subtitle_region)
        return selector.show()
    except Exception as e:
        print(f"❌ 색상 선택기 오류: {e}")
        # 기본값 반환
        return {
            'title_color': (0, 0, 0),  # 검정색
            'subtitle_color': (220, 220, 220)  # 연한 회색
        }

if __name__ == "__main__":
    # 테스트
    video_path = "input_videos/그냥 눈물 밖에 나오지 않습니다.mp4"
    result = select_background_colors(video_path)
    if result:
        print(f"선택된 색상:")
        print(f"  타이틀: {result['title_color']}")
        print(f"  자막: {result['subtitle_color']}")
    else:
        print("색상 선택이 취소되었습니다.")