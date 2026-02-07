import subprocess
import time
import sys
import os

def run_applescript(script):
    """运行 AppleScript"""
    p = subprocess.Popen(['osascript', '-'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    stdout, stderr = p.communicate(script)
    if p.returncode != 0:
        print(f"执行 AppleScript 错误: {stderr}")
        return False
    return True

def send_wechat_message(target_name, message_content):
    # Step 1: 准备临时文件
    target_file = "/tmp/wechat_target.txt"
    msg_file = "/tmp/wechat_msg.txt"

    with open(target_file, "w", encoding="utf-8") as f:
        f.write(target_name)

    with open(msg_file, "w", encoding="utf-8") as f:
        f.write(message_content)

    print("1. 临时文件已准备就绪")

    # Step 2: 构建 AppleScript
    # 使用“坐标点击法”强制激活输入框
    full_script = f'''
    -- 定义读取文件的函数
    on copyFileContent(filePath)
        do shell script "cat " & quoted form of filePath & " | pbcopy"
    end copyFileContent

    tell application "System Events"
        -- 1. 复制联系人姓名
        my copyFileContent("{target_file}")
        delay 0.5

        -- 2. 激活微信并搜索
        tell application "WeChat" to activate
        delay 0.5
        tell process "WeChat"
            set frontmost to true
        end tell

        -- Cmd+F 搜索
        keystroke "f" using {{command down}}
        delay 0.8

        -- Cmd+V 粘贴姓名
        keystroke "v" using {{command down}}
        delay 1.5

        -- 回车进入会话
        key code 36
        delay 1.5

        -- 🔧 关键修复：查找输入框并模拟鼠标点击
        tell process "WeChat"
            try
                -- 寻找输入框 (Text Area)
                set allInputs to every text area of every window
                if (count of allInputs) > 0 then
                    set targetInput to item 1 of allInputs

                    -- 获取输入框的位置和大小
                    set {{x, y}} to position of targetInput
                    set {{w, h}} to size of targetInput

                    -- 计算中心点坐标
                    set clickX to x + (w / 2)
                    set clickY to y + (h / 2)

                    -- 🖱️ 模拟鼠标点击输入框中心
                    click at {{clickX, clickY}}
                    delay 0.5
                end if
            on error
                -- 如果找不到，尝试备用方案：再次激活窗口
            end try
        end tell

        -- 3. 复制消息内容
        my copyFileContent("{msg_file}")
        delay 0.8

        -- 4. 粘贴并发送
        keystroke "v" using {{command down}}
        delay 1.0
        key code 36
    end tell
    '''


    print("2. 开始执行全自动化脚本 (请保持双手离开键鼠)...")
    run_applescript(full_script)
    print("✅ 全流程指令已发送完毕")

if __name__ == "__main__":
    # 配置
    file_path = "/Users/zhanggongqing/project/孵化项目/cloudwork/data/福满亲家宴_博山菜_经营日报_20260205.md"
    target_person = "刘琪"

    if not os.path.exists(file_path):
        print(f"❌ 错误: 找不到文件 {file_path}")
        sys.exit(1)

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        print(f"📄 读取日报文件成功，准备发送给 [{target_person}]")
        send_wechat_message(target_person, content)

    except Exception as e:
        print(f"❌ 发生异常: {e}")
