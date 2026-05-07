import http.client
import os
import uuid

# 创建测试文件
test_content = "Test document content for upload testing."
with open("test_upload.txt", "w", encoding="utf-8") as f:
    f.write(test_content)

boundary = "----WebKitFormBoundary" + uuid.uuid4().hex

# 构建multipart form data（模拟前端的请求格式）
with open("test_upload.txt", "rb") as f:
    file_data = f.read()

body = (
    f"--{boundary}\r\n"
    'Content-Disposition: form-data; name="file"; filename="test_upload.txt"\r\n'
    'Content-Type: text/plain\r\n'
    "\r\n"
    + file_data.decode('utf-8') + "\r\n"
    f"--{boundary}--\r\n"
)

print("=== 测试直接连接后端 ===")
print(f"目标地址: localhost:8000/upload/file")
print(f"请求体长度: {len(body)} bytes")

# 测试直接连接后端
conn = http.client.HTTPConnection("localhost", 8000)
try:
    conn.request(
        "POST",
        "/upload/file",
        body,
        {
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Content-Length": str(len(body))
        }
    )
    response = conn.getresponse()
    print(f"状态码: {response.status}")
    print(f"响应: {response.read().decode('utf-8')}")
except Exception as e:
    print(f"错误: {e}")
finally:
    conn.close()

print("\n=== 测试通过Vite代理 ===")
print(f"目标地址: localhost:3000/api/upload/file")

# 测试通过Vite代理
conn2 = http.client.HTTPConnection("localhost", 3000)
try:
    conn2.request(
        "POST",
        "/api/upload/file",
        body,
        {
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Content-Length": str(len(body)),
            "Origin": "http://localhost:3000"
        }
    )
    response = conn2.getresponse()
    print(f"状态码: {response.status}")
    print(f"响应: {response.read().decode('utf-8')}")
except Exception as e:
    print(f"错误: {e}")
finally:
    conn2.close()

# 清理测试文件
os.remove("test_upload.txt")