import subprocess
import time

def run_applescript(script):
    p = subprocess.Popen(['osascript', '-'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    stdout, stderr = p.communicate(script)
    return stdout.strip(), stderr.strip()

def find_input():
    print("🕵️‍♂️ 正在全盘搜索微信输入框...")

    script = '''
    tell application "System Events"
        tell application "WeChat" to activate
        delay 0.5

        tell process "WeChat"
            set frontmost to true
            delay 0.5

            -- 方法 1: 直接获取所有 text area (最快)
            try
                set allInputs to every text area of every window
                set inputCount to count of allInputs

                if inputCount > 0 then
                    log "✅ 发现 " & inputCount & " 个输入框"

                    -- 通常聊天输入框是最后一个或者拥有特定属性
                    -- 我们尝试给每一个都写点字，看看哪个是正确的
                    repeat with inputField in allInputs
                        try
                            -- 尝试获取焦点
                            set focused of inputField to true
                            delay 0.2
                            -- 尝试设置值 (比粘贴更稳)
                            set value of inputField to "✅ 成功定位到此输入框"
                            return "✅ 已尝试向输入框写入测试内容，请检查微信窗口。"
                        on error
                            -- 忽略只读区域的错误
                        end try
                    end repeat
                else
                    return "⚠️ 未直接发现 Text Area，尝试深层搜索..."
                end if
            on error
                return "❌ 搜索过程出错"
            end try

            -- 方法 2: 如果上面没找到，尝试递归搜索 Splitter Group (针对复杂布局)
            try
                set targetWindow to front window
                set allSplitters to every splitter group of targetWindow

                repeat with sp in allSplitters
                    try
                         set textAreas to every text area of sp
                         if (count of textAreas) > 0 then
                            set inputField to item 1 of textAreas
                            set focused of inputField to true
                            set value of inputField to "✅ 深度扫描定位成功"
                            return "✅ 深度扫描发现输入框并已写入。"
                         end if

                         -- 再深一层
                         set subSplitters to every splitter group of sp
                         repeat with subSp in subSplitters
                            set subTextAreas to every text area of subSp
                            if (count of subTextAreas) > 0 then
                                set inputField to item 1 of subTextAreas
                                set focused of inputField to true
                                set value of inputField to "✅ 双重深度定位成功"
                                return "✅ 双重深度扫描发现输入框并已写入。"
                            end if
                         end repeat
                    end try
                end repeat
            on error
               return "❌ 深度搜索也未找到"
            end try

            return "⚠️ 扫描完成，未找到可写的输入框。"
        end tell
    end tell
    '''

    stdout, stderr = run_applescript(script)
    print(stdout)
    if stderr:
        print(f"Error: {stderr}")

if __name__ == "__main__":
    find_input()
