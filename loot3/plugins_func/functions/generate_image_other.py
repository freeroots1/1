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
generate_image_other_function_desc = {
    "type": "function",
    "function": {
        "name": "generate_image_other",
        "description": "基于用户意图和相关上下文ID生成(非贴纸/非诗句)图片,  基于用户意图和相关上下文ID打印(非贴纸/非诗句)图片, generate or print image excluding stickers and poem based on user intent and conversation history.",
        "parameters": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "The refined, descriptive prompt synthesized by the LLM. It should combine the user's current request with visual details."
                },
                "content_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional. List of contentIDs from previous turns containing the raw data needed for the image."
                },
            },
            "required": ["text", "content_ids"]
        }
    }
}

# -----------------------------
# function_call 实现
# -----------------------------
@register_function(
    "generate_image_other",
    generate_image_other_function_desc,
    ToolType.WAIT
)
def generate_image_other(text, content_ids=None):
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
            text=text,
            save_path=image_save_path,
            mode="other",
            quality="hq",
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

        logger.info(f"图片生成成功: {text}, 保存路径: {image_save_path}")
        return ActionResponse(action=Action.REQLLM, result="图片生成成功", response=response_data)

    except Exception as e:
        logger.exception("generate_image_sticker error")
        return ActionResponse(action=Action.RESPONSE, result="图片生成失败",
                              response={"success": False, "error": str(e)})
