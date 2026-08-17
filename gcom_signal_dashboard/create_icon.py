from PIL import Image, ImageDraw

def create_dashboard_icon(size=256):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Outer rounded rectangle background
    margin = int(size * 0.05)
    r = int(size * 0.2)
    bg_color = (25, 25, 30, 255)
    border_color = (0, 210, 160, 255)
    
    # Draw rounded rectangle for background
    draw.rounded_rectangle([margin, margin, size - margin, size - margin], radius=r, fill=bg_color, outline=border_color, width=int(size * 0.03))
    
    # Draw signal bars (4 cellular signal strength bars)
    bar_widths = int(size * 0.12)
    gap = int(size * 0.05)
    start_x = int(size * 0.18)
    base_y = int(size * 0.78)
    
    heights = [int(size * 0.2), int(size * 0.35), int(size * 0.5), int(size * 0.62)]
    colors = [
        (84, 160, 255, 255),   # rssi blue
        (254, 202, 87, 255),   # band yellow
        (162, 155, 254, 255),  # rsrq purple
        (29, 209, 161, 255)    # sinr teal green
    ]
    
    for i in range(4):
        x0 = start_x + i * (bar_widths + gap)
        y0 = base_y - heights[i]
        x1 = x0 + bar_widths
        y1 = base_y
        draw.rounded_rectangle([x0, y0, x1, y1], radius=int(bar_widths * 0.3), fill=colors[i])
        
    # Draw a dynamic pulse/waveform line across top of bars
    points = [
        (int(size * 0.2), int(size * 0.35)),
        (int(size * 0.35), int(size * 0.25)),
        (int(size * 0.5), int(size * 0.4)),
        (int(size * 0.65), int(size * 0.18)),
        (int(size * 0.8), int(size * 0.28)),
    ]
    draw.line(points, fill=(255, 159, 67, 255), width=int(size * 0.04))
    for pt in points:
        pr = int(size * 0.03)
        draw.ellipse([pt[0]-pr, pt[1]-pr, pt[0]+pr, pt[1]+pr], fill=(255, 255, 255, 255))

    return img

def main():
    sizes = [16, 32, 48, 64, 128, 256]
    images = [create_dashboard_icon(s) for s in sizes]
    images[-1].save("app_icon.ico", format="ICO", sizes=[(s, s) for s in sizes])
    print("app_icon.ico created successfully!")

if __name__ == "__main__":
    main()
