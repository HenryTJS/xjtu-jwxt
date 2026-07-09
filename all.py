#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
西安交通大学教务系统多功能爬虫（Cookie 分离 + CSV 输出）
支持：
1. 查询整体培养方案列表
2. 查询具体培养方案课程（需 PYFADM）
3. 查询整体课表列表
4. 查询具体教学班课表详情
"""

import requests
import json
import csv
import os
from datetime import datetime
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

# ========================== 工具函数 ==========================
def clean_cookie(cookie_str):
    """移除换行、制表符等空白字符，确保 Cookie 单行"""
    return ''.join(cookie_str.split())


def save_csv(data_list, prefix="data"):
    """
    将数据列表保存为带时间戳的 CSV 文件。
    data_list: list[dict] 格式的数据
    """
    if not data_list:
        print("⚠️ 没有数据可保存。")
        return None

    filename = f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    # 提取所有键作为 CSV 表头（按第一个 dict 的键顺序）
    fieldnames = list(data_list[0].keys())

    with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data_list)

    print(f"✅ 数据已保存至 {filename}（共 {len(data_list)} 条）")
    return filename


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


# ========================== 功能函数 ==========================

def query_overall_plan(njdm="2025", faztdm="99", page_size=200, page_number=1):
    """查询整体培养方案列表"""
    print("\n===== 正在查询整体培养方案 =====")
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
            "value": faztdm
        }
    ]
    data = {
        "querySetting": json.dumps(query_settings, ensure_ascii=False),
        "*order": "-NJDM,+DWDM,+ZYDM",
        "pageSize": str(page_size),
        "pageNumber": str(page_number)
    }
    result = request_post(url, data, referer)
    if result:
        data_list = result.get("data", [])
        print(f"共获取 {len(data_list)} 条记录（当前页）")
        save_csv(data_list, "overall_plan")
    return result


def query_specific_plan(pyfadm):
    """查询具体培养方案课程（需加密参数）"""
    print("\n===== 正在查询具体培养方案课程 =====")
    url = "https://jwxt.xjtu.edu.cn/jwapp/sys/jwpubapp/modules/pyfa/kzkccx.do"
    referer = "https://jwxt.xjtu.edu.cn/jwapp/sys/qxfacx/*default/index.do"
    data = {"PYFADM": pyfadm}
    result = request_post(url, data, referer)
    if result:
        data_list = result.get("data", [])
        save_csv(data_list, "specific_plan")
    return result


def query_overall_schedule(semester="2025-2026-3", task_status="1", page_size=100, page_number=1):
    """查询整体课表列表"""
    print("\n===== 正在查询整体课表列表 =====")
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
                "value": task_status,
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
    data = {
        "querySetting": json.dumps(query_setting, ensure_ascii=False),
        "*order": "+KKDWDM,+KCH,+KXH",
        "pageSize": str(page_size),
        "pageNumber": str(page_number)
    }
    result = request_post(url, data, referer)
    if result:
        data_list = result.get("data", [])
        print(f"共获取 {len(data_list)} 条记录（当前页）")
        save_csv(data_list, "overall_schedule")
    return result


def query_specific_schedule(semester, jxbid):
    """查询具体教学班课表详情"""
    print("\n===== 正在查询具体教学班课表 =====")
    url = "https://jwxt.xjtu.edu.cn/jwapp/sys/kcbcx/modules/qxkcb/qxkcb.do"
    referer = "https://jwxt.xjtu.edu.cn/jwapp/sys/kcbcx/*default/index.do"
    data = {"XNXQDM": semester, "JXBID": jxbid}
    result = request_post(url, data, referer)
    if result:
        data_list = result.get("data", [])
        save_csv(data_list, f"specific_schedule_{jxbid}")
    return result


# ========================== 交互式菜单 ==========================
def main():
    print("=" * 50)
    print("西安交通大学教务系统多功能爬虫")
    print("=" * 50)
    print("请先确保 .env 文件中的 COOKIE_STR 已更新为最新有效值！")
    print("注意：Cookie 必须是一行连续的字符串，不要包含换行。")
    print("-" * 50)
    while True:
        print("\n请选择功能：")
        print("1. 查询整体培养方案列表")
        print("2. 查询具体培养方案课程（需 PYFADM）")
        print("3. 查询整体课表列表")
        print("4. 查询具体教学班课表详情")
        print("0. 退出")
        choice = input("请输入数字选择：").strip()
        if choice == "0":
            print("退出程序。")
            break
        elif choice == "1":
            njdm = input("请输入年级代码（默认2025）：").strip() or "2025"
            faztdm = input("请输入方案状态代码（默认99）：").strip() or "99"
            page_size = input("请输入每页条数（默认200）：").strip() or "200"
            page_number = input("请输入页码（默认1）：").strip() or "1"
            query_overall_plan(njdm, faztdm, int(page_size), int(page_number))
        elif choice == "2":
            pyfadm = input("请输入 PYFADM 参数（必填）：").strip()
            if not pyfadm:
                print("❌ PYFADM 不能为空，请重新选择。")
                continue
            query_specific_plan(pyfadm)
        elif choice == "3":
            semester = input("请输入学期代码（默认2025-2026-3）：").strip() or "2025-2026-3"
            task_status = input("请输入任务状态（默认1）：").strip() or "1"
            page_size = input("请输入每页条数（默认100）：").strip() or "100"
            page_number = input("请输入页码（默认1）：").strip() or "1"
            query_overall_schedule(semester, task_status, int(page_size), int(page_number))
        elif choice == "4":
            semester = input("请输入学期代码（默认2025-2026-3）：").strip() or "2025-2026-3"
            jxbid = input("请输入教学班ID（必填）：").strip()
            if not jxbid:
                print("❌ 教学班ID不能为空，请重新选择。")
                continue
            query_specific_schedule(semester, jxbid)
        else:
            print("无效选择，请重新输入。")


if __name__ == "__main__":
    main()
