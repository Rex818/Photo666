# Photo666 v0.1.0 安装说明

## 📋 系统要求

### 最低要求
- **操作系统**: Windows 10/11, macOS 10.14+, Ubuntu 18.04+
- **Python**: 3.8 或更高版本
- **内存**: 4GB RAM
- **存储空间**: 500MB 可用空间

### 推荐配置
- **操作系统**: Windows 11, macOS 12+, Ubuntu 20.04+
- **Python**: 3.9 或更高版本
- **内存**: 8GB RAM
- **存储空间**: 2GB 可用空间
- **显卡**: 支持OpenGL 3.3+

## 🚀 快速安装

### Windows 用户

#### 方法一：便携版（推荐）
1. 下载 `Photo666_v0.1.0_Portable.zip`
2. 解压到任意目录
3. 双击运行 `Photo666.bat`
4. 首次运行会自动安装依赖，请耐心等待

#### 方法二：源码安装
```bash
# 1. 克隆仓库
git clone https://github.com/your-username/photo666.git
cd photo666

# 2. 创建虚拟环境
python -m venv venv

# 3. 激活虚拟环境
venv\Scripts\activate

# 4. 安装依赖
pip install -r requirements.txt

# 5. 运行程序
python main.py
```

### macOS 用户

#### 方法一：便携版
1. 下载 `Photo666_v0.1.0_Portable.zip`
2. 解压到任意目录
3. 打开终端，进入解压目录
4. 运行 `./Photo666.sh`
5. 首次运行会自动安装依赖

#### 方法二：源码安装
```bash
# 1. 克隆仓库
git clone https://github.com/your-username/photo666.git
cd photo666

# 2. 创建虚拟环境
python3 -m venv venv

# 3. 激活虚拟环境
source venv/bin/activate

# 4. 安装依赖
pip install -r requirements.txt

# 5. 运行程序
python main.py
```

### Linux 用户

#### Ubuntu/Debian
```bash
# 1. 安装系统依赖
sudo apt update
sudo apt install python3 python3-venv python3-pip

# 2. 下载并解压
wget https://github.com/your-username/photo666/releases/download/v0.1.0/Photo666_v0.1.0_Portable.zip
unzip Photo666_v0.1.0_Portable.zip
cd Photo666_v0.1.0_Portable

# 3. 运行程序
./Photo666.sh
```

#### CentOS/RHEL
```bash
# 1. 安装系统依赖
sudo yum install python3 python3-venv python3-pip

# 2. 下载并解压
wget https://github.com/your-username/photo666/releases/download/v0.1.0/Photo666_v0.1.0_Portable.zip
unzip Photo666_v0.1.0_Portable.zip
cd Photo666_v0.1.0_Portable

# 3. 运行程序
./Photo666.sh
```

## 🔧 依赖包说明

Photo666 需要以下Python包：

### 核心依赖
- **PyQt6**: GUI框架
- **Pillow**: 图像处理
- **SQLite3**: 数据库（Python内置）
- **PyYAML**: 配置文件解析
- **structlog**: 结构化日志

### 插件依赖
- **requests**: HTTP请求（GPS插件）
- **geopy**: 地理编码（GPS插件）
- **googletrans**: 翻译功能（Google翻译插件）

## 🐛 常见问题

### Q: 提示"未找到Python"错误
**A**: 请确保已安装Python 3.8+，并添加到系统PATH中。

### Q: 安装依赖包失败
**A**: 尝试以下解决方案：
1. 更新pip: `pip install --upgrade pip`
2. 使用国内镜像: `pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/`
3. 检查网络连接

### Q: 程序启动后界面显示异常
**A**: 可能是PyQt6版本问题，尝试：
```bash
pip uninstall PyQt6 PyQt6-Qt6 PyQt6-sip
pip install PyQt6==6.4.0
```

### Q: GPS位置查询功能不工作
**A**: 检查网络连接，GPS插件需要访问在线地图服务。

### Q: 翻译功能不工作
**A**: Google翻译插件需要网络连接，如果无法访问Google服务，可以尝试使用VPN。

## 📞 技术支持

如果遇到其他问题，请：

1. 查看[常见问题](docs/faq.md)
2. 在GitHub Issues中提交问题
3. 发送邮件到：support@photo666.com

## 🔄 更新说明

### 从旧版本升级
1. 备份您的数据文件（data目录）
2. 下载新版本
3. 解压并运行新版本
4. 程序会自动迁移数据

### 数据迁移
Photo666会自动处理数据迁移，您的照片、相册、标签等数据会被保留。

---

**Photo666 v0.1.0** - 让照片管理更简单、更智能！ 