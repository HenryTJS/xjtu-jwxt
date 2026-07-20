#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量爬取脚本：
1. 查询整体培养方案列表（任务1），提取所有 PYFADM 及对应的 PYFAMC
2. 遍历每个 PYFADM 查询具体培养方案课程（任务2）
3. 合并所有课程数据，增加 PYFAMC 列，输出为 {njdm}.csv
"""

import requests
import json
import csv
import os
import sys
from dotenv import load_dotenv

# ========================== 加载环境变量 ==========================
load_dotenv()
COOKIE_STR = os.getenv("COOKIE_STR", "")

if not COOKIE_STR:
    print("❌ 未检测到 COOKIE_STR 环境变量，请检查 .env 文件配置！")
    print("   参考 .env.example 文件进行配置。")
    exit(1)

# 通用请求头
BASE_HEADERS = {
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "Origin": "https://jwxt.xjtu.edu.cn",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36 Edg/150.0.0.0",
    "X-Requested-With": "XMLHttpRequest",
    "DNT": "1",
}

PAGE_SIZE = "999"


# ========================== 工具函数 ==========================
def clean_cookie(cookie_str):
    """移除换行、制表符等空白字符，确保 Cookie 单行"""
    cookie_str = cookie_str.strip()
    if len(cookie_str) >= 2 and cookie_str[0] in ('"', "'") and cookie_str[-1] == cookie_str[0]:
        cookie_str = cookie_str[1:-1]
    return ''.join(cookie_str.split())


def request_post(url, data, referer):
    """发送 POST 请求并返回 JSON 结果"""
    headers = BASE_HEADERS.copy()
    headers["Cookie"] = clean_cookie(COOKIE_STR)
    headers["Referer"] = referer

    try:
        resp = requests.post(url, headers=headers, data=data, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ 网络请求失败: {e}")
        with open("response_error.html", "w", encoding='utf-8') as f:
            f.write(resp.text)
        return None
    except json.JSONDecodeError:
        print("❌ 返回内容不是有效的 JSON，可能是 Cookie 失效或参数错误")
        with open("response_nonjson.html", "w", encoding='utf-8') as f:
            f.write(resp.text)
        return None


def extract_rows(result):
    """从教务系统 API 响应中提取 rows 数据列表"""
    datas = result.get("datas", {})
    if not datas:
        if isinstance(result, list):
            return result
        elif isinstance(result, dict):
            if "data" in result:
                return result["data"] if isinstance(result["data"], list) else [result["data"]]
            else:
                return [result]
    else:
        module_data = next(iter(datas.values()), {})
        rows = module_data.get("rows", [])
        if rows:
            return rows
        # 没有 rows 时返回空列表，避免混入元数据字段
        return []


def fetch_all_pages(url, data_template, referer):
    """自动翻页获取所有数据"""
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

        if total_size is not None and len(all_rows) >= total_size:
            print(f"  已获取全部 {total_size} 条数据，翻页结束。")
            break

        page_number += 1

    return all_rows


# ========================== 主流程 ==========================
def main():
    print("=" * 50)
    print("批量培养方案课程爬取")
    print("=" * 50)
    print("请先确保 .env 文件中的 COOKIE_STR 已更新为最新有效值！")
    print("-" * 50)

    # 1. 输入年级代码
    njdm = input("请输入年级代码（示例：2025）：").strip()
    if not njdm:
        print("❌ 年级代码不能为空。")
        sys.exit(1)

    # 2. 爬取整体培养方案列表（任务1）
    print(f"\n===== 正在查询 {njdm} 级整体培养方案列表 =====")
    url_plan_list = "https://jwxt.xjtu.edu.cn/jwapp/sys/qxfacx/modules/pyfacxepg/qxpyfacxzl.do"
    referer_plan = "https://jwxt.xjtu.edu.cn/jwapp/sys/qxfacx/*default/index.do"
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

    plan_list = fetch_all_pages(url_plan_list, data_template, referer_plan)
    if not plan_list:
        print(f"❌ 未获取到 {njdm} 级的培养方案列表，无法继续。")
        sys.exit(1)

    print(f"\n共获取 {len(plan_list)} 条培养方案记录")

    # 3. 提取 PYFADM -> PYFAMC 映射
    pyfadm_map = {}  # PYFADM -> PYFAMC
    for plan in plan_list:
        pyfadm = plan.get("PYFADM", "").strip()
        pyfamc = plan.get("PYFAMC", "").strip()
        if pyfadm:
            pyfadm_map[pyfadm] = pyfamc

    print(f"共提取 {len(pyfadm_map)} 个 PYFADM")

    if not pyfadm_map:
        print("❌ 未提取到任何 PYFADM，无法继续。")
        sys.exit(1)

    # 4. 遍历每个 PYFADM 爬取具体培养方案课程（任务2）
    print("\n===== 开始批量爬取具体培养方案课程 =====")
    url_course = "https://jwxt.xjtu.edu.cn/jwapp/sys/jwpubapp/modules/pyfa/kzkccx.do"
    referer_course = "https://jwxt.xjtu.edu.cn/jwapp/sys/qxfacx/*default/index.do"

    all_courses = []  # 合并所有课程数据
    total_pyfadm = len(pyfadm_map)
    for idx, (pyfadm, pyfamc) in enumerate(pyfadm_map.items(), 1):
        print(f"\n  [{idx}/{total_pyfadm}] 正在查询 PYFADM={pyfadm} ({pyfamc})")
        data = {"PYFADM": pyfadm}
        result = request_post(url_course, data, referer_course)
        if not result:
            print(f"  ⚠️ 跳过 PYFADM={pyfadm}")
            continue

        course_list = extract_rows(result)
        if not course_list:
            print(f"  ⚠️ PYFADM={pyfadm} 无课程数据")
            continue

        # 为每条课程记录增加 PYFAMC 列
        for course in course_list:
            course["PYFAMC"] = pyfamc
            all_courses.append(course)

        print(f"  ✅ 获取 {len(course_list)} 条课程，累计 {len(all_courses)} 条")

    # 5. 合并输出为 {njdm}.csv
    if not all_courses:
        print("\n❌ 未获取到任何课程数据。")
        sys.exit(1)

    filename = f"{njdm}.csv"
    fieldnames = list(all_courses[0].keys())

    with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_courses)

    print(f"\n{'=' * 50}")
    print(f"✅ 全部完成！共 {len(all_courses)} 条课程记录")
    print(f"📁 已保存至 {filename}")


if __name__ == "__main__":
    main()
