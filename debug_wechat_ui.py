import subprocess
import time

def run_applescript(script):
    p = subprocess.Popen(['osascript', '-'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    stdout, stderr = p.communicate(script)
    return stdout.strip(), stderr.strip()

def diagnose_wechat_ui():
    print("🕵️‍♂️ 开始诊断微信 UI 结构...")
    print("请保持微信运行，脚本将尝试寻找并聚焦输入框。")

    # AppleScript 脚本：尝试遍历并寻找输入框
    # 注意：微信的 UI 结构比较复杂，通常输入框位于 splitter group 的深层结构中
    script = '''
    tell application "System Events"
        tell application "WeChat" to activate
        delay 0.5

        tell process "WeChat"
            set frontmost to true
            delay 0.5

            if not (exists front window) then
                return "❌ 错误：未检测到微信窗口，请确保微信已登录并打开主界面。"
            end if

            set mainWin to front window
            log "窗口标题: " & (name of mainWin)

            -- 策略 1: 尝试常见的标准路径 (微信 Mac 版常见结构)
            -- 通常结构：window -> splitter group -> splitter group -> text area
            try
                -- 寻找所有可能的 text area (输入框通常是 text area)
                -- 注意：entire contents 可能会比较慢，我们限制在 splitter group 中查找
                set inputField to value of attribute "AXFocusedUIElement"

                -- 尝试定位输入框（通常是多行文本域）
                -- 我们尝试在窗口的子元素中寻找 text area
                set allTextAreas to {}

                try
                    -- 深入一层寻找
                    set allTextAreas to every text area of splitter group 1 of splitter group 1 of mainWin
                on error
                    try
                         set allTextAreas to every text area of splitter group 1 of mainWin
                    end try
                end try

                if (count of allTextAreas) > 0 then
                    set targetInput to item 1 of allTextAreas

                    -- 动作：强制聚焦
                    set focused of targetInput to true

                    -- 验证：输入文字
                    delay 0.2
                    keystroke "✅ 已定位到输入框"

                    return "✅ 成功：找到 Text Area 并已尝试输入测试文字。"
                else
                    return "⚠️ 警告：在常见路径下未找到 Text Area。可能是界面结构已变更。"
                end if

            on error errMsg
                return "❌ 诊断过程出错: " & errMsg
            end try
        end tell
    end tell
    '''

    stdout, stderr = run_applescript(script)
    print(f"\n📋 诊断结果:\n{stdout}")
    if stderr:
        print(f"🔴 错误信息: {stderr}")

if __name__ == "__main__":
    diagnose_wechat_ui()
