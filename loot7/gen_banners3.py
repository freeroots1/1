from PIL import Image, ImageDraw
import os

DIR = '/root/.openclaw/workspace/banners'
W, H = 750, 320

def gradient(draw, w, h, c1, c2):
    for y in range(h):
        r = int(c1[0] + (c2[0]-c1[0])*y/h)
        g = int(c1[1] + (c2[1]-c1[1])*y/h)
        b = int(c1[2] + (c2[2]-c1[2])*y/h)
        draw.line([(0,y),(w,y)], fill=(r,g,b))

def circle(draw, cx, cy, r, fill, a):
    tmp = Image.new('RGBA', (W, H), (0,0,0,0))
    t = ImageDraw.Draw(tmp)
    t.ellipse([cx-r,cy-r,cx+r,cy+r], fill=(*fill,a))
    draw._image.paste(tmp, (0,0), tmp)

def make(fn, c1, c2, tag_bg, tcol, tag, title, sub, rtext, rsub, rsub2, cta, circs):
    img = Image.new('RGB', (W, H), (255,255,255))
    d = ImageDraw.Draw(img)
    gradient(d, W, H, c1, c2)
    for cx,cy,r,fc,fa in circs:
        circle(d, cx, cy, r, fc, fa)
    # tag
    d.rounded_rectangle([(50,45),(200,70)], 4, fill=tag_bg)
    d.text((57,48), tag, fill=tcol)
    # title
    d.text((50,95), title, fill=(255,255,255))
    # sub
    d.text((50,148), sub, fill=(230,230,230))
    # right box
    d.rounded_rectangle([(500,45),(710,280)], 12, fill=(255,255,255,25))
    d.text((605,85), rtext, fill=(255,213,79), anchor='mt')
    if rsub:
        d.text((605,145), rsub, fill=(200,200,200), anchor='mt')
    if rsub2:
        d.text((605,175), rsub2, fill=(200,200,200), anchor='mt')
    # cta
    d.rounded_rectangle([(50,210),(220,250)], 25, fill=(255,255,255))
    d.text((63,215), cta, fill=c1)
    fp = os.path.join(DIR, fn)
    img.save(fp)
    print(f'  {fn} ({os.path.getsize(fp)//1024}KB)')

print('生成Banner...')
make('banner1.png', (196,30,26), (229,57,53), (255,213,79), (196,30,26), '🔥 新店开业',
     '祥和购物超市', '6月20日 · 盛大开业！全场让利',
     '8.8折', '开业狂欢', '原价9.5折', '🎉 进店有礼 →',
     [(680,300,200,(255,255,255),20), (80,-30,130,(255,213,79),15)])

make('banner2.png', (21,101,192), (25,118,210), (255,213,79), (21,101,192), '💎 会员专享',
     '注册即送88积分', '消费1元=1积分 · 升级金卡享更多优惠',
     '🥇', '金卡会员', '满200元升级', '⭐ 立即成为会员',
     [(100,50,160,(144,202,249),20), (680,400,140,(255,213,79),12)])

make('banner3.png', (46,125,50), (67,160,71), (255,213,79), (46,125,50), '🚚 免费配送',
     '满38元免费送到家', '生鲜果蔬 · 日用百货 · 下单即送',
     '🚚', '满38元免配送费', '下午4点前下单当日达', '🛒 立即选购 →',
     [(120,400,180,(165,214,167),20), (680,30,150,(255,213,79),12)])

print('\n✅ 全部完成！')
