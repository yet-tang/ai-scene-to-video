# 自定义字体管理

本目录用于管理项目中使用的自定义字体，这些字体将被打包到 Docker 容器中供视频渲染使用。

## 当前内置字体

### 1. 阿里巴巴普惠体 (AlibabaPuHuiTi-3-75-SemiBold)
- **文件**: `AlibabaPuHuiTi-3-75-SemiBold.ttf`
- **适用场景**: 房产视频字幕、标题、片头片尾
- **特点**: 现代、简洁、易读，适合中文显示
- **配置Key**: `alibaba-puhuiti-semibold`

## 如何添加新字体

### 步骤 1: 准备字体文件

将字体文件（`.ttf` 或 `.otf` 格式）放到本目录：

```bash
# 示例
cp /path/to/your/新字体.ttf assets/fonts/
```

**字体要求**：
- 格式：TrueType (`.ttf`) 或 OpenType (`.otf`)
- 编码：支持中文字符（Unicode）
- 大小：建议单个字体文件 < 20MB
- 授权：确保拥有商用授权

### 步骤 2: 注册字体到配置

编辑 `engine/config.py`，在 `AVAILABLE_FONTS` 字典中添加新字体：

```python
AVAILABLE_FONTS = {
    "noto-sans-bold": "Noto-Sans-CJK-SC-Bold",
    "alibaba-puhuiti-semibold": "AlibabaPuHuiTi-3-75-SemiBold",
    "your-font-key": "YourFontName",  # 添加这一行
}
```

**注意**：
- `your-font-key`: 自定义的配置键（小写、用连字符分隔）
- `YourFontName`: 字体的 Family Name（通过 `fc-list` 查看）

### 步骤 3: 重新构建镜像

```bash
# 本地测试
docker compose -f docker-compose.coolify.yaml build engine

# 或者推送代码，等待 GitHub Actions 自动构建
git add assets/fonts/
git commit -m "Add new custom font"
git push
```

### 步骤 4: 使用新字体

在 Coolify 或 `.env` 中配置：

```bash
# 方式 1: 使用字体 Key（推荐）
SUBTITLE_FONT_KEY=your-font-key

# 方式 2: 直接指定字体名称
SUBTITLE_FONT=YourFontName
```

## 字体验证

### 本地验证（需要 Docker 运行）

```bash
# 进入容器
docker exec -it <engine_container_id> bash

# 列出所有可用字体
fc-list | grep -i "your-font-name"

# 或使用 Python 工具
docker exec -it <engine_container_id> python -c "
from font_manager import FontManager
print(FontManager.list_available_fonts())
"
```

### 查看字体状态日志

启动 Engine Worker 时会自动打印字体状态：

```
=== Font Manager Status ===
Custom fonts directory: /app/assets/fonts
Custom font files found: 1
  - AlibabaPuHuiTi-3-75-SemiBold.ttf -> /app/assets/fonts/AlibabaPuHuiTi-3-75-SemiBold.ttf
Total system fonts available: 156
Configured font 'AlibabaPuHuiTi-3-75-SemiBold': ✓ Available
=========================
```

## 字体管理 API

项目提供了 `font_manager.py` 模块用于字体管理：

```python
from font_manager import FontManager

# 列出所有可用字体
fonts = FontManager.list_available_fonts()

# 搜索特定字体
alibaba_fonts = FontManager.search_font('alibaba')

# 验证字体是否可用
is_valid = FontManager.validate_font('AlibabaPuHuiTi-3-75-SemiBold')

# 获取字体详细信息
info = FontManager.get_font_info('AlibabaPuHuiTi-3-75-SemiBold')

# 打印完整的字体状态
FontManager.log_font_status()
```

## 常见问题

### Q1: 字体无法显示中文

**原因**: 字体文件不包含中文字符集。

**解决**: 使用支持 CJK (中日韩) 字符的字体，如：
- Noto Sans CJK（系统自带）
- 思源黑体
- 阿里巴巴普惠体

### Q2: 字体文件过大导致镜像臃肿

**原因**: 完整字体包含所有语言和字重。

**解决**: 使用字体子集化工具裁剪：

```bash
# 安装 fonttools
pip install fonttools

# 生成中文子集
pyftsubset input.ttf \
  --output-file=output.ttf \
  --text-file=常用汉字.txt \
  --layout-features='*'
```

### Q3: 字体在 MoviePy 中渲染失败

**原因**: ImageMagick 权限策略或字体未注册。

**排查步骤**:
1. 检查 `/etc/ImageMagick-*/policy.xml` 配置
2. 运行 `fc-cache -f -v` 重建字体缓存
3. 确认字体在 `fc-list` 输出中存在

### Q4: 如何获取字体的 Family Name？

```bash
# 方式 1: 使用 fc-scan
fc-scan /app/assets/fonts/yourfont.ttf | grep family

# 方式 2: 使用 otfinfo (需要安装 lcdf-typetools)
otfinfo --family /app/assets/fonts/yourfont.ttf
```

## 推荐字体

### 中文字体

| 字体名称 | 特点 | 授权 | 适用场景 |
|---------|------|------|----------|
| 阿里巴巴普惠体 | 现代、简洁 | 免费商用 | 房产视频、企业宣传 |
| 思源黑体 | 清晰、规范 | 开源 (OFL) | 通用场景 |
| 思源宋体 | 传统、优雅 | 开源 (OFL) | 高端住宅、古典风格 |
| 站酷高端黑 | 时尚、粗壮 | 免费商用 | 标题、重点强调 |

### 英文字体

| 字体名称 | 特点 | 授权 | 适用场景 |
|---------|------|------|----------|
| Montserrat | 现代、几何 | 开源 (OFL) | 豪华公寓、现代设计 |
| Roboto | 清晰、中性 | 开源 (Apache) | 通用场景 |
| Playfair Display | 优雅、衬线 | 开源 (OFL) | 高端住宅、经典风格 |

## 版权声明

- 本项目使用的字体需确保拥有合法的商用授权
- 阿里巴巴普惠体：遵循《普惠体用户协议》，允许商用
- 建议在使用第三方字体前仔细阅读其授权协议

## 参考资源

- [Google Fonts](https://fonts.google.com/) - 大量开源字体
- [FontSquirrel](https://www.fontsquirrel.com/) - 免费商用字体
- [思源字体](https://github.com/adobe-fonts) - Adobe 开源字体家族
- [站酷字体](https://www.zcool.com.cn/special/zcoolfonts/) - 站酷免费字体
