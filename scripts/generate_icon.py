from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


root = Path(__file__).resolve().parents[1]
assets = root / "assets"
assets.mkdir(exist_ok=True)
canvas = Image.new("RGBA", (256, 256), (9, 11, 16, 255))
draw = ImageDraw.Draw(canvas)
draw.rounded_rectangle((22, 22, 234, 234), radius=58, fill=(114, 241, 184, 255))
try:
    font = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 112)
except OSError:
    font = ImageFont.load_default()
box = draw.textbbox((0, 0), "R", font=font)
x = (256 - (box[2] - box[0])) / 2
y = (256 - (box[3] - box[1])) / 2 - box[1]
draw.text((x, y), "R", font=font, fill=(7, 20, 15, 255))
canvas.save(assets / "rgb-sound.png")
canvas.save(assets / "rgb-sound.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
