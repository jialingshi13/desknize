# 桌面整理

一个简单的本机工具：打开后预览桌面根目录里的文件，按类型再按修改时间的年/月归类，确认后才移动。支持撤销上次整理。

双击打包好的 `desktop_organizer.exe` 即可使用，无需安装。

## 它会做什么

- 只处理**桌面根目录中的文件**，不把文件夹收进分类目录
- 按扩展名归入「图片 / 文档 / 表格 / 演示 / 视频 / 音乐 / 压缩包 / 安装包 / 代码 / 其他」
- 每个文件分类下再按 `年/月` 分层，例如 `图片/2026/09/vacation.jpg`
- **快捷方式和文件夹都留在桌面**，整理后先排快捷方式，再排文件夹（回收站等系统图标排在最后）
- 窗口为竖向长方形，点「开始整理」即可；底部可按文件名检索
- 第一次运行会在桌面创建带刷子图标的「桌面整理」快捷方式
- 「检索」页可按文件名、后缀和修改日期筛选整个桌面（含已整理的子文件夹）
- 预览时可取消勾选个别文件或整组分类
- 目标已有同名文件时自动改成 `照片 (2).jpg`，不会覆盖
- 不移动文件夹、隐藏文件、`desktop.ini` 以及本程序自己的 exe

## 运行（开发）

需要 Python 3.10+ 和 tkinter（Windows 官方安装包已自带；Debian/Ubuntu 需安装 `python3-tk`）。

```bash
python run.py
```

或安装后再启动：

```bash
pip install -e .
python -m desktop_organizer
```

## 测试

```bash
pip install -e ".[dev]"
pytest
```

测试使用临时目录，不会改动你的真实桌面。

## 一键安装并打包（Windows）

电脑上需要先装一次 [Python 3.10+](https://www.python.org/downloads/)（勾选 **Add python.exe to PATH**，用 python.org 官方安装包）。

然后在本项目文件夹里**双击** `InstallAndBuild.bat`。

脚本会自动安装 PyInstaller 并生成：

- `dist\desktop_organizer.exe`
- 项目根目录的 `桌面整理.exe`

之后双击 exe 即可，不必再开 Python。日常开发可双击 `Run.bat`。

### 方式二：手动命令

打开命令提示符或 PowerShell，进入项目根目录：

```bat
cd C:\desktop-organizer
python -m pip install -U pip pyinstaller
python -m PyInstaller --noconfirm packaging\desktop_organizer.spec
```

若提示找不到 `python`，改用：

```bat
py -3 -m pip install -U pip pyinstaller
py -3 -m PyInstaller --noconfirm packaging\desktop_organizer.spec
```

### 结果

生成的单文件在 `dist\desktop_organizer.exe`。拷到任意位置（包括桌面）双击即可，无需再装 Python。程序会跳过自己的 exe，不会把它归类走。

### 常见问题

- 提示找不到 `python`：重新安装 Python 并勾选 PATH，或改用上面的 `py -3` 命令。
- 杀毒软件误报：PyInstaller 单文件常见现象，把 exe 加入信任即可。
- 想重新打包：再运行一次 `packaging\build.bat`（会先删掉旧的 `build` 和 `dist`）。

## 撤销

整理成功后，窗口里的「撤销上次整理」会把上一批文件移回桌面原处，并尽量删掉当时新建的空分类文件夹。撤销记录保存在用户目录下的 `.desktop_organizer/last_undo.json`。
