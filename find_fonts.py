import tkinter
from tkinter import font

try:
    root = tkinter.Tk()
    print("--- 利用可能なフォントファミリー ---")
    # Get a list of all font families
    font_families = sorted(font.families())
    
    # Filter for fonts that might support Japanese
    jp_fonts = [f for f in font_families if any(keyword in f.lower() for keyword in ['gothic', 'mincho', 'ipa', 'noto', 'takao', 'vl', 'jp'])]
    
    if jp_fonts:
        print("\n[日本語フォントの候補]")
        for f in jp_fonts:
            print(f)
    
    print("\n[すべてのフォント]")
    for f in font_families:
        print(f)

except Exception as e:
    print(f"エラーが発生しました: {e}")

finally:
    if 'root' in locals() and root:
        root.destroy()
