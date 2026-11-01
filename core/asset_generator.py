import os
from PIL import Image, ImageDraw

assets_dir = 'assets'
os.makedirs(assets_dir, exist_ok=True)

def create_cute_pet(filename, body_color, eye_color="black", blush_color="#ff9999", 
                    frames_count=4, bounce_height=8, eye_state="open", extra_fx=None):
    """
    生成一个更可爱的、带有圆角的果冻状小精灵
    eye_state: 'open', 'closed', 'happy'
    extra_fx: 'sweat' (汗滴), 'sparkle' (闪光), None
    """
    frames = []
    width, height = 100, 100
    
    for i in range(frames_count):
        img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # 计算跳跃偏移量
        # i=0: 0, i=1: -bounce, i=2: 0, i=3: +bounce (压扁)
        if i == 0 or i == 2:
            y_offset = 0
            squash = 0
        elif i == 1:
            y_offset = -bounce_height
            squash = -2  # 拉长
        else:
            y_offset = bounce_height // 2
            squash = 4   # 压扁
            
        # 身体基础参数
        body_x1, body_x2 = 25 - squash, 75 + squash
        body_y1, body_y2 = 40 + y_offset, 90 + y_offset
        
        # 画阴影 (固定在底部)
        draw.ellipse([30, 85, 70, 95], fill=(0, 0, 0, 50))
        
        # 画身体 (圆角矩形效果，通过画多个重叠的形状模拟像素圆角)
        draw.rounded_rectangle([body_x1, body_y1, body_x2, body_y2], radius=15, fill=body_color)
        
        # 画眼睛
        eye_y = 55 + y_offset + (squash // 2)
        if eye_state == "open":
            draw.ellipse([body_x1 + 12, eye_y, body_x1 + 18, eye_y + 8], fill=eye_color)
            draw.ellipse([body_x2 - 18, eye_y, body_x2 - 12, eye_y + 8], fill=eye_color)
            # 高光
            draw.ellipse([body_x1 + 13, eye_y + 1, body_x1 + 15, eye_y + 3], fill="white")
            draw.ellipse([body_x2 - 17, eye_y + 1, body_x2 - 15, eye_y + 3], fill="white")
        elif eye_state == "happy":
            # 眯眼笑 ^^
            draw.arc([body_x1 + 10, eye_y, body_x1 + 20, eye_y + 6], start=180, end=0, fill=eye_color, width=2)
            draw.arc([body_x2 - 20, eye_y, body_x2 - 10, eye_y + 6], start=180, end=0, fill=eye_color, width=2)
        elif eye_state == "closed":
            # 闭眼 --
            draw.line([body_x1 + 10, eye_y + 4, body_x1 + 20, eye_y + 4], fill=eye_color, width=2)
            draw.line([body_x2 - 20, eye_y + 4, body_x2 - 10, eye_y + 4], fill=eye_color, width=2)

        # 画腮红
        draw.ellipse([body_x1 + 5, eye_y + 6, body_x1 + 15, eye_y + 10], fill=blush_color)
        draw.ellipse([body_x2 - 15, eye_y + 6, body_x2 - 5, eye_y + 10], fill=blush_color)
        
        # 附加特效
        if extra_fx == "sparkle" and i % 2 == 0:
            # 闪光星星
            draw.line([10, 30, 20, 30], fill="yellow", width=2)
            draw.line([15, 25, 15, 35], fill="yellow", width=2)
            draw.line([80, 20, 90, 20], fill="yellow", width=2)
            draw.line([85, 15, 85, 25], fill="yellow", width=2)
        elif extra_fx == "sweat" and i % 2 != 0:
            # 汗滴/努力工作
            draw.ellipse([body_x2 - 5, body_y1 + 5, body_x2 + 3, body_y1 + 15], fill="#89b4fa")

        frames.append(img)
        
    duration = 150 if extra_fx == "sweat" else 250
    frames[0].save(os.path.join(assets_dir, filename), save_all=True, append_images=frames[1:], duration=duration, loop=0)

# 生成更精美的动画
print("Generating cute assets...")
# 1. Idle: 浅蓝色，慢慢呼吸，睁眼
create_cute_pet('idle.gif', body_color='#89b4fa', eye_state="open", frames_count=4, bounce_height=4)

# 2. Action/Working: 橙色，快速跳动，努力工作(汗滴)，闭眼
create_cute_pet('working.gif', body_color='#f9e2af', eye_state="closed", extra_fx="sweat", frames_count=4, bounce_height=10)
# 兼容旧逻辑的 action
create_cute_pet('action.gif', body_color='#f9e2af', eye_state="closed", extra_fx="sweat", frames_count=4, bounce_height=10)

# 3. Done/Accept: 绿色，开心笑眼，带闪光
create_cute_pet('done.gif', body_color='#a6e3a1', eye_state="happy", extra_fx="sparkle", frames_count=4, bounce_height=12)
create_cute_pet('accept.gif', body_color='#a6e3a1', eye_state="happy", extra_fx="sparkle", frames_count=4, bounce_height=12)

# 生成一个简单的托盘图标
img = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)
draw.rounded_rectangle([8, 16, 56, 56], radius=10, fill='#89b4fa')
draw.ellipse([18, 28, 24, 34], fill='black')
draw.ellipse([40, 28, 46, 34], fill='black')
img.save(os.path.join(assets_dir, 'icon.png'))

print("Assets updated!")
