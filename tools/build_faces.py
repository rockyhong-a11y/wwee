#!/usr/bin/env python3
"""assets/faces/*.png 를 모아 표정 아틀라스를 만들고 index.html 에 반영한다.

파일 규격
    assets/faces/<포트레이트 3자리 인덱스>_<무드>.png
    예) 067_rage.png, 081_pain.png, 007_joy.png

    - 인덱스: 000~121 (assets/roster_reference.jpg 에서 번호 확인)
    - 무드: joy proud fierce rage pain down focus calm  (게임의 MOODS 키)
    - 권장 규격: 3:4 비율, 96x128 이상, PNG(투명 배경 권장)
      투명이 아니어도 자동으로 타원 페더 알파를 입힌다.

사용
    python3 tools/build_faces.py            # 빌드 + index.html 패치
    python3 tools/build_faces.py --dry      # 무엇이 반영될지만 출력
"""
import os, re, sys, json, base64
from PIL import Image, ImageDraw, ImageFilter, ImageChops

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC  = os.path.join(ROOT, 'assets', 'faces')
HTML = os.path.join(ROOT, 'index.html')
FW, FH = 96, 128
MOODS = {'joy','proud','fierce','rage','pain','down','focus','calm'}

def alpha(im):
    """이미 투명하면 그대로, 아니면 타원 페더 + 하단 페이드를 입힌다."""
    im = im.convert('RGBA').resize((FW, FH), Image.LANCZOS)
    if im.getchannel('A').getextrema()[0] < 250:
        return im
    m = Image.new('L', (FW, FH), 0)
    ImageDraw.Draw(m).ellipse((FW*.02, -FH*.02, FW*.98, FH), fill=255)
    m = m.filter(ImageFilter.GaussianBlur(10))
    g = Image.linear_gradient('L').rotate(180).resize((FW, FH))
    g = g.point(lambda v: 255 if v > 190 else int(v*255/190))
    im.putalpha(ImageChops.multiply(m, g))
    return im

def main():
    dry = '--dry' in sys.argv
    if not os.path.isdir(SRC):
        sys.exit('assets/faces 폴더가 없습니다.')
    files = []
    for f in sorted(os.listdir(SRC)):
        m = re.fullmatch(r'(\d{1,3})_([a-z]+)\.(png|webp|jpg|jpeg)', f)
        if not m:
            if not f.startswith('.'): print('  건너뜀(형식 불일치):', f)
            continue
        pi, mood = int(m.group(1)), m.group(2)
        if mood not in MOODS:
            print('  건너뜀(알 수 없는 무드):', f); continue
        files.append((pi, mood, os.path.join(SRC, f)))
    if not files:
        sys.exit('표정 파일이 없습니다.')

    tiles, fmap = [], {}
    for pi, mood, path in files:
        tiles.append(alpha(Image.open(path)))
        fmap.setdefault(str(pi), {})[mood] = len(tiles) - 1
    cols = min(8, len(tiles))
    rows = (len(tiles) + cols - 1) // cols
    at = Image.new('RGBA', (FW*cols, FH*rows), (0,0,0,0))
    for i, t in enumerate(tiles):
        at.paste(t, ((i % cols)*FW, (i//cols)*FH))
    tmp = os.path.join(ROOT, '.faces_atlas.webp')
    at.save(tmp, 'WEBP', quality=78, method=6)
    size = os.path.getsize(tmp)
    print(f'표정 {len(tiles)}종 · 캐릭터 {len(fmap)}명 · 격자 {cols}x{rows} · {size:,} bytes')
    for pi in sorted(fmap, key=int):
        print(f'  #{pi}: ' + ', '.join(sorted(fmap[pi])))
    if dry:
        os.remove(tmp); return

    uri = 'data:image/webp;base64,' + base64.b64encode(open(tmp,'rb').read()).decode()
    os.remove(tmp)
    s = open(HTML, encoding='utf-8').read()
    s = re.sub(r'--faces:url\("[^"]*"\)', '--faces:url("' + uri + '")', s, count=1)
    s = re.sub(r'const FCOL = \d+, FROW = \d+;',
               f'const FCOL = {cols}, FROW = {rows};', s, count=1)
    s = re.sub(r'const FACEMAP = \{.*?\};',
               'const FACEMAP = ' + json.dumps(fmap) + ';', s, count=1, flags=re.S)
    open(HTML, 'w', encoding='utf-8').write(s)
    print('index.html 반영 완료 ·', f'{len(s):,}', 'bytes')

if __name__ == '__main__':
    main()
