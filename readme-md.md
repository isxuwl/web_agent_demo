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

## 贡献

欢迎提交问题和拉取请求。对于重大更改，请先开issue讨论您想要改变的内容。

## 许可

[MIT](https://choosealicense.com/licenses/mit/)
