"""
配置文件加载器。
    
从 config.yaml 读取 YAML 格式的配置项，并通过 Python 的 setattr
将每个配置项动态绑定为实例属性。这样可以用 config.mode,
config.targetLocation 等方式直接访问配置值。
"""
import yaml

class Config:
    """YAML 配置加载器，将配置项动态绑定为实例属性。"""

    def __init__(self):
        # 使用 utf-8 编码打开 YAML 配置文件
        with open("config.yaml", 'r') as f:
            # yaml.safe_load 安全解析（不执行任意 Python 代码）
            config = yaml.safe_load(f)
        # 将每个 YAML 键值对设置为实例属性
        # 例如 YAML 中 mode: "static" → config.mode = "static"
        for i in config:
            setattr(self, i, config[i])


# 模块级单例：导入 config 模块时自动加载配置
# 使用方式: from config import config; config.mode
config = Config()
