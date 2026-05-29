import io
from PIL import Image


def analyze_image(image_bytes: bytes) -> str:
    """分析图片，返回描述信息"""
    try:
        img = Image.open(io.BytesIO(image_bytes))

        # 基本信息
        width, height = img.size
        fmt = img.format or "未知"
        mode = img.mode

        # 文件大小
        size_kb = len(image_bytes) / 1024

        # 主要颜色分析
        colors = get_dominant_colors(img)

        # 构建描述
        lines = [
            f"图片格式: {fmt}",
            f"尺寸: {width}x{height}",
            f"大小: {size_kb:.1f}KB",
            f"主要颜色: {colors}",
        ]

        # 判断图片类型
        if width == height:
            lines.append("类型: 正方形图片（可能是头像）")
        elif width > height * 2:
            lines.append("类型: 超宽图片（可能是横幅）")
        elif height > width * 2:
            lines.append("类型: 超高图片（可能是长图）")
        elif width > height:
            lines.append("类型: 横图")
        else:
            lines.append("类型: 竖图")

        # 动图判断
        if getattr(img, "is_animated", False):
            lines.append(f"动图: 是（{img.n_frames}帧）")

        return "\n".join(lines)

    except Exception as e:
        return f"图片分析失败: {e}"


def get_dominant_colors(img: Image.Image, num_colors: int = 3) -> str:
    """获取图片主要颜色"""
    try:
        # 缩小图片加速分析
        small = img.copy()
        small.thumbnail((50, 50))
        if small.mode != "RGB":
            small = small.convert("RGB")

        # 获取颜色
        colors = small.getcolors(maxcolors=10000)
        if not colors:
            return "无法分析"

        # 按出现次数排序
        colors.sort(key=lambda x: x[0], reverse=True)

        # 转为十六进制颜色值
        result = []
        for count, (r, g, b) in colors[:num_colors]:
            hex_color = f"#{r:02x}{g:02x}{b:02x}"
            color_name = get_color_name(r, g, b)
            result.append(f"{color_name}({hex_color})")

        return ", ".join(result)

    except Exception:
        return "无法分析"


def get_color_name(r: int, g: int, b: int) -> str:
    """根据 RGB 值判断颜色名称"""
    # 简单的颜色分类
    if r > 200 and g > 200 and b > 200:
        return "白色"
    elif r < 50 and g < 50 and b < 50:
        return "黑色"
    elif r > 200 and g < 100 and b < 100:
        return "红色"
    elif r < 100 and g > 200 and b < 100:
        return "绿色"
    elif r < 100 and g < 100 and b > 200:
        return "蓝色"
    elif r > 200 and g > 200 and b < 100:
        return "黄色"
    elif r > 200 and g < 100 and b > 200:
        return "紫色"
    elif r < 100 and g > 200 and b > 200:
        return "青色"
    elif r > 200 and g > 100 and b < 100:
        return "橙色"
    elif r > 150 and g > 100 and b > 100:
        return "粉色"
    elif r > 100 and g > 100 and b > 100:
        return "灰色"
    else:
        return "混合色"
