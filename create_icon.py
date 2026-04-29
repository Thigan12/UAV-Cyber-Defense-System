from PIL import Image, ImageDraw

def create_drone_icon():
    img = Image.new('RGBA', (100, 100), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    color_safe = "#00f0ff"
    
    # Arms (X shape)
    draw.line([20, 20, 80, 80], fill=color_safe, width=6)
    draw.line([20, 80, 80, 20], fill=color_safe, width=6)
    
    # Center body
    draw.ellipse([35, 35, 65, 65], fill="#131b26", outline=color_safe, width=4)
    
    # Propeller guards
    draw.ellipse([5, 5, 35, 35], outline=color_safe, width=3)
    draw.ellipse([65, 65, 95, 95], outline=color_safe, width=3)
    draw.ellipse([5, 65, 35, 95], outline=color_safe, width=3)
    draw.ellipse([65, 5, 95, 35], outline=color_safe, width=3)
    
    # Front indicator (red triangle)
    draw.polygon([(50, 20), (45, 30), (55, 30)], fill="#ff003c")
    
    img.save("drone_icon_safe.png")

create_drone_icon()
