import subprocess

def check_permissions():
    print("🕵️‍♂️ 正在测试读取权限...")

    script = '''
    tell application "System Events"
        tell process "WeChat"
            set frontmost to true
            if (count of windows) > 0 then
                return "✅ 成功读取！当前窗口标题: [" & name of front window & "]"
            else
                return "❌ 失败: 无法读取窗口 (System Events 认为无窗口)"
            end if
        end tell
    end tell
    '''

    p = subprocess.Popen(['osascript', '-'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    stdout, stderr = p.communicate(script)
    print(stdout.strip())
    if stderr: print(f"错误详情: {stderr}")

if __name__ == "__main__":
    check_permissions()
