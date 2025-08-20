# 📝 폰트 매핑 가이드

## 폰트 구조

```
📁 프로젝트 루트/
├── Fonts/ (타이틀용)
│   ├── Korean/     DoHyeon-Regular.ttf
│   ├── English/    BebasNeue-Regular.ttf
│   ├── Spanish/    Anton-Regular.ttf
│   ├── German/     Anton-Regular.ttf
│   ├── French/     Anton-Regular.ttf
│   ├── Vietnamese/ BeVietnamPro-ExtraBold.ttf
│   ├── Thai/       Kanit-ExtraBold.ttf
│   ├── Japanese/   MPLUS1p-ExtraBold.ttf
│   └── Chinese/    ZCOOLKuaiLe-Regular.ttf
│
└── SubtitleFonts/ (자막용)
    ├── Korean/     DoHyeon-Regular.ttf (타이틀 폰트 재사용)
    ├── Western/    NotoSans-Regular.ttf ✨NEW
    ├── Vietnamese/ BeVietnamPro-Regular.ttf (타이틀 폰트 재사용)
    ├── Thai/       Kanit-Regular.ttf
    ├── Chinese/    ZCOOLKuaiLe-Regular.ttf (타이틀 폰트 재사용)
    └── Japanese/   MPLUS1p-Regular.ttf ✨NEW
```

## 언어별 폰트 매핑

| 언어 | 타이틀 폰트 | 자막 폰트 | 비고 |
|------|-------------|-----------|------|
| 🇰🇷 Korean | Do Hyeon | Do Hyeon | 동일 폰트 사용 |
| 🇺🇸 English | Bebas Neue | **Noto Sans** ✨ | 전용 자막 폰트 |
| 🇪🇸 Spanish | Anton | **Noto Sans** ✨ | 전용 자막 폰트 |
| 🇩🇪 German | Anton | **Noto Sans** ✨ | 전용 자막 폰트 |
| 🇫🇷 French | Anton | **Noto Sans** ✨ | 전용 자막 폰트 |
| 🇻🇳 Vietnamese | Be Vietnam Pro ExtraBold | Be Vietnam Pro Regular | 동일 패밀리 |
| 🇹🇭 Thai | Kanit ExtraBold | Kanit Regular | 동일 패밀리 |
| 🇯🇵 Japanese | M PLUS 1p ExtraBold | **M PLUS 1p Regular** ✨ | 동일 패밀리 |
| 🇨🇳 Chinese | ZCOOL KuaiLe | ZCOOL KuaiLe | 동일 폰트 사용 |

## 폰트 특성

### 타이틀 폰트 (굵고 임팩트 있음)
- **굵기**: Bold, ExtraBold
- **스타일**: 강렬하고 눈에 띄는 디자인
- **용도**: 영상 제목, 큰 텍스트

### 자막 폰트 (읽기 쉽고 깔끔함)  
- **굵기**: Regular, Medium
- **스타일**: 가독성 우선, 깔끔한 디자인
- **용도**: 자막, 본문 텍스트

## 새로 추가된 자막 폰트

### Noto Sans Regular (Western 언어용)
- **특징**: Google이 개발한 고품질 산세리프 폰트
- **스타일**: 깔끔하고 현대적인 디자인으로 높은 가독성
- **용도**: 영어/스페인어/독일어/프랑스어 자막
- **장점**: 
  - 다국어 지원이 뛰어남
  - 화면에서 읽기 쉬운 최적화된 디자인
  - 자막 텍스트에 적합한 균형 잡힌 글자 간격

### M PLUS 1p Regular (일본어 자막용)
- **특징**: 일본어 히라가나, 가타카나, 한자를 완벽 지원
- **스타일**: 모던하고 깔끔한 산세리프 디자인의 Regular 굵기
- **용도**: 일본어 자막 전용
- **개발**: M+ FONTS PROJECT에서 개발한 오픈소스 폰트
- **장점**: 
  - 일본어 문자의 가독성이 뛰어남
  - 영문자와 일본어의 균형 잡힌 디자인
  - 자막에 적합한 적절한 굵기

## 기존 일본어 타이틀 폰트

### M PLUS 1p ExtraBold
- **특징**: 일본어 히라가나, 가타카나, 한자를 완벽 지원
- **스타일**: 모던하고 깔끔한 산세리프 디자인의 ExtraBold 굵기
- **용도**: 일본어 타이틀 전용
- **개발**: M+ FONTS PROJECT에서 개발한 오픈소스 폰트
- **장점**: 
  - 일본어 문자의 가독성이 뛰어남
  - 영문자와 일본어의 균형 잡힌 디자인
  - ExtraBold 굵기로 타이틀에 적합한 임팩트
