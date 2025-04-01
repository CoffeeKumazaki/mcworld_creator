from PIL import Image, ImageDraw
import numpy as np

img = Image.new('L', (450, 300), 0)  # 'L'はグレースケールモード
draw = ImageDraw.Draw(img)

# 道路を描画
for i in range(10):
    draw.line((i*10, 0, i*10, 300), fill=255, width=i+1)

image_array = np.array(img)
##  csvファイルに保存
np.savetxt('image_array.csv', image_array, delimiter=',', fmt='%d')