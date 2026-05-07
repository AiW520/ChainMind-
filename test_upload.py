import http.client
import os
import uuid

# 创建测试文件
test_content = "This is a test document for upload.\n\nIt contains multiple paragraphs.\n\nThis is the third paragraph."
with open("test_upload.txt", "w", encoding="utf-8") as f:
    f.write(test_content)

boundary = "----WebKitFormBoundary" + uuid.uuid4().hex

# 构建multipart form data
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

# 发送请求
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
    print(f"Status: {response.status} {response.reason}")
    print(f"Headers: {response.getheaders()}")
    print(f"Body: {response.read().decode('utf-8')}")
except Exception as e:
    print(f"Error: {e}")
finally:
    conn.close()

# 清理测试文件
os.remove("test_upload.txt")