// 定义自定义CSS样式，用于设置滚动条的外观。
const customCSS = `
    ::-webkit-scrollbar {
        width: 10px;
    }
    ::-webkit-scrollbar-track {
        background: #27272a;
    }
    ::-webkit-scrollbar-thumb {
        background: #888;
        border-radius: 0.375rem;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: #555;
    }
`;

// 创建一个新的<style>元素，并将自定义CSS内容设置为其文本内容。
const styleTag = document.createElement("style");
styleTag.textContent = customCSS;
document.head.append(styleTag);

let labels = [];//用来存储所有创建的标记元素（浮动边框）

function unmarkPage() {//用于移除之前所有的标记元素，清空labels数组
  // Unmark page logic
  for (const label of labels) {
    document.body.removeChild(label);
  }
  labels = [];
}

function markPage() {// markPage函数：标记页面上的可交互元素
  unmarkPage(); // 首先调用unmarkPage函数，清除之前的标记

  var bodyRect = document.body.getBoundingClientRect();// 获取整个body的边界矩形

  var items = Array.prototype.slice// 获取页面上所有元素，并进行处理
    .call(document.querySelectorAll("*"))// 选择页面上的所有元素
    .map(function (element) {
      // 获取视口的宽度和高
      var vw = Math.max(
        document.documentElement.clientWidth || 0,
        window.innerWidth || 0
      );
      var vh = Math.max(
        document.documentElement.clientHeight || 0,
        window.innerHeight || 0
      );
      // 获取并清理元素的文本内容
      var textualContent = element.textContent.trim().replace(/\s{2,}/g, " ");
      var elementType = element.tagName.toLowerCase();
      var ariaLabel = element.getAttribute("aria-label") || "";
      var name = element.getAttribute("name") || "";
      var title = element.getAttribute("title") || "";
      var placeholder = element.getAttribute("placeholder") || "";
      var role = element.getAttribute("role") || "";
      
      // 获取元素的所有边界矩形，并过滤出有效的矩形
      var rects = [...element.getClientRects()]
        .filter((bb) => {
          var center_x = bb.left + bb.width / 2;
          var center_y = bb.top + bb.height / 2;
          var elAtCenter = document.elementFromPoint(center_x, center_y);

          return elAtCenter === element || element.contains(elAtCenter);
        })
        .map((bb) => {
          const rect = {
            left: Math.max(0, bb.left),
            top: Math.max(0, bb.top),
            right: Math.min(vw, bb.right),
            bottom: Math.min(vh, bb.bottom),
          };
          return {
            ...rect,
            width: rect.right - rect.left,
            height: rect.bottom - rect.top,
          };
        });
      // 计算元素占据的总面积
      var area = rects.reduce((acc, rect) => acc + rect.width * rect.height, 0);
      
      // 返回一个对象，包含元素及其相关信息
      return {
        element: element,
        include:
          element.tagName === "INPUT" ||
          element.tagName === "TEXTAREA" ||
          element.tagName === "SELECT" ||
          element.tagName === "BUTTON" ||
          element.tagName === "A" ||
          element.onclick != null ||// 具有onclick事件监听器
          window.getComputedStyle(element).cursor == "pointer" ||// 鼠标指针样式为"pointer"
          element.tagName === "IFRAME" ||
          element.tagName === "VIDEO",
        area,
        rects,
        text: textualContent,
        type: elementType,
        ariaLabel: ariaLabel,
        name: name,
        title: title,
        placeholder: placeholder,
        role: role
      };
    })
    .filter((item) => item.include && item.area >= 20);

  // 只保留最内层的可点击元素
  items = items.filter(
    (x) => !items.some((y) => x.element.contains(y.element) && !(x == y))
  );

  // // 生成随机颜色的函数
  function getRandomColor() {
    var letters = "0123456789ABCDEF";
    var color = "#";
    for (var i = 0; i < 6; i++) {
      color += letters[Math.floor(Math.random() * 16)];
    }
    return color;
  }

  // 为选中的元素创建浮动边框和标签
  items.forEach(function (item, index) {
    item.rects.forEach((bbox) => {
      newElement = document.createElement("div");
      var borderColor = getRandomColor();
      newElement.style.outline = `2px dashed ${borderColor}`;
      newElement.style.position = "fixed";
      newElement.style.left = bbox.left + "px";
      newElement.style.top = bbox.top + "px";
      newElement.style.width = bbox.width + "px";
      newElement.style.height = bbox.height + "px";
      newElement.style.pointerEvents = "none";
      newElement.style.boxSizing = "border-box";
      newElement.style.zIndex = 2147483647;

      // 添加浮动标签
      var label = document.createElement("span");
      label.textContent = index;
      label.style.position = "absolute";
      label.style.top = "-19px";
      label.style.left = "0px";
      label.style.background = borderColor;
      label.style.color = "white";
      label.style.padding = "2px 4px";
      label.style.fontSize = "12px";
      label.style.borderRadius = "2px";
      newElement.appendChild(label);

      document.body.appendChild(newElement);
      labels.push(newElement);
    });
  });
   // 收集所有标记元素的中心坐标及其类型、文本内容等信息
  const coordinates = items.flatMap((item) =>
    item.rects.map(({ left, top, width, height }) => ({
      x: (left + left + width) / 2,
      y: (top + top + height) / 2,
      type: item.type,
      text: item.text,
      ariaLabel: item.ariaLabel,
      name: item.name,
      title: item.title,
      placeholder: item.placeholder,
      role: item.role
    }))
  );
  return coordinates;
}