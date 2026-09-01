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
generate_image_sticker_function_desc = {
    "type": "function",
    "function": {
        "name": "generate_image_sticker",
        "description": "生成趣味/搞笑图片，打印趣味/搞笑图片，生成贴纸，打印贴纸，generate sticker/funny image, print sticker, print funny image",
        "parameters": {
            "type": "object",
            "properties": {
                "visual_des": {
                    "type": "string",
                    "description": "用户输入的图片描述文本，用户意图创建的图片描述信息"
                },
                "mode": {
                    "type": "string",
                    "description": "图片模式：sticker",
                    "enum": ["sticker"],
                    "default": "sticker"
                },
                "quality": {
                    "type": "string",
                    "description": "图片质量：hq",
                    "enum": ["hq"],
                    "default": "hq"
                }
            },
            "required": ["visual_des"]
        }
    }
}

# -----------------------------
# function_call 实现
# -----------------------------
@register_function(
    "generate_image_sticker",
    generate_image_sticker_function_desc,
    ToolType.WAIT
)
def generate_image_sticker(visual_des: str, mode: str = "sticker", quality: str = "hq"):
    response_data = generate_image_sticker_direct(visual_des, mode, quality)
    if response_data["success"]:
        return ActionResponse(action=Action.REQLLM, result="图片生成成功", response=response_data)
    else:
        return ActionResponse(action=Action.RESPONSE, result="图片生成失败", response=response_data)

def generate_image_sticker_direct(visual_des: str, mode: str = "sticker", quality: str = "hq"):
    """
    生成可打印/贴纸图片，并返回 ActionResponse
    """
    try:
        folder_path = "image_results"
        os.makedirs(folder_path, exist_ok=True)
        # folder_path = r"\\192.168.2.109\huishi\安装包\xiaozhi-server-log"
        filename = f"{uuid.uuid4().hex}.png"
        image_save_path = os.path.join(folder_path, filename)

        # 调用原有生成逻辑
        result = generate_image_task(
            text=visual_des,
            save_path=image_save_path,
            mode=mode,
            quality=quality,
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
            "type": "image sticker",
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

        logger.info(f"图片生成成功: {visual_des}, 保存路径: {image_save_path}")
        return response_data

    except Exception as e:
        logger.exception("generate_image_sticker error")
        return {"success": False, "error": str(e)}

