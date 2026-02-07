import subprocess

def run_applescript(script):
    p = subprocess.Popen(['osascript', '-'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    stdout, stderr = p.communicate(script)
    return stdout.strip(), stderr.strip()

def inspect_ui():
    print("🕵️‍♂️ 正在深度扫描微信 UI 结构...")

    script = '''
    tell application "System Events"
        tell process "WeChat"
            set frontmost to true
            if not (exists front window) then return "无窗口"

            set win to front window

            -- 获取第一层级的所有元素类型
            set level1 to every UI element of win

            set resultLog to ""

            repeat with item1 in level1
                set itemRole to role of item1
                set itemDesc to description of item1
                set resultLog to resultLog & "\nLayer 1: " & itemRole & " | " & itemDesc

                -- 如果是分割组，尝试深入一层
                if itemRole is "AXSplitGroup" then
                    set level2 to every UI element of item1
                    repeat with item2 in level2
                        set resultLog to resultLog & "\n    Layer 2: " & role of item2 & " | " & description of item2

                        -- 再深入一层（通常输入框在第三层）
                        if role of item2 is "AXSplitGroup" then
                             set level3 to every UI element of item2
                             repeat with item3 in level3
                                set resultLog to resultLog & "\n        Layer 3: " & role of item3 & " | " & description of item3

                                -- 尝试找 Text Area
                                if role of item3 is "AXTextArea" then
                                    set resultLog to resultLog & " [TARGET FOUND!]"
                                end if
                             end repeat
                        end if
                    end repeat
                end if
            end repeat

            return resultLog
        end tell
    end tell
    '''

    stdout, stderr = run_applescript(script)
    print(stdout)
    if stderr:
        print(f"Error: {stderr}")

if __name__ == "__main__":
    inspect_ui()
