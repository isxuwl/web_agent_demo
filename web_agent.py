import base64
import io
import os
import time
import logging
from typing import List, Optional, TypedDict,Tuple
from PIL import Image
from playwright.sync_api import sync_playwright, Page
from openai import OpenAI
import re
import json
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

console = Console()

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 环境变量设置
os.environ['OPENAI_API_KEY'] = ''
os.environ['OPENAI_API_BASE'] = ''

def extract_json(text):
    # 使用正则表达式找到 JSON 内容
    match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
    if match:
        json_str = match.group(1)
        try:
            # 尝试解析 JSON
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            print(f"JSON 解析错误: {e}")
            return None
    else:
        return json.loads(text)

    
# 类型定义
class BBox(TypedDict):
    x: float
    y: float
    text: str
    type: str
    ariaLabel: str

class Prediction(TypedDict):
    action: str
    args: Optional[List[str]]

# 初始化OpenAI客户端
client = OpenAI(api_key=os.environ['OPENAI_API_KEY'], base_url=os.environ['OPENAI_API_BASE'])

# 系统提示 (In-Context Learning,ICL)
SYSTEM_PROMPT = """
你是一个像人类一样浏览网页的机器人。你现在需要完成一项任务。在每次迭代中，你将收到一个观察结果，包含网页截图、当前URL、页面标题和一些文本。这个截图的特点是在每个网页元素的左上角放置了数字标签。仔细分析截图信息，识别需要交互的网页元素对应的数字标签，然后按照指南选择以下操作之一：

1. 点击网页元素（Click）
2. 删除文本框中的现有内容，然后输入新内容（Type）
3. 向上或向下滚动（Scroll）
4. 等待（Wait）
5. 返回上一页（GoBack）
6. 导航到指定URL（Navigate）
7. 使用搜索网站重新开始（Search）
8. 提供最终答案（ANSWER）

相应地，操作必须严格遵循以下格式：

- Click [数字标签] 
- Type [数字标签] [内容] 
- Scroll [数字标签或WINDOW] [up或down] 
- Wait 
- GoBack
- Navigate [URL]
- Search
- ANSWER [结论性内容]

* 重要提示 *
仔细分析用户的意图，用户想要操作的网页是否是当前网页，不是的话需要导航到对应网页再操作。特别注意页面的URL变化，避免在已经变化的页面上重复执行操作。

你必须遵循的关键指南：

* 操作指南 *
1) 每次迭代只执行一个操作。
2) 点击或输入时，确保选择正确的边界框。
3) 数字标签位于对应边界框的左上角，颜色相同。
4) 如果操作是Navigate，只需导航到该网站URL，不执行其他操作。
5) 如果网页中的图标没有与输入指令匹配的描述文本，你需要根据标准图标含义推断哪个图标可能代表输入指令。
6) 请严格遵循指南。如果要求查看页面顶部，只看那里；如果顶部没有找到，回答未找到。请严格遵守指示。
7) 严格遵循输入中给出的指南，如果无法找到任何内容，就用ANSWER回复未找到。
8) 除非特别要求，否则不要重复太多指令。
9) 已知URL时直接Navigate，否则使用Search。
10) 每次操作后，仔细检查页面URL和内容是否发生变化。如果页面已经改变，调整你的策略以适应新的页面状态。

* 使用ANSWER的指南 *
1) 当你认为已经找到了任务要求的信息，并且可以回答用户的问题时，使用ANSWER操作。
2) ANSWER操作应该包含对问题的直接回答，尽可能简洁明了。
3) 如果经过多次尝试后仍然无法找到所需信息，也可以使用ANSWER操作，说明无法找到答案的原因。

* 网页浏览指南 *
1) 不要与网页中出现的无用网页元素（如登录、注册、捐赠）交互。
2) 策略性地选择以最小化浪费的时间。
3) 只有在特别要求登录或输入用户名和密码时才执行这些操作，否则不要执行。

你的回复必须严格遵循以下JSON格式：

{
  "thought": "你的详细思考过程（包括当前状态、页面变化的观察、下一步计划及理由）",
  "action": "你选择的一个操作格式"
}

然后用户将提供：
Observation: {{用户提供的带标签的截图、当前URL、页面标题以及action执行结果}}

请注意：
1. JSON中不要使用换行符，保持为单行格式。
2. "thought"和"action"的值应该是字符串。
3. "action"的值必须严格遵循之前指定的操作格式之一。
4. 确保JSON格式正确，可以被解析。
5. 在"thought"中详细描述你的推理过程，包括当前页面状态、URL变化的观察、你的理解和下一步行动的理由。
6. 始终关注页面的变化，特别是URL的变化，以避免重复不必要的操作。

下面是一个示例任务执行过程：

任务：帮我去豆瓣网站找一部名字叫做追凶者的电影

初始状态：当前页面 URL 是 https://www.bing.com

{
  "thought": "当前在必应搜索页面，需要导航到豆瓣网站。我知道豆瓣的网址是 https://www.douban.com/，将直接导航到那里。",
  "action": "Navigate https://www.douban.com/"
}

[系统会执行这个动作，然后提供新的页面截图、URL和标题]

{
  "thought": "现在我们在豆瓣网站首页，URL已经变为 https://www.douban.com/。在顶部导航栏中，我看到了'电影'选项。点击'电影'标签会带我们到豆瓣电影页面，那里更适合进行电影搜索。",
  "action": "Click 10"
}

[系统会执行这个动作，然后提供新的页面截图、URL和标题]

{
  "thought": "我们现在在豆瓣电影页面，URL已经变为 https://movie.douban.com/。在页面顶部有一个搜索框，标记为15。我们需要在这里输入'追凶者'来查找电影。",
  "action": "Type 15 追凶者"
}

[系统会执行这个动作，然后提供新的页面截图、URL和标题]

{
  "thought": "搜索结果已显示，URL变为包含搜索参数的形式。我需要查看是否有完全匹配'追凶者'的电影。第一个结果（标记为3）的标题就是'追凶者'，应该就是我们要找的。我将点击这个链接查看详细信息。",
  "action": "Click 3"
}

[系统会执行这个动作，然后提供新的页面截图、URL和标题]

{
  "thought": "我们已经成功找到'追凶者'电影的详情页面，URL显示为该电影的专属页面。页面上显示了电影的各种信息，包括导演、主演、评分等。现在我可以总结这些信息来完成任务。",
  "action": "ANSWER 我已在豆瓣网站上找到'追凶者'这部电影。这是由徐纪周执导的犯罪惊悚片。主演包括刘烨和张译。豆瓣用户平均评分7.4分。电影于2023年上映，讲述了警察追捕凶手的故事。如需更多信息，我可以进一步描述。"
}

记住，要详细解释你的思考过程，并确保JSON格式正确。特别注意页面的变化，包括URL和内容的变化，避免重复不必要的操作。在每次操作后，重新评估当前页面状态，并据此调整你的策略。
"""

