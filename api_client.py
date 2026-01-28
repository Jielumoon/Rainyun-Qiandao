"""
雨云 API 客户端封装
用于服务器查询、积分获取、自动续费等功能
"""
import logging
import time
from typing import Optional

import requests

from rainyun.config import Config, get_default_config

logger = logging.getLogger(__name__)


class RainyunAPIError(Exception):
    """雨云 API 调用异常"""
    pass


class RainyunAPI:
    """雨云 API 客户端"""

    def __init__(self, api_key: str, config: Optional[Config] = None):
        """
        初始化 API 客户端

        Args:
            api_key: 雨云 API 密钥（从后台获取）
        """
        self.api_key = api_key
        self.config = config or get_default_config()
        self.api_base_url = self.config.api_base_url
        self.request_timeout = self.config.request_timeout
        self.max_retries = self.config.max_retries
        self.retry_delay = self.config.retry_delay
        self.headers = {
            "x-api-key": api_key,
            "Content-Type": "application/json"
        }

    def _request(self, method: str, endpoint: str, data: dict = None) -> dict:
        """
        发送 API 请求（带重试机制）

        Args:
            method: HTTP 方法 (GET/POST)
            endpoint: API 端点路径
            data: 请求体数据 (POST 时使用)

        Returns:
            API 响应的 data 字段

        Raises:
            RainyunAPIError: API 调用失败时抛出
        """
        url = f"{self.api_base_url}{endpoint}"
        last_error = None

        for attempt in range(1, self.max_retries + 1):
            try:
                if method.upper() == "GET":
                    response = requests.get(url, headers=self.headers, timeout=self.request_timeout)
                else:
                    response = requests.post(url, headers=self.headers, json=data, timeout=self.request_timeout)

                # 先尝试解析 JSON，不管 HTTP 状态码
                # 雨云 API 业务错误也返回 JSON（如 400 + {"code":70007,"message":"..."})
                try:
                    result = response.json()
                except ValueError:
                    # 无法解析 JSON，可能是真正的网络错误
                    response.raise_for_status()
                    raise RainyunAPIError(f"响应不是有效 JSON: {response.text[:200]}")

                # 雨云 API 返回格式：{"code": 200, "message": "...", "data": {...}}
                api_code = result.get("code")
                api_message = result.get("message", "未知错误")

                if api_code != 200:
                    # 业务错误，不需要重试（如积分不足、未到续费时间等）
                    raise RainyunAPIError(f"API 返回错误 [{api_code}]: {api_message}")

                return result.get("data", {})

            except requests.RequestException as e:
                # 网络层错误（连接超时、DNS 解析失败等），可以重试
                last_error = e
                if attempt < self.max_retries:
                    logger.warning(f"请求失败 (第 {attempt} 次): {e}，{self.retry_delay}s 后重试...")
                    time.sleep(self.retry_delay)
                continue

        raise RainyunAPIError(f"网络请求失败 (已重试 {self.max_retries} 次): {last_error}")

    def get_server_ids(self, product_type: str = "rgs") -> list:
        """
        获取所有游戏云服务器 ID 列表

        Args:
            product_type: 产品类型，默认 rgs（游戏云）

        Returns:
            服务器 ID 列表，如 [44500, 44501]
        """
        data = self._request("GET", f"/product/id_list?product_type={product_type}")
        # 返回格式：{"rgs": [44500, 44501, ...]}
        # key 是产品类型，value 是 ID 列表
        return data.get(product_type, [])

    def get_server_detail(self, server_id: int) -> dict:
        """
        获取服务器详细信息

        Args:
            server_id: 服务器 ID

        Returns:
            服务器详情字典，包含：
            - Data: 服务器基础信息（ExpDate, Status, CPU, Memory 等）
            - RenewPointPrice: 续费价格 {"7": 2258, "31": 10000}
        """
        return self._request("GET", f"/product/rgs/{server_id}/")

    def get_user_points(self) -> int:
        """
        获取当前用户积分余额

        Returns:
            积分数量
        """
        data = self._request("GET", "/user/")
        # 返回格式：{"Points": 12345, ...}
        return data.get("Points", 0)

    def renew_server(self, server_id: int, days: int = 7) -> dict:
        """
        使用积分续费服务器

        Args:
            server_id: 服务器 ID
            days: 续费天数（默认 7 天 = 2258 积分）

        Returns:
            续费结果

        Raises:
            RainyunAPIError: 续费失败时抛出
        """
        data = {
            "duration_day": days,
            "product_id": server_id,
            "product_type": "rgs"
        }
        return self._request("POST", "/product/point_renew", data)

    def test_connection(self) -> bool:
        """
        测试 API 连接是否正常

        Returns:
            True 表示连接正常
        """
        try:
            self.get_user_points()
            return True
        except RainyunAPIError:
            return False
