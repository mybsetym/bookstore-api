# app/utils/format_converter.py
"""
数据格式转换工具：解决数据库字符串与代码列表的格式匹配问题
"""
from typing import List, Optional

def list_to_str(url_list: Optional[List[str]], separator: str = ",", max_count: int = 3) -> str:
    """
    列表转逗号分隔字符串（入库用）
    :param url_list: URL列表（可为空）
    :param separator: 分隔符（默认逗号）
    :param max_count: 最大URL数量（限制最多3张图片）
    :return: 逗号分隔的字符串，空列表/None返回空字符串
    """
    if not url_list:  # 处理None/空列表
        return ""
    # 过滤空URL、去重、限制数量
    valid_urls = [url.strip() for url in url_list if url.strip()]
    limited_urls = valid_urls[:max_count]
    return separator.join(limited_urls)

def str_to_list(url_str: Optional[str], separator: str = ",") -> List[str]:
    """
    字符串转列表（出库用）
    :param url_str: 逗号分隔的URL字符串（可为空）
    :param separator: 分隔符（默认逗号）
    :return: URL列表，空字符串/None返回空列表
    """
    if not url_str or url_str.strip() == "":  # 处理空字符串/None
        return []
    # 分割后过滤空URL（避免",url2"分割出["", "url2"]）
    url_list = [url.strip() for url in url_str.split(separator) if url.strip()]
    return url_list