# 工具函数 在给定的页面上点击指定的边界框
def click(page: Page, bbox_id: int, bboxes: List[BBox]) -> Tuple[str, Optional[Page]]:
    """点击指定的边界框，并处理可能打开的新页面"""
    try:
        bbox = bboxes[bbox_id] # 获取边界框信息
        # initial_pages = len(page.context.pages)
        
        # context = browser.new_context()
        with page.context.expect_page() as new_page_info:
            page.mouse.click(bbox["x"], bbox["y"])# 点击边界框并捕获新页面
        page.goto(new_page_info.value.url)# 切换到新页面并等待加载
        page.wait_for_load_state(timeout=100000)
        # page = new_page_info.value

        logging.info(f"点击边界框 {bbox_id} 并切换到新页面: {page.url}")

        return f"点击了边界框 {bbox_id},并导航到页面: {page.url}", None
        
        # # 等待一小段时间，让可能的新页面有时间打开
        # time.sleep(1)
        
        # # 检查是否有新页面打开
        # new_pages = len(page.context.pages)
        # if new_pages > initial_pages:
        #     # 切换到新打开的页面
        #     new_page = page.context.pages[-1]  # 获取最后一个（新）页面
        #     new_page.wait_for_load_state("networkidle", timeout=30000)
        #     logging.info(f"点击边界框 {bbox_id} 并切换到新页面: {new_page.url}")
        #     return f"点击边界框 {bbox_id} 并切换到新页面: {new_page.url}", new_page
        # else:
        #     # 在当前页面等待加载完成
        #     page.wait_for_load_state("networkidle", timeout=30000)
        #     logging.info(f"点击了边界框 {bbox_id}")
        #     return f"点击了边界框 {bbox_id}", None

    except IndexError:
        logging.error(f"错误：未找到边界框 {bbox_id}")
        return f"错误：未找到边界框 {bbox_id}", None

def type_text(page: Page, bbox_id: int, text: str, bboxes: List[BBox]) -> str:
    """在指定的边界框中输入文本"""
    bbox = bboxes[bbox_id]
    page.mouse.click(bbox["x"], bbox["y"])
    page.keyboard.press("Control+A")
    page.keyboard.press('Backspace')
    page.keyboard.type(text)
    page.keyboard.press('Enter')
    page.wait_for_load_state(timeout=60000)
    logging.info(f"在边界框 {bbox_id} 中输入了文本 '{text}' 并提交")
    return f"在边界框 {bbox_id} 中输入了文本 '{text}' 并提交"

