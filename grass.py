import asyncio
import json
import logging
import random
import ssl
import time
import uuid
import os
import websockets
from faker import Faker
from websockets_proxy import Proxy, proxy_connect

# 配置日志级别
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 存储已连接的 WebSocket 对象的列表
connected_websockets = []


async def send_message(websocket, message):
    """
    发送消息到 WebSocket 服务器
    """
    message_str = json.dumps(message)
    logging.info(f"Sending message: {message_str}")
    await websocket.send(message_str)


async def receive_message(websocket):
    """
    接收 WebSocket 服务器的消息
    """
    response = await websocket.recv()
    logging.info(f"Received response: {response}")
    return json.loads(response)


async def authenticate(websocket, auth_id, device_id, user_id):
    """
    发送认证消息到 WebSocket 服务器
    """
    auth_message = {
        "id": auth_id,
        "origin_action": "AUTH",
        "result": {
            "browser_id": device_id,
            "user_id": user_id,
            "user_agent": 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            "timestamp": int(time.time()),
            "device_type": "extension",
            "version": "3.3.2"
        }
    }
    await send_message(websocket, auth_message)


async def run_websocket_logic(websocket, user_id, device_id):
    try:
        # 第1步：接收平台auth请求响应
        auth_response = await receive_message(websocket)

        await asyncio.sleep(random.randint(10, 20) / 10)
        # 第3步：进行auth请求
        await authenticate(websocket, auth_response["id"], device_id, user_id)
        await asyncio.sleep(20)

        """
        业务逻辑处理
        """
        # 第2步：发送ping请求
        message = {
            "id": str(uuid.uuid4()),
            "version": "1.0.0",
            "action": "PING",
            "data": {}
        }
        await send_message(websocket, message)

        while True:
            # 第4步：得到认证成功请求响应
            pong_response = await receive_message(websocket)
            await asyncio.sleep(random.randint(1, 9) / 10)
            pong_message = {
                "id": pong_response["id"],
                "origin_action": "PONG"
            }
            # 第5步：回复平台已得到认证成功请求响应
            await send_message(websocket, pong_message)

            await asyncio.sleep(random.randint(180, 250) / 10)

            ping_message = {
                "id": str(uuid.uuid4()),
                "version": "1.0.0",
                "action": "PING",
                "data": {}
            }
            # 第6步：发送心跳包
            await send_message(websocket, ping_message)
            await asyncio.sleep(random.randint(1, 9) / 10)

    except websockets.exceptions.ConnectionClosed as e:
        logging.error(f"Connection closed unexpectedly: {e}")
    finally:
        await websocket.close()  # 确保关闭连接


async def run_with_proxy(uri, ssl_context, custom_headers, device_id, user_id, proxy):
    """
    使用代理运行 WebSocket 连接
    """
    try:
        async with proxy_connect(uri, ssl=ssl_context, extra_headers=custom_headers, proxy=proxy, proxy_conn_timeout=10) as websocket_p:
            # 将连接加入到已连接的 WebSocket 列表中
            connected_websockets.append(websocket_p)
            await run_websocket_logic(websocket_p, user_id, device_id)
    except Exception as e:
        logging.error(f"Error occurred with proxy {proxy.proxy_host}: {proxy.proxy_port} {e}")



async def run_without_proxy(uri, ssl_context, custom_headers, device_id, user_id):
    """
    不使用代理运行 WebSocket 连接
    """
    try:
        async with websockets.connect(uri, ssl=ssl_context, extra_headers=custom_headers) as websocket:
            # 将连接加入到已连接的 WebSocket 列表中
            connected_websockets.append(websocket)
            await run_websocket_logic(websocket, user_id, device_id)
    except Exception as e:
        logging.error(f"Error occurred without proxy  {e}")



async def close_connected_websockets():
    """
    关闭所有已连接的 WebSocket 连接
    """
    # 等待一段时间，确保之前的连接已经完全关闭
    await asyncio.sleep(5)
    for ws in connected_websockets:
        await ws.close()


async def main(user_id, use_proxy, proxies=None):
    """
    主函数
    """
    # 在运行主函数之前确保关闭之前的所有 WebSocket 连接
    await close_connected_websockets()


    tasks = []


    if use_proxy:
        for proxy in proxies:
            device_id = str(uuid.uuid4())
            logging.info(device_id)
            uri_options = ["wss://proxy.wynd.network:4650/"]
            # uri_options = ["wss://proxy.wynd.network:4444"]
            custom_headers = {
                "User-Agent": Faker().chrome()
            }

            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

            tasks.append(run_with_proxy(random.choice(uri_options), ssl_context, custom_headers, device_id, user_id, proxy))
    else:
        device_id = str(uuid.uuid4())
        logging.info(device_id)
        uri_options = ["wss://proxy.wynd.network:4650/"]
        #uri_options = ["wss://proxy.wynd.network:4650"]
        custom_headers = {
            "User-Agent": Faker().chrome()
        }

        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        tasks.append(run_without_proxy(random.choice(uri_options), ssl_context, custom_headers, device_id, user_id))

    await asyncio.gather(*tasks)


if __name__ == "__main__":
    user_id = os.getenv('MT_GRASS_ID')
    if not user_id:
        user_id = '2595e120-4687-4286-aaaa-de52ea13a274'
    logging.info(f"user id: {user_id}")
    use_proxy = False  # 设置为 True 则使用代理，False 则不使用
    # 账号密码模式 'socks5://username:password@address:port'
    # 无密码模式 'socks5://address:port'

    proxies = [Proxy.from_url("socks5://192.168.2.141:1082")]


    loop = asyncio.get_event_loop()
    loop.run_until_complete(main(user_id, use_proxy, proxies))
