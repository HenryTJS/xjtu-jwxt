# xjtu-jwxt

针对西安交通大学教务系统的一些自动化爬取脚本。

## 功能

1. **查询整体培养方案列表** — 按年级、方案状态等条件查询
2. **查询具体培养方案课程** — 需提供 PYFADM 加密参数
3. **查询整体课表列表** — 按学期、任务状态等条件查询
4. **查询具体教学班课表详情** — 需提供教学班 ID

## 快速开始

### 1. 安装依赖

```bash
pip install requests python-dotenv
```

### 2. 配置 Cookie

1. 复制 `.env.example` 为 `.env`（**注意：`.env` 文件包含敏感信息，不会上传到 Git**）：

```bash
copy .env.example .env
```

2. 打开 `.env` 文件，将 `COOKIE_STR` 替换为你从浏览器复制的**完整有效 Cookie 字符串**。

> **如何获取 Cookie？**
> 1. 使用 Chrome/Edge 浏览器登录 [西安交通大学教务系统](https://jwxt.xjtu.edu.cn)
> 2. 按 `F12` 打开开发者工具 → 切换到 **Network（网络）** 标签
> 3. 刷新页面，任意点击一个请求
> 4. 在请求头（Request Headers）中找到 `Cookie:` 字段
> 5. 复制其完整值（**单行字符串，不要包含换行**）

### 3. 运行

```bash
python all.py
```

根据交互式菜单选择功能，输入对应参数即可。

## 输出说明

- 所有查询结果均输出为 **CSV 文件**（UTF-8 BOM 编码，可直接用 Excel 打开）
- 文件名格式：`{功能前缀}_{时间戳}.csv`
- 输出文件已在 `.gitignore` 中配置，**不会上传到 Git**

## 文件说明

| 文件 | 说明 | 是否上传 Git |
|------|------|-------------|
| `all.py` | 主程序脚本 | ✅ 是 |
| `.env` | Cookie 配置文件（敏感信息） | ❌ 否（已在 `.gitignore`） |
| `.env.example` | Cookie 配置模板 | ✅ 是 |
| `.gitignore` | Git 忽略规则 | ✅ 是 |
| `README.md` | 本说明文件 | ✅ 是 |
| `*.csv` | 爬取结果数据 | ❌ 否（已在 `.gitignore`） |

## 注意事项

- Cookie 有时效性，失效后请重新从浏览器复制更新到 `.env` 文件
- Cookie 必须是一行连续的字符串，不要包含换行或多余空格
- 如果请求失败，请检查 Cookie 是否有效
