#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
西安交通大学教务系统多功能爬虫（Cookie 分离 + CSV 输出）
支持：
1. 查询整体培养方案列表
2. 查询具体培养方案课程
3. 查询整体课表列表
4. 查询具体教学班课表详情
5. 查询课程列表
6. 查询课程详情
"""

import requests
import json
import csv
import os
from dotenv import load_dotenv

# ========================== 加载环境变量 ==========================
load_dotenv()
COOKIE_STR = os.getenv("COOKIE_STR", "")

if not COOKIE_STR:
    print("❌ 未检测到 COOKIE_STR 环境变量，请检查 .env 文件配置！")
    print("   参考 .env.example 文件进行配置。")
    exit(1)

# 通用请求头（不含 Cookie，由各函数添加）
BASE_HEADERS = {
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "Origin": "https://jwxt.xjtu.edu.cn",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36 Edg/150.0.0.0",
    "X-Requested-With": "XMLHttpRequest",
    "DNT": "1",
}

# 每页最大条数（一次查完所有数据）
PAGE_SIZE = "999"

# ========================== 工具函数 ==========================
def clean_cookie(cookie_str):
    """移除换行、制表符等空白字符，确保 Cookie 单行"""
    cookie_str = cookie_str.strip()
    # 兼容用户可能在 .env 值两侧加了引号的情况
    if len(cookie_str) >= 2 and cookie_str[0] in ('"', "'") and cookie_str[-1] == cookie_str[0]:
        cookie_str = cookie_str[1:-1]
    return ''.join(cookie_str.split())


def save_csv(data_list, prefix="data"):
    """
    将数据列表保存为 CSV 文件，保留所有列。
    data_list: list[dict] 格式的数据
    """
    if not data_list:
        print("⚠️ 没有数据可保存。")
        return None

    filename = f"{prefix}.csv"
    # 提取所有键作为 CSV 表头（按第一个 dict 的键顺序）
    fieldnames = list(data_list[0].keys())

    with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data_list)

    print(f"✅ 数据已保存至 {filename}（共 {len(data_list)} 条）")
    return filename


def extract_rows(result):
    """从教务系统 API 响应中提取 rows 数据列表（通用）"""
    datas = result.get("datas", {})
    # 如果 datas 为空，可能数据直接放在 result 的某个字段，尝试直接返回 result 本身
    if not datas:
        # 某些接口直接返回数组或对象，直接返回 result 作为单条数据
        if isinstance(result, list):
            return result
        elif isinstance(result, dict):
            # 如果 result 有 data 字段，尝试取 data
            if "data" in result:
                return result["data"] if isinstance(result["data"], list) else [result["data"]]
            else:
                # 否则将整个 result 作为一条数据
                return [result]
    else:
        # 取第一个模块的 rows
        module_data = next(iter(datas.values()), {})
        rows = module_data.get("rows", [])
        if rows:
            return rows
        # 如果 rows 为空，尝试取第一个模块的 data
        if "data" in module_data:
            return module_data["data"] if isinstance(module_data["data"], list) else [module_data["data"]]
        # 否则将整个模块数据作为一条
        return [module_data]
    return []


def request_post(url, data, referer):
    """发送 POST 请求并返回 JSON 结果，自动处理头部编码"""
    headers = BASE_HEADERS.copy()
    # 清理 Cookie 中的空白字符
    headers["Cookie"] = clean_cookie(COOKIE_STR)
    # 只设置域名级别的 Referer，避免长字符串中可能的非 ASCII 字符
    headers["Referer"] = referer

    try:
        resp = requests.post(url, headers=headers, data=data, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ 网络请求失败: {e}")
        # 保存原始响应以便调试
        with open("response_error.html", "w", encoding='utf-8') as f:
            f.write(resp.text)
        print("原始响应已保存到 response_error.html")
        return None
    except json.JSONDecodeError:
        print("❌ 返回内容不是有效的 JSON，可能是 Cookie 失效或参数错误")
        with open("response_nonjson.html", "w", encoding='utf-8') as f:
            f.write(resp.text)
        print("原始响应已保存到 response_nonjson.html")
        return None


def fetch_all_pages(url, data_template, referer):
    """
    自动翻页获取所有数据。
    从第 1 页开始，每页 PAGE_SIZE 条，根据 totalSize 判断是否继续翻页。
    返回合并后的数据列表。
    """
    all_rows = []
    page_number = 1
    total_size = None

    while True:
        data = data_template.copy()
        data["pageSize"] = PAGE_SIZE
        data["pageNumber"] = str(page_number)

        print(f"  正在获取第 {page_number} 页...")
        result = request_post(url, data, referer)
        if not result:
            print(f"  ⚠️ 第 {page_number} 页请求失败，停止翻页。")
            break

        # 获取 totalSize（仅在第一次记录）
        if total_size is None:
            datas = result.get("datas", {})
            module_data = next(iter(datas.values()), {}) if datas else {}
            total_size = module_data.get("totalSize", 0)
            if total_size:
                print(f"  共 {total_size} 条数据，开始翻页获取...")

        rows = extract_rows(result)
        if not rows:
            print(f"  第 {page_number} 页无数据，翻页结束。")
            break

        all_rows.extend(rows)
        print(f"  第 {page_number} 页获取 {len(rows)} 条，累计 {len(all_rows)} 条。")

        # 判断是否还有更多数据
        if total_size is not None and len(all_rows) >= total_size:
            print(f"  已获取全部 {total_size} 条数据，翻页结束。")
            break

        page_number += 1

    return all_rows


# ========================== 功能函数 ==========================

def query_overall_plan():
    """查询整体培养方案列表（自动翻页，合并输出一个 CSV）"""
    print("\n===== 正在查询整体培养方案 =====")
    njdm = input("请输入年级代码（示例：2025）：").strip()
    if not njdm:
        print("❌ 年级代码不能为空。")
        return None

    url = "https://jwxt.xjtu.edu.cn/jwapp/sys/qxfacx/modules/pyfacxepg/qxpyfacxzl.do"
    referer = "https://jwxt.xjtu.edu.cn/jwapp/sys/qxfacx/*default/index.do"
    query_settings = [
        {
            "name": "NJDM",
            "caption": "年级",
            "linkOpt": "AND",
            "builderList": "cbl_String",
            "builder": "equal",
            "value": njdm,
            "value_display": f"{njdm}级"
        },
        {
            "name": "FAZTDM",
            "caption": "",
            "builder": "equal",
            "linkOpt": "AND",
            "value": "99"
        }
    ]
    data_template = {
        "querySetting": json.dumps(query_settings, ensure_ascii=False),
        "*order": "-NJDM,+DWDM,+ZYDM",
    }

    all_rows = fetch_all_pages(url, data_template, referer)
    if all_rows:
        print(f"\n共获取 {len(all_rows)} 条记录")
        save_csv(all_rows, f"overall_plan_{njdm}")
    return all_rows


def query_specific_plan():
    """查询具体培养方案课程（需 PYFADM）"""
    print("\n===== 正在查询具体培养方案课程 =====")
    pyfadm = input("请输入 PYFADM 参数（示例：03406d85277248e69fd1b9cbcb261e25）：").strip()
    if not pyfadm:
        print("❌ PYFADM 不能为空。")
        return None

    url = "https://jwxt.xjtu.edu.cn/jwapp/sys/jwpubapp/modules/pyfa/kzkccx.do"
    referer = "https://jwxt.xjtu.edu.cn/jwapp/sys/qxfacx/*default/index.do"
    data = {"PYFADM": pyfadm}
    result = request_post(url, data, referer)
    if result:
        data_list = extract_rows(result)
        save_csv(data_list, f"specific_plan_{pyfadm}")
    return result


def query_overall_schedule():
    """查询整体课表列表（自动翻页，合并输出一个 CSV）"""
    print("\n===== 正在查询整体课表列表 =====")
    semester = input("请输入学期代码（示例：2025-2026-3）：").strip()
    if not semester:
        print("❌ 学期代码不能为空。")
        return None

    url = "https://jwxt.xjtu.edu.cn/jwapp/sys/kcbcx/modules/qxkcb/qxfbkccx.do"
    referer = "https://jwxt.xjtu.edu.cn/jwapp/sys/kcbcx/*default/index.do"
    query_setting = [
        {
            "name": "XNXQDM",
            "value": semester,
            "linkOpt": "and",
            "builder": "equal"
        },
        [
            {
                "name": "RWZTDM",
                "value": "1",
                "linkOpt": "and",
                "builder": "equal"
            },
            {
                "name": "RWZTDM",
                "linkOpt": "or",
                "builder": "isNull"
            }
        ]
    ]
    data_template = {
        "querySetting": json.dumps(query_setting, ensure_ascii=False),
        "*order": "+KKDWDM,+KCH,+KXH",
    }

    all_rows = fetch_all_pages(url, data_template, referer)
    if all_rows:
        print(f"\n共获取 {len(all_rows)} 条记录")
        save_csv(all_rows, f"overall_schedule_{semester}")
    return all_rows


def query_specific_schedule():
    """查询具体教学班课表详情"""
    print("\n===== 正在查询具体教学班课表 =====")
    jxbid = input("请输入教学班ID（示例：202620271MACH40460101）：").strip()
    if not jxbid:
        print("❌ 教学班ID不能为空。")
        return None

    # 从教学班ID前9位自动提取学期代码（如 202620271 → 2026-2027-1）
    semester = f"{jxbid[:4]}-{jxbid[4:8]}-{jxbid[8:9]}"

    url = "https://jwxt.xjtu.edu.cn/jwapp/sys/kcbcx/modules/qxkcb/qxkcb.do"
    referer = "https://jwxt.xjtu.edu.cn/jwapp/sys/kcbcx/*default/index.do"
    data = {"XNXQDM": semester, "JXBID": jxbid}
    result = request_post(url, data, referer)
    if result:
        data_list = extract_rows(result)
        save_csv(data_list, f"specific_schedule_{jxbid}")
    return result


# ========================== 新增功能：课程查询 ==========================

def query_course_list():
    """查询课程列表（整体课程查询，自动翻页）"""
    print("\n===== 正在查询课程列表 =====")
    url = "https://jwxt.xjtu.edu.cn/jwapp/sys/kccx/modules/kccx/kcxxcx.do"
    referer = "https://jwxt.xjtu.edu.cn/jwapp/sys/kccx/*default/index.do"
    data_template = {
        "KCZTDM": "1",
    }

    all_rows = fetch_all_pages(url, data_template, referer)
    if all_rows:
        print(f"\n共获取 {len(all_rows)} 条课程记录")
        save_csv(all_rows, "course_list")
    return all_rows


def query_course_detail():
    """查询课程详情（根据课程号）"""
    print("\n===== 正在查询课程详情 =====")
    kch = input("请输入课程号（示例：JAPN540912）：").strip()
    if not kch:
        print("❌ 课程号不能为空。")
        return None

    url = "https://jwxt.xjtu.edu.cn/jwapp/sys/kccx/kcxq/initKcdg.do"
    referer = "https://jwxt.xjtu.edu.cn/jwapp/sys/kccx/*default/index.do"
    data = {"KCH": kch}
    result = request_post(url, data, referer)
    if result:
        data_list = extract_rows(result)
        if data_list:
            save_csv(data_list, f"course_detail_{kch}")
        else:
            # 如果提取不到 rows，可能数据直接放在 result 中，我们直接保存整个 result 为一条
            save_csv([result], f"course_detail_{kch}")
    return result


# ========================== 交互式菜单 ==========================
def main():
    print("=" * 50)
    print("西安交通大学教务系统多功能爬虫")
    print("=" * 50)
    print("请先确保 .env 文件中的 COOKIE_STR 已更新为最新有效值！")
    print("-" * 50)
    while True:
        print("\n请选择功能：")
        print("1. 查询整体培养方案列表")
        print("2. 查询具体培养方案课程")
        print("3. 查询整体课表列表")
        print("4. 查询具体教学班课表详情")
        print("5. 查询课程列表")
        print("6. 查询课程详情")
        print("0. 退出")
        choice = input("请输入数字选择：").strip()
        if choice == "0":
            print("退出程序。")
            break
        elif choice == "1":
            query_overall_plan()
        elif choice == "2":
            query_specific_plan()
        elif choice == "3":
            query_overall_schedule()
        elif choice == "4":
            query_specific_schedule()
        elif choice == "5":
            query_course_list()
        elif choice == "6":
            query_course_detail()
        else:
            print("无效选择，请重新输入。")


if __name__ == "__main__":
    main()