# 根据指定的目标（窗口或元素）和方向（向上或向下）进行滚动操作
def scroll(page: Page, target: str, direction: str, bboxes: List[BBox]) -> str:
    """滚动页面或元素"""
    scroll_amount = 500 if target.upper() == "WINDOW" else 200
    scroll_direction = -scroll_amount if direction.lower() == "up" else scroll_amount
    
    if target.upper() == "WINDOW":
        page.evaluate(f"window.scrollBy(0, {scroll_direction})")
        logging.info(f"滚动了窗口 {direction}")
        return f"滚动了窗口 {direction}"
    else:
        bbox = bboxes[int(target)]
        page.mouse.move(bbox["x"], bbox["y"])
        page.mouse.wheel(0, scroll_direction)
        logging.info(f"滚动了元素 {target} {direction}")
        return f"滚动了元素 {target} {direction}"

def wait(seconds: int = 5) -> str:
    """等待指定的秒数"""
    time.sleep(seconds)
    logging.info(f"等待了 {seconds} 秒")
    return f"等待了 {seconds} 秒"

def go_back(page: Page) -> str:
    """返回上一页"""
    page.go_back(wait_until="networkidle", timeout=30000)
    logging.info(f"返回到了上一页 {page.url}")
    return f"返回到了上一页 {page.url}"

def to_search_page(page: Page) -> str:
    """导航到搜索网站首页"""
    page.goto("https://www.bing.com/", wait_until="networkidle", timeout=60000)
    logging.info("导航到了必应搜索首页")
    return "导航到了必应搜索首页"

# 用于标记页面上的可交互元素，并保存带有标记的页面截图
screenshot_counter = 0
def mark_page(page: Page):
    """标记页面上的可交互元素"""
    global screenshot_counter
    page.wait_for_load_state("networkidle",timeout=60000) 
    with open("mark_page.js", encoding='utf-8') as f:# 从文件mark_page.js中读取JavaScript脚本内容
        mark_page_script = f.read()
    
    page.evaluate(mark_page_script)# 执行JavaScript脚本
    for _ in range(10):
        try:
            bboxes = page.evaluate("markPage()")
            break
        except Exception as e:
            logging.warning(f"标记页面失败，重试中: {str(e)}")
            time.sleep(3)
    else:
        logging.error("10次尝试后仍无法标记页面")
        raise Exception("Failed to mark page after 10 attempts")
    
    screenshot = page.screenshot(timeout=60000)
    screenshot_counter += 1 

    # 确保截图目录存在
    screenshot_dir = "./screenshot"
    os.makedirs(screenshot_dir, exist_ok=True)

    file_name = os.path.join(screenshot_dir, f"mark{screenshot_counter}.png")
    img = Image.open(io.BytesIO(screenshot))
    img.save(file_name)
    logging.info(f"保存了截图 {file_name}")
    page.evaluate("unmarkPage()")
    return {
        "img": base64.b64encode(screenshot).decode(),
        "bboxes": bboxes,
    }

import time

def perform_action(action: str, args: List[str], page: Page, bboxes: List[BBox]) -> Tuple[str, Optional[Page]]:
    """执行预测的动作"""
    logging.info(f"执行动作: {action}, 参数: {args}")
    result = ""
    new_page = None
    
    try:
        if action == "Click":
            result, new_page = click(page, int(args[0]), bboxes)
        elif action == "Type":
            result = type_text(page, int(args[0]), args[1], bboxes)
            page.wait_for_load_state("networkidle",timeout=60000)
        elif action == "Scroll":
            result = scroll(page, args[0], args[1], bboxes)
        elif action == "Wait":
            result = wait()
        elif action == "GoBack":
            result = go_back(page)
        elif action == "Search":
            result = to_search_page(page)
        elif action == "Navigate":
            page.goto(args[0], wait_until="networkidle")
            result = f"导航到了 {args[0]}"
        elif action == "ANSWER":
            answer = " ".join(args) if args else "未提供具体答案"
            logging.info(f"找到答案: {answer}")
            result = f"ANSWER: {answer}"
        else:
            logging.warning(f"未知动作: {action}")
            result = f"未知动作: {action}"
        
    except Exception as e:
        logging.error(f"执行操作 {action} 时出错: {str(e)}")
        result = f"执行操作 {action} 时出错: {str(e)}"
    
    return result, new_page

