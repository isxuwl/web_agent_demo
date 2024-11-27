# Web Agent

这是一个基于OpenAI GPT和Playwright的Web代理程序，能够模拟人类浏览网页并执行特定任务。

## 功能

- 自动浏览网页
- 执行点击、输入、滚动等操作
- 使用GPT模型理解网页内容并做出决策
- 支持截图和页面元素标记

## 安装

1. 克隆仓库：
   ```
   git clone https://github.com/yourusername/web-agent.git
   cd web-agent
   ```

2. 安装依赖：
   ```
   pip install -r requirements.txt
   ```

3. 设置环境变量：
   - OPENAI_API_KEY：你的OpenAI API密钥
   - OPENAI_API_BASE：API基础URL（如果使用自定义端点）

## 使用

运行主程序：

```
python web_agent.py
```

## 注意事项

- 确保你有足够的OpenAI API使用额度
- 网页浏览可能需要一定时间，请耐心等待
- 程序执行过程中会保存截图，请确保有足够的磁盘空间

## 说明
web_agent.py的Web代理程序，使用Playwright库来自动化Web浏览器操作，并结合OpenAI的GPT模型来生成基于网页截图和当前页面信息的下一步操作指令。


mark_page.js 脚本的主要功能是在网页上标记出特定的交互元素，并为这些元素生成一个浮动边框以及标签。

主要函数说明
1. main()
作用：程序的入口点，初始化浏览器并启动Web Agent。
流程：
启动Playwright浏览器
导航到起始页面（Bing）
调用web_agent()函数执行任务
输出最终结果


2. web_agent(question: str, page: Page, max_steps: int = 10) -> str
作用：Web Agent的主循环，控制整个任务执行流程。
参数：
question: 用户的任务描述
page: Playwright的Page对象
max_steps: 最大执行步骤数
返回值：任务的最终答案或执行结果
流程：
循环执行直到找到答案或达到最大步骤数
在每一步中标记页面元素，获取页面信息
调用GPT获取下一步操作
执行操作并记录结果


3. mark_page(page: Page)
作用：标记页面上的可交互元素
流程：
等待页面加载完成
执行JavaScript脚本标记元素
获取标记后的元素信息
截取页面截图
返回标记信息和截图


4. get_next_action(input: str, scratchpad: str, bbox_descriptions: str, img: str, current_url: str) -> Prediction
作用：调用GPT模型获取下一步操作
参数：
input: 用户的任务描述
scratchpad: 之前的操作历史
bbox_descriptions: 页面元素描述
img: 页面截图（Base64编码）
current_url: 当前页面URL
返回值：包含下一步操作和思考过程的字典


5. perform_action(action: str, args: List[str], page: Page, bboxes: List[BBox]) -> Tuple[str, Optional[Page]]
作用：执行具体的浏览器操作
参数：
action: 操作类型（如Click, Type, Scroll等）
args: 操作参数
page: Playwright的Page对象
bboxes: 页面元素信息
返回值：操作结果描述和可能的新页面对象

辅助函数


click(page: Page, bbox_id: int, bboxes: List[BBox]) -> Tuple[str, Optional[Page]]


type_text(page: Page, bbox_id: int, text: str, bboxes: List[BBox]) -> str


scroll(page: Page, target: str, direction: str, bboxes: List[BBox]) -> str


wait(seconds: int = 5) -> str


go_back(page: Page) -> str


to_search_page(page: Page) -> str


这些函数实现了各种具体的浏览器操作，如点击、输入文本、滚动页面等。


环境变量：程序依赖 OPENAI_API_KEY 和 OPENAI_API_BASE 环境变量。


外部文件：程序需要 mark_page.js 文件来实现页面元素的标记。


错误处理：程序包含了多处错误处理和重试逻辑，以增强稳定性。


日志记录：使用 logging 模块记录详细的执行日志。


美化输出：使用 rich 库美化控制台输出，提高可读性。

## 贡献

欢迎提交问题和拉取请求。对于重大更改，请先开issue讨论您想要改变的内容。

## 许可

[MIT](https://choosealicense.com/licenses/mit/)
