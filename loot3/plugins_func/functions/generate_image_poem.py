import os
import sys
import uuid
import logging
from plugins_func.register import register_function, ToolType, ActionResponse, Action

from plugins_func.functions.utils.make_image import generate_image_task
from plugins_func.functions.utils.printer_util import create_print_bin_image
from plugins_func.functions.utils.convToLvgl1 import png_to_lvgl_bin

if sys.platform == "win32":
    sys.stderr.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")

logger = logging.getLogger("Image-Service-FC")
logging.basicConfig(level=logging.INFO)

# -----------------------------
# 定义 function_call schema
# -----------------------------
generate_image_poem_function_desc = {
    "type": "function",
    "function": {
        "name": "generate_image_poem",
        "description": "生成(诗/诗词/诗歌)的图片，打印(诗/诗词/诗歌)，生成并打印(诗/诗词/诗歌)，generate poem image, print poem, print poem image",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "诗标题"
                },
                "author_era": {
                    "type": "string",
                    "description": "诗作者和年代"
                },
                "content": {
                    "type": "string",
                    "description": "诗全文"
                },
                "mode": {
                    "type": "string",
                    "description": "图片模式：poem",
                    "enum": ["poem"],
                    "default": "poem"
                },
                "quality": {
                    "type": "string",
                    "description": "图片质量：hq",
                    "enum": ["hq"],
                    "default": "hq"
                }
            },
            "required": ["title", "author_era", "content"]
        }
    }
}


# -----------------------------
# function_call 实现
# -----------------------------
@register_function(
    "generate_image_poem",
    generate_image_poem_function_desc,
    ToolType.WAIT
)
def generate_image_poem(title: str, author_era: str, content: str, mode: str = "poem", quality: str = "auto"):
    """
    生成可打印/贴纸图片，并返回 ActionResponse
    """
    try:
        folder_path = "image_results"
        os.makedirs(folder_path, exist_ok=True)
        # folder_path = r"\\192.168.2.109\huishi\安装包\xiaozhi-server-log"
        filename = f"{uuid.uuid4().hex}.png"
        image_save_path = os.path.join(folder_path, filename)

        text = f"""
        诗名: {title}
        作者: {author_era}
        全文: {content}
        """
        poem_dict = {
            "title": title,
            "author_era": author_era,
            "content": content,
        }
        # 调用原有生成逻辑
        result = generate_image_task(
            text=text,
            save_path=image_save_path,
            mode=mode,
            quality=quality,
            other=poem_dict
        )

        image_save_path = result["save_path"]

        # 生成 display_bin
        display_size = (240, 240)
        display_bin_file = image_save_path.replace(".png", f"_{display_size[0]}x{display_size[1]}_rgb565.bin")
        png_to_lvgl_bin(image_save_path, display_bin_file, output_format="rgb565", target_size=display_size)

        # 生成打印用 bin
        bin_save_path = image_save_path.replace(".png", "_400x400.bin")
        create_print_bin_image(image_save_path, bin_save_path)

        response_data = {
            "success": True,
            "response": "已经为您创建好图像了。" if result.get("response") is None else result.get("response"),
            "type": "image poem",
            "data": {
                "type": "sticker",
                "mode": result["mode"],
                "backend": result["backend"],
                "prompt": result["prompt"],
                "duration_sec": result["duration_sec"],
                "display_bin": os.path.abspath(display_bin_file),
                "display_size": display_size,
                "print_bin": os.path.abspath(bin_save_path),
            }
        }

        logger.info(f"图片生成成功: {text}, 保存路径: {image_save_path}")
        return ActionResponse(action=Action.REQLLM, result="图片生成成功", response=response_data)

    except Exception as e:
        logger.exception("generate_image_poem error")
        return ActionResponse(action=Action.RESPONSE, result="图片生成失败", response={"success": False, "error": str(e)})
