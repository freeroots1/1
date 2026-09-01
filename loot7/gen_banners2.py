from PIL import Image, ImageDraw, ImageFont
import os

DIR = '/root/.openclaw/workspace/banners'
os.makedirs(DIR, exist_ok=True)
W, H = 750, 320

def draw_gradient(draw, w, h, c1, c2, c3=None):
    for y in range(h):
        r = int(c1[0] + (c2[0]-c1[0])*y/h)
        g = int(c1[1] + (c2[1]-c1[1])*y/h)
        b = int(c1[2] + (c2[2]-c1[2])*y/h)
        draw.line([(0,y),(w,y)], fill=(r,g,b))

def draw_circle(draw, cx, cy, r, fill, alpha=50):
    tmp = Image.new('RGBA', (W, H), (0,0,0,0))
    tdraw = ImageDraw.Draw(tmp)
    tdraw.ellipse([cx-r, cy-r, cx+r, cy+r], fill=(*fill, alpha))
    draw._image.paste(tmp, (0,0), tmp)

def make_banner(fname, grad_colors, tag_bg, tag_text_color, tag_label, title, sub, right_text, right_sub, right_sub2, cta_text, circles):
    img = Image.new('RGB', (W, H), (255,255,255))
    draw = ImageDraw.Draw(img)
    draw_gradient(draw, W, H, grad_colors[0], grad_colors[1], grad_colors[2] if len(grad_colors)>2 else None)
    
    for cx, cy, r, c, a in circles:
        draw_circle(draw, cx, cy, r, c, a)
    
    # Tag
    draw.rounded_rectangle([(50, 45), (190, 70)], radius=4, fill=tag_bg)
    draw.text((57, 48), tag_label, fill=tag_text_color)
    
    # Title
    draw.text((50, 95), title, fill=(255,255,255))
    
    # Subtitle
    draw.text((50, 145), sub, fill='rgba(255,255,255,0.8)')
    
    # Right box
    draw.rounded_rectangle([(510, 50), (710, 280)], radius=12, fill=(255,255,255,30))
    ry = 85
    draw.text((560, ry), right_text, fill=(255,215,0), anchor='ma')
    if right_sub:
        draw.text((560, ry+55), right_sub, fill='rgba(255,255,255,0.5)', anchor='ma')
    if right_sub2:
        draw.text((560, ry+80), right_sub2, fill='rgba(255,255,255,0.5)', anchor='ma')
    
    # CTA
    draw.rounded_rectangle([(50, 210), (210, 250)], radius=20, fill=(255,255,255))
    draw.text((63, 215), cta_text, fill=grad_colors[0])
    
    img.save(os.path.join(DIR, fname))
    print(f'  {fname} ({os.path.getsize(os.path.join(DIR, fname))//1024}KB)')

print('生成Banner...')

# Banner 1 - 开业大促 (红)
make_banner('banner1.png',
    grad_colors=[(196,30,26), (229,57,53)],
    tag_bg=(255,213,79), tag_text_color=(196,30,26), tag_label='🔥 新店开业',
    title='祥和购物超市',
    sub='6月20日 · 盛大开业！全场让利',
    right_text='8.8折', right_sub='开业狂欢', right_sub2='原价9.5折',
    cta_text='🎉 进店有礼 →',
    circles=[(650,250,200,(255,255,255),15), (100,-20,120,(255,215,0),10)]
)

# Banner 2 - 会员专享 (蓝)
make_banner('banner2.png',
    grad_colors=[(21,101,192), (25,118,210)],
    tag_bg=(255,213,79), tag_text_color=(21,101,192), tag_label='💎 会员专享',
    title='注册即送88积分',
    sub='消费1元=1积分·升级金卡享更多优惠',
    right_text='🥇', right_sub='金卡会员', right_sub2='满200元升级',
    cta_text='⭐ 立即成为会员',
    circles=[(100,50,150,(144,202,249),15), (650,380,120,(255,213,79),10)]
)

# Banner 3 - 免费配送 (绿)
make_banner('banner3.png',
    grad_colors=[(46,125,50), (67,160,71)],
    tag_bg=(255,213,79), tag_text_color=(46,125,50), tag_label='🚚 免费配送',
    title='满38元免费送到家',
    sub='生鲜果蔬·日用百货·下单即送',
    right_text='🚚', right_sub='满38元免配送费', right_sub2='下午4点前下单当日达',
    cta_text='🛒 立即选购 →',
    circles=[(100,380,160,(165,214,167),15), (680,50,140,(255,213,79),10)]
)

print('\n全部生成完成！')
