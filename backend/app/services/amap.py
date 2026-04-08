"""
高德地图 POI 周边搜索服务。
文档：https://lbs.amap.com/api/webservice/guide/api/search
"""

import os
import httpx
from typing import Any
from urllib.parse import quote_plus

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


async def _request_json(path_qs: str, timeout: float) -> dict:
    """
    高德请求容错策略：
    1) 先走显式 HTTP(S) 代理（如果有）
    2) 失败后自动尝试直连
    每种网络路径最多重试 2 次
    """
    proxy = _proxy()
    tried = [proxy] if proxy else []
    tried.append(None)  # 最后尝试直连
    last_exc: Exception | None = None

    for current_proxy in tried:
        for _ in range(2):
            try:
                async with httpx.AsyncClient(timeout=timeout, proxy=current_proxy, trust_env=False) as client:
                    resp = await client.get(f"{AMAP_BASE}{path_qs}")
                    resp.raise_for_status()
                    return resp.json()
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                last_exc = exc
                continue

    if last_exc:
        raise last_exc
    raise RuntimeError("AMAP 请求失败")


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
    # keywords 用于品牌/口味偏好（如奶茶、麦当劳）时做更强语义约束
    qs = (
        f"key={_key()}"
        f"&location={location}"
        f"&types={poi_types}"
        f"&radius={radius}"
        f"&offset={limit}"
        f"&page=1"
        f"&extensions=base"
        f"&sortrule=weight"
    )
    if keywords.strip():
        qs += f"&keywords={quote_plus(keywords.strip())}"

    data = await _request_json(f"/place/around?{qs}", _TIMEOUT)

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
        data = await _request_json(f"/geocode/regeo?{qs}", 3.5)
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


async def regeo_with_adcode(location: str) -> tuple[str, str]:
    """
    逆地理编码扩展版：返回 (address_name, adcode)。
    供需要同时获取地名和 adcode（用于天气查询）的调用方使用，
    避免对同一坐标重复发起两次 regeo 请求。
    失败时返回 ("", "")。
    """
    qs = f"key={_key()}&location={location}&poitype=&radius=100&extensions=base&roadlevel=1"
    try:
        data = await _request_json(f"/geocode/regeo?{qs}", 3.5)
        if data.get("status") != "1":
            return "", ""
        addr = data.get("regeocode", {}).get("addressComponent", {})
        neighborhood = addr.get("neighborhood", {}).get("name", "")
        township = addr.get("township", "")
        district = addr.get("district", "")
        name = neighborhood or township or district or ""
        adcode = addr.get("adcode", "")
        return name, adcode
    except Exception:
        return "", ""


async def get_weather_by_adcode(adcode: str) -> dict:
    """
    根据已知 adcode 直接查询天气，跳过 regeo 步骤。
    供 regeo_with_adcode 结果复用时调用，避免重复 regeo。
    失败时返回 {}。
    """
    if not adcode:
        return {}
    try:
        qs = f"key={_key()}&city={adcode}&extensions=base&output=JSON"
        weather_data = await _request_json(f"/weather/weatherInfo?{qs}", 3.0)
        if weather_data.get("status") != "1" or not weather_data.get("lives"):
            return {}
        live = weather_data["lives"][0]
        return {
            "weather": live.get("weather", ""),
            "temperature": live.get("temperature", ""),
        }
    except Exception:
        return {}


async def geocode(address: str) -> str:
    """文字地址 → "lng,lat"，失败返回空字符串。"""
    qs = f"key={_key()}&address={address}&output=JSON"
    try:
        data = await _request_json(f"/geocode/geo?{qs}", 4.0)
        if data.get("status") != "1" or not data.get("geocodes"):
            return ""
        return data["geocodes"][0].get("location", "")
    except Exception:
        return ""


async def get_static_map(
    poi_location: str,
    user_location: str = "",
    size: str = "750*380",
    zoom: int = 15,
) -> bytes:
    """
    获取高德静态地图图片字节流（由后端代理，不暴露 key）。
    poi_location: "lng,lat"  目标地点
    user_location: "lng,lat" 用户当前位置（可选，显示蓝点）
    """
    markers = f"large,0x16a34a,W:{poi_location}"
    if user_location and user_location != poi_location:
        markers += f"|mid,0x3B82F6,:{user_location}"

    qs = (
        f"key={_key()}"
        f"&zoom={zoom}"
        f"&size={size}"
        f"&markers={markers}"
        f"&scale=2"
    )

    proxy = _proxy()
    async with httpx.AsyncClient(timeout=6.0, proxy=proxy, trust_env=False) as client:
        resp = await client.get(f"{AMAP_BASE}/staticmap?{qs}")
        resp.raise_for_status()
        return resp.content


async def get_weather_from_location(location: str) -> dict:
    """
    从坐标获取当前天气信息（高德天气API）。
    失败时静默返回 {}，不阻塞主流程。
    """
    try:
        # Step 1: 逆地理编码获取 adcode
        qs = f"key={_key()}&location={location}&extensions=base&roadlevel=1"
        regeo_data = await _request_json(f"/geocode/regeo?{qs}", 3.0)
        if regeo_data.get("status") != "1":
            return {}
        adcode = (
            regeo_data.get("regeocode", {})
            .get("addressComponent", {})
            .get("adcode", "")
        )
        if not adcode:
            return {}

        # Step 2: 查询实况天气
        qs2 = f"key={_key()}&city={adcode}&extensions=base&output=JSON"
        weather_data = await _request_json(f"/weather/weatherInfo?{qs2}", 3.0)
        if weather_data.get("status") != "1" or not weather_data.get("lives"):
            return {}
        live = weather_data["lives"][0]
        return {
            "weather": live.get("weather", ""),
            "temperature": live.get("temperature", ""),
        }
    except Exception:
        return {}


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
