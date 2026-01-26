# Python 3.9 类型注解兼容性

**提取日期**: 2026-01-25
**来源**: cloudwork 项目
**标签**: python, typing, 兼容性

## 问题
VPS 运行 Python 3.9，部分类型注解语法不兼容。

## 解决方案
使用 typing 模块的兼容写法:
- `Optional[str]` 而不是 `str | None`
- `Tuple[str, str]` 而不是 `tuple[str, str]`

## 适用场景
当目标环境是 Python 3.9 或更早版本时。