#!/bin/bash
DIR=/root/.openclaw/workspace/banners

# Banner 1 - 开业大促 (红)
convert -size 750x320 \
  -define gradient:direction=south \
  gradient:'#C41E1A'-'#E53935' \
  -fill white -draw "circle 650,-20 650,100" \
  -fill white -draw "circle -50,380 -50,280" \
  -fill '#FFD54F' -draw "rectangle 60,50 180,70" \
  -fill '#C41E1A' -pointsize 22 -annotate +65+67 '🔥 新店开业' \
  -fill white -pointsize 48 -font 'PingFangSC-Bold' -annotate +60+130 '祥和购物超市' 2>/dev/null || \
  -fill white -pointsize 48 -annotate +60+130 '祥和购物超市' \
  -fill '#FFD54F' -pointsize 56 -annotate +530+130 '8.8折' \
  -fill 'rgba(255,255,255,0.5)' -pointsize 18 -annotate +530+170 '原价9.5折' \
  -fill 'rgba(255,255,255,0.8)' -pointsize 24 -annotate +60+170 '6月20日 · 盛大开业！全场让利' \
  -fill white -pointsize 22 -annotate +60+230 '🎉 进店有礼' \
  $DIR/banner1.png 2>&1

echo "banner1 done"

# Banner 2 - 会员专享 (蓝)
convert -size 750x320 \
  -define gradient:direction=south \
  gradient:'#1565C0'-'#1976D2' \
  -fill white -draw "circle 100,-50 100,70" \
  -fill white -draw "circle 600,400 600,300" \
  -fill '#FFD54F' -draw "rectangle 60,50 190,70" \
  -fill '#1565C0' -pointsize 22 -annotate +65+67 '💎 会员专享' \
  -fill white -pointsize 44 -annotate +60+130 '注册即送88积分' \
  -fill '#FFD54F' -pointsize 56 -annotate +530+130 '🥇' \
  -fill 'rgba(255,255,255,0.5)' -pointsize 16 -annotate +530+170 '满200元升级' \
  -fill 'rgba(255,255,255,0.8)' -pointsize 22 -annotate +60+170 '消费1元=1积分 · 升级享优惠' \
  -fill '#FFD54F' -pointsize 22 -annotate +60+230 '⭐ 立即成为会员' \
  $DIR/banner2.png 2>&1

echo "banner2 done"

# Banner 3 - 免费配送 (绿)
convert -size 750x320 \
  -define gradient:direction=south \
  gradient:'#2E7D32'-'#43A047' \
  -fill white -draw "circle 100,400 100,300" \
  -fill white -draw "circle 650,-30 650,70" \
  -fill '#FFD54F' -draw "rectangle 60,50 190,70" \
  -fill '#2E7D32' -pointsize 22 -annotate +65+67 '🚚 免费配送' \
  -fill white -pointsize 48 -annotate +60+130 '满38元免费送到家' \
  -fill '#FFD54F' -pointsize 56 -annotate +530+130 '🚚' \
  -fill 'rgba(255,255,255,0.8)' -pointsize 18 -annotate +530+165 '满38元免配送费' \
  -fill 'rgba(255,255,255,0.8)' -pointsize 18 -annotate +530+190 '下午4点前下单当日达' \
  -fill 'rgba(255,255,255,0.8)' -pointsize 22 -annotate +60+170 '生鲜果蔬 · 日用百货 · 下单即送' \
  -fill white -pointsize 22 -annotate +60+230 '🛒 立即选购' \
  $DIR/banner3.png 2>&1

echo "banner3 done"
ls -la $DIR/banner*.png
