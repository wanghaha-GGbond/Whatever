"""
高德地图 POI 周边搜索服务。
文档：https://lbs.amap.com/api/webservice/guide/api/search
"""

import os
import httpx
from typing import Any

AMAP_BASE = "https://restapi.amap.com/v3"
_TIMEOUT = 5.0  # seconds


def _proxy() -> httpx.Proxy | None:
    """
    使用环境变量里的 HTTP 代理（跳过 SOCKS，httpx 不支持 SOCKS）。
    ALL_PROXY=socks:// 会让 httpx 崩溃，trust_env=False 则直连不稳定，
    所以这里显式读 HTTPS_PROXY / HTTP_PROXY 中的 http:// 代理。
    """
    for var in ("HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy"):
        url = os.getenv(var, "")
        if url.startswith("http://") or url.startswith("https://"):
            return httpx.Proxy(url)
    return None


def _key() -> str:
    key = os.getenv("AMAP_KEY", "")
    if not key:
        raise RuntimeError("AMAP_KEY 未设置，请在 .env 中配置")
    return key


async def search_around(
    location: str,        # "lng,lat"，例如 "121.4737,31.2304"
    poi_types: str,       # 高德类型码，"|" 分隔
    keywords: str = "",
    radius: int = 3000,   # 搜索半径，单位 m
    limit: int = 20,      # 返回条数（最大25）
) -> list[dict[str, Any]]:
    """
    调用高德周边搜索，返回 POI 列表。
    每个 POI 格式：
    {
        "id": str,
        "name": str,
        "type": str,        # 高德 type 字段，如 "公园广场;公园;公园"
        "type_code": str,   # 高德 typecode
        "location": str,    # "lng,lat"
        "distance": int,    # 米
        "price_level": str, # "0"~"4"，可能为空
        "open_time": str,   # 营业时间，可能为空
        "rating": str,      # 评分，可能为空
        "address": str,
    }
    """
    # 手动拼 URL：httpx params= 会把 | 编码成 %7C，高德不认多类型
    # 注意：高德 keywords 和 types 同时传会互相干扰，优先用 types
    qs = (
        f"key={_key()}"
        f"&location={location}"
        f"&types={poi_types}"
        f"&radius={radius}"
        f"&offset={limit}"
        f"&page=1"
        f"&extensions=base"
        f"&sortrule=distance"
    )

    async with httpx.AsyncClient(timeout=_TIMEOUT, proxy=_proxy(), trust_env=False) as client:
        resp = await client.get(f"{AMAP_BASE}/place/around?{qs}")
        resp.raise_for_status()
        data = resp.json()

    if data.get("status") != "1" or not data.get("pois"):
        return []

    result = []
    for poi in data["pois"]:
        # base 模式：评分/价格在顶层；all 模式在 biz_ext 里
        biz = poi.get("biz_ext") or {}
        result.append({
            "id":          poi.get("id", ""),
            "name":        poi.get("name", ""),
            "type":        poi.get("type", ""),
            "type_code":   poi.get("typecode", ""),
            "location":    poi.get("location", ""),
            "distance":    int(poi.get("distance") or 0),
            "price_level": biz.get("cost") or poi.get("biz_type") or "",
            "open_time":   biz.get("opentime", ""),
            "rating":      biz.get("rating") or poi.get("biz_rating") or "",
            "address":     poi.get("address", ""),
        })
    return result


def get_type_label(type_str: str) -> str:
    """
    从高德 type 字符串（如"公园广场;公园;公园"）提取最后一级作为显示标签。
    """
    if not type_str:
        return "地点"
    parts = type_str.split(";")
    # 取最后非空部分
    for part in reversed(parts):
        if part.strip():
            return part.strip()
    return parts[0]


async def regeo(location: str) -> str:
    """
    逆地理编码：坐标 → 人类可读地址（街道/小区级别）。
    失败时返回空字符串。
    """
    qs = f"key={_key()}&location={location}&poitype=&radius=100&extensions=base&roadlevel=1"
    try:
        async with httpx.AsyncClient(timeout=2.0, proxy=_proxy(), trust_env=False) as client:
            resp = await client.get(f"{AMAP_BASE}/geocode/regeo?{qs}")
            data = resp.json()
        if data.get("status") != "1":
            return ""
        addr = data.get("regeocode", {}).get("addressComponent", {})
        # 优先取：街道 or 社区名
        neighborhood = addr.get("neighborhood", {}).get("name", "")
        township = addr.get("township", "")
        district = addr.get("district", "")
        return neighborhood or township or district or ""
    except Exception:
        return ""


async def geocode(address: str) -> str:
    """文字地址 → "lng,lat"，失败返回空字符串。"""
    qs = f"key={_key()}&address={address}&output=JSON"
    try:
        async with httpx.AsyncClient(timeout=3.0, proxy=_proxy(), trust_env=False) as client:
            resp = await client.get(f"{AMAP_BASE}/geocode/geo?{qs}")
            data = resp.json()
        if data.get("status") != "1" or not data.get("geocodes"):
            return ""
        return data["geocodes"][0].get("location", "")
    except Exception:
        return ""


def nav_url(name: str, location: str) -> str:
    """生成高德地图导航链接（网页版，移动端会唤起 App）。"""
    try:
        lng, lat = location.split(",")
        return (
            f"https://uri.amap.com/navigation?"
            f"to={lng},{lat},{name}&"
            f"mode=walk&"
            f"callnative=1"
        )
    except Exception:
        return f"https://maps.apple.com/?q={name}"