def format_bbox_descriptions(bboxes):
    descriptions = []
    for i, bbox in enumerate(bboxes):
        element_type = bbox['type']
        content = bbox['ariaLabel'] or bbox['text'] or bbox['placeholder']
        x, y = bbox['x'], bbox['y']
        
        description = (
            f"元素 {i}:\n"
            f"  类型: {element_type}\n"
            f"  内容: \"{content}\"\n"
        )
        descriptions.append(description)
    
    return "\n".join(descriptions)

def print_ai_response(response):
    """美化打印AI的响应"""
    try:
        thought = Text(response.get('thought', 'No thought provided'))
        thought.stylize("italic magenta")
        action = Text(response.get('action', 'No action provided'))
        action.stylize("bold green")
        
        panel = Panel(
            Text("\n").join([
                Text("思考:", style="bold"),
                thought,
                Text("\n行动:", style="bold"),
                action
            ]),
            title="AI Response",
            border_style="blue"
        )
        console.print(panel)
    except Exception as e:
        console.print(f"Error printing AI response: {e}", style="bold red")

def get_next_action(input: str, scratchpad: str, bbox_descriptions: str, img: str, current_url: str) -> Prediction:
    """获取下一个动作的预测"""
    prompt = f"""
    任务: {input}

    当前状态:
    URL: {current_url}

    操作历史:
    {scratchpad}

    可用元素:
    {bbox_descriptions}

    请基于以上信息和任务要求，决定下一步操作。
    """

    stream = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{img}"
                        }
                    }
                ]
            }
        ],
        max_tokens=3000,
        stream=True
    )

    full_response = ""
    for chunk in stream:
        if chunk.choices[0].delta.content is not None:
            content = chunk.choices[0].delta.content
            full_response += content
            print(content, end='', flush=True)

    # action_text = response.choices[0].message.content.strip()
    # logging.info(f"GPT响应: {action_text}")
    
    try:
        action_data = extract_json(full_response)
        print_ai_response(action_data)  # 使用美化打印函数
        
        # 确保 action_data 包含 'thought' 和 'action' 键
        if 'thought' not in action_data or 'action' not in action_data:
            raise ValueError("AI response is missing 'thought' or 'action'")
        
        action = action_data['action']
        args = action.split()[1:] if len(action.split()) > 1 else None
        logging.info(f"解析后的动作: {action}, 参数: {args}")
        
        return {
            "action": action.split()[0],
            "args": args,
            "thought": action_data['thought']
        }
    except Exception as e:
        logging.error(f"解析GPT响应时出错: {str(e)}")
        return {
            "action": "ANSWER",
            "args": ["无法理解GPT的响应"],
            "thought": f"解析错误: {str(e)}"
        }


def web_agent(question: str, page: Page, max_steps: int = 10) -> str:
    """Web代理主函数"""
    scratchpad = []
    for step in range(max_steps):
        logging.info(f"步骤 {step + 1}")
        
        marked_page = mark_page(page)
        bbox_descriptions = format_bbox_descriptions(marked_page['bboxes'])
        
        current_url = page.url
        
        scratchpad_text = "\n".join([f"{i+1}. 思考: {s['thought']}\n   操作: {s['action']}\n   结果: {s['result']}" for i, s in enumerate(scratchpad)])
        
        context_info = f"""
        当前URL: {current_url}
        页面标题: {page.title()}
        """
        logging.info(f"上下文信息: \n{context_info}")
        
        prediction = get_next_action(question, scratchpad_text + context_info, bbox_descriptions, marked_page['img'], current_url)
        
        observation,new_page  = perform_action(prediction['action'], prediction['args'], page, marked_page['bboxes'])
        
        
        scratchpad.append({
            "thought": prediction['thought'],
            "action": f"{prediction['action']}: {prediction['args']}",
            "result": observation
        })

        if prediction['action'] == "ANSWER":
            logging.info(f"任务完成，返回答案")
            return observation.split("ANSWER: ", 1)[1] if "ANSWER: " in observation else observation
    
    logging.warning("达到最大步骤数而未找到答案")
    return "达到最大步骤数而未找到答案"

def main():
    """主函数"""
    logging.info("开始执行主函数")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto("https://www.bing.com", timeout=60000)
        page.wait_for_load_state() 
        logging.info("导航到必应首页")
        
        result = web_agent("去arxiv网站，找一篇关于autogen的论文，告诉我他讲了什么", page)
        logging.info(f"最终响应: {result}")
        console.print(f"[bold]最终响应:[/bold] {result}", style="green")
        
        browser.close()
    logging.info("主函数执行完毕")

if __name__ == "__main__":
    main()