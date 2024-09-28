# 使用官方 Python 镜像
FROM swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/python:3.11-slim

# 设置工作目录
WORKDIR /security-cellm

# 复制依赖文件并安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 暴露 Flask 端口
EXPOSE 5000

# 启动 Flask 应用
CMD ["python", "security-cellm.py"]
