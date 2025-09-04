# 学習時間管理アプリケーション
# 機能：タイマー、学習目標管理、試験目標管理、模試結果管理、学習履歴管理

# 必要なライブラリのインポート
import tkinter as tk
from tkinter import ttk, messagebox
import tkinter.font as font
import platform
from datetime import datetime, timedelta
from visualize import show_analysis_window  # グラフ表示機能
import database  # データベース操作機能
import report_generator  # レポート生成機能
import pandas as pd  # データ分析用

# カレンダー機能の利用可能性をチェック
try:
    from tkcalendar import DateEntry
    CALENDAR_AVAILABLE = True  # カレンダーウィジェットが利用可能
except ImportError:
    CALENDAR_AVAILABLE = False  # カレンダーウィジェットが利用不可

class StudyTimerApp:
    """学習時間管理アプリケーションのメインクラス"""
    
    def __init__(self, root):
        """アプリケーションの初期化"""
        self.root = root
        self.root.title("Study Time Logger")
        self.root.geometry("1000x800")  # 全UI要素が表示されるサイズに設定

        # データベースの初期化
        database.init_db()

        # タイマーの状態管理変数
        self.timer_running = False      # タイマーが動作中かどうか
        self.is_paused = False          # タイマーが一時停止中かどうか
        self.start_time = None          # タイマー開始時刻
        self.elapsed_time = timedelta(0) # 経過時間
        self.after_id = None            # タイマー更新用ID

        # ポモドーロタイマーの状態管理
        self.pomodoro_mode = tk.BooleanVar()  # ポモドーロモードのオン/オフ
        self.pomodoro_state = None            # 現在の状態（作業中/休憩中）
        self.pomodoro_cycles = 0              # 完了したポモドーロサイクル数

        # UI初期設定とデータ読み込み
        self.setup_styles()              # スタイル設定
        self.setup_ui()                  # UI構築
        self.load_mock_exams()           # 模試データ読み込み
        self.load_exam_goals()           # 試験目標データ読み込み
        self.load_study_goals()          # 学習目標データ読み込み
        self.load_study_history()        # 学習履歴データ読み込み
        self.update_progress_display()   # 進捗表示を更新

    def setup_styles(self):
        """アプリケーションの見た目・スタイルを設定"""
        # OS別にフォントファミリーを選択
        os_name = platform.system()
        if os_name == "Linux":
            default_font_family = "Ubuntu"
        elif os_name == "Windows":
            default_font_family = "Segoe UI"
        else:
            default_font_family = "San Francisco"  # macOS
        
        # ttkスタイルの設定
        style = ttk.Style()
        style.theme_use('clam')  # 統一感のあるテーマを使用
        
        # 各UI要素のフォント設定
        style.configure('.', font=(default_font_family, 12))                    # 基本フォント
        style.configure('TButton', font=(default_font_family, 12, 'bold'))      # ボタン用フォント
        style.configure('TLabel', font=(default_font_family, 12))               # ラベル用フォント
        style.configure('Status.TLabel', font=(default_font_family, 14, 'italic'))  # ステータス表示用
        style.configure('Timer.TLabel', font=(default_font_family, 48))         # タイマー表示用（大きめ）
        
        # 進捗バーのカスタムスタイル設定
        style.layout("Goal.TProgressbar",
                     [('Horizontal.Progressbar.trough',
                       {'children': [('Horizontal.Progressbar.pbar',
                                      {'side': 'left', 'sticky': 'ns'})],
                        'sticky': 'nswe'})])
        style.configure("Goal.TProgressbar", thickness=20, background='green')  # 緑色の太い進捗バー
        
        # テーブルヘッダーのフォント設定
        style.configure("Treeview.Heading", font=(default_font_family, 12, 'bold'))
        
        # 目標達成状況に応じた色分け
        style.configure("Achieved.TLabel", foreground="green")     # 達成済み：緑
        style.configure("NotAchieved.TLabel", foreground="red")    # 未達成：赤

    def setup_ui(self):
        """メインUIの構築（タブ形式でそれぞれの機能を整理）"""
        # メインのタブコンテナを作成
        notebook = ttk.Notebook(self.root)
        notebook.pack(pady=10, padx=10, fill="both", expand=True)

        # 各機能用のタブフレームを作成
        timer_tab = ttk.Frame(notebook)          # タイマー機能
        study_history_tab = ttk.Frame(notebook)  # 学習履歴管理
        study_goals_tab = ttk.Frame(notebook)    # 学習目標管理
        exam_goals_tab = ttk.Frame(notebook)     # 試験目標管理
        mock_exam_tab = ttk.Frame(notebook)      # 模試結果管理

        # タブにフレームを追加
        notebook.add(timer_tab, text='Timer')           # タイマー
        notebook.add(study_history_tab, text='Study History')  # 学習履歴
        notebook.add(study_goals_tab, text='Study Goals')      # 学習目標
        notebook.add(exam_goals_tab, text='Exam Goals')        # 試験目標
        notebook.add(mock_exam_tab, text='Mock Exams')         # 模試結果

        # 各タブのUI構築メソッドを呼び出し
        self.setup_timer_tab(timer_tab)           # タイマー画面の構築
        self.setup_study_history_tab(study_history_tab)  # 学習履歴画面の構築
        self.setup_study_goals_tab(study_goals_tab)      # 学習目標画面の構築
        self.setup_exam_goals_tab(exam_goals_tab)        # 試験目標画面の構築
        self.setup_mock_exam_tab(mock_exam_tab)          # 模試結果画面の構築

    def setup_timer_tab(self, parent_tab):
        """タイマータブのUI構築（メイン機能）"""
        # ポモドーロモードの設定エリア
        pomodoro_frame = ttk.Frame(parent_tab)
        pomodoro_frame.pack(pady=5)
        
        # ポモドーロモードのチェックボックス
        self.pomodoro_check = ttk.Checkbutton(pomodoro_frame, text="Pomodoro Mode", 
                                             variable=self.pomodoro_mode, 
                                             command=self.toggle_pomodoro_mode)
        self.pomodoro_check.pack(side="left", padx=5)
        
        # ポモドーロの現在状態表示ラベル（作業中/休憩中など）
        self.pomodoro_status_label = ttk.Label(pomodoro_frame, text="", style="Status.TLabel")
        self.pomodoro_status_label.pack(side="left", padx=5)

        # 日次目標の進捗表示エリア
        self.goal_frame = ttk.LabelFrame(parent_tab, text="Daily Goal Progress", padding=10)
        self.goal_frame.pack(pady=5, padx=10, fill="x")
        
        # 目標進捗のテキスト表示
        self.goal_progress_label = ttk.Label(self.goal_frame, text="No goal set.")
        self.goal_progress_label.pack()
        
        # 目標達成率を視覚的に表示する進捗バー
        self.goal_progressbar = ttk.Progressbar(self.goal_frame, orient="horizontal", 
                                               length=300, mode="determinate", 
                                               style="Goal.TProgressbar")
        self.goal_progressbar.pack(pady=5)

        # 学習科目の選択メニュー
        self.subjects = ["Chemistry", "English", "Information", "Japanese", "Math", "Physics", "Social Studies"]
        self.selected_subject = tk.StringVar(value=self.subjects[0])  # デフォルトは最初の科目
        
        # 科目変更時に進捗表示を更新するトリガーを設定
        self.selected_subject.trace_add("write", self.on_subject_change)
        
        # 科目選択用のプルダウンメニュー
        self.subject_menu = ttk.OptionMenu(
            parent_tab, self.selected_subject, self.subjects[0], *self.subjects)
        self.subject_menu.pack(pady=5)

        # タイマーの時間表示ラベル（大きく表示）
        self.timer_label = ttk.Label(
            parent_tab, text="00:00:00", style='Timer.TLabel', anchor="center")
        self.timer_label.pack(pady=10, fill="x")

        # タイマー操作ボタン用のフレーム
        self.button_frame = ttk.Frame(parent_tab)
        self.button_frame.pack(pady=5)
        
        # 分析・レポートボタン用のフレーム
        self.bottom_button_frame = ttk.Frame(parent_tab)
        self.bottom_button_frame.pack(pady=5)

        # タイマー操作用ボタンの作成
        self.start_button = ttk.Button(
            self.button_frame, text="Start", command=self.start_timer, style='TButton')  # タイマー開始
        self.pause_button = ttk.Button(
            self.button_frame, text="Pause", command=self.pause_timer, style='TButton')  # 一時停止
        self.resume_button = ttk.Button(
            self.button_frame, text="Resume", command=self.resume_timer, style='TButton')  # 再開
        self.stop_button = ttk.Button(
            self.button_frame, text="Stop", command=self.stop_and_reset_all, style='TButton')  # 停止
        self.save_button = ttk.Button(
            self.button_frame, text="Save", command=self.save_and_reset, style='TButton')  # 保存
        self.discard_button = ttk.Button(
            self.button_frame, text="Discard", command=self.discard_and_reset, style='TButton')  # 破棄
        
        # 分析・レポート機能用ボタン
        self.analysis_button = ttk.Button(
            self.bottom_button_frame, text="Analysis", 
            command=self.open_analysis_window, style='TButton')  # グラフ分析
        self.report_button = ttk.Button(
            self.bottom_button_frame, text="Generate Report", 
            command=self.generate_report_callback, style='TButton')  # レポート生成
        
        # UIを初期状態にリセット
        self.reset_ui()

    def setup_study_goals_tab(self, parent_tab):
        """学習目標管理タブのUI構築（日次・週次の学習時間目標を設定・管理）"""
        # メインフレーム（縦型レイアウト）
        main_frame = ttk.Frame(parent_tab)
        main_frame.pack(fill="both", expand=True)

        # 学習目標設定用の入力フォームエリア
        input_frame = ttk.LabelFrame(main_frame, text="Set Study Time Goal", padding=10)
        input_frame.pack(pady=10, padx=10, fill="x")
        input_frame.columnconfigure(1, weight=1)  # 2列目を伸縮可能に設定

        # 目標の種類選択（日次または週次）
        self.study_goal_type = tk.StringVar(value="daily")  # デフォルトは日次目標
        ttk.Label(input_frame, text="Goal Type:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        
        # ラジオボタン用のサブフレーム
        goal_type_frame = ttk.Frame(input_frame)
        goal_type_frame.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        
        # 日次目標用ラジオボタン
        daily_radio = ttk.Radiobutton(goal_type_frame, text="Daily", variable=self.study_goal_type, value="daily")
        daily_radio.pack(side="left", padx=(0, 10))
        
        # 週次目標用ラジオボタン
        weekly_radio = ttk.Radiobutton(goal_type_frame, text="Weekly", variable=self.study_goal_type, value="weekly")
        weekly_radio.pack(side="left")

        # 対象科目の選択（「全科目」または個別科目）
        all_subjects = ["All"] + self.subjects  # 「全科目」オプションを追加
        self.study_goal_subject = tk.StringVar(value=all_subjects[0])  # デフォルトは「全科目」
        ttk.Label(input_frame, text="Subject:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        
        # 科目選択用プルダウンメニュー
        subject_menu = ttk.OptionMenu(input_frame, self.study_goal_subject, all_subjects[0], *all_subjects)
        subject_menu.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        # 目標時間（分単位）の入力
        ttk.Label(input_frame, text="Target (minutes):").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.study_goal_minutes_entry = ttk.Entry(input_frame)
        self.study_goal_minutes_entry.grid(row=2, column=1, padx=5, pady=5, sticky="ew")

        # メモ・コメント欄
        ttk.Label(input_frame, text="Notes:").grid(row=3, column=0, padx=5, pady=5, sticky="w")
        self.study_goal_notes_entry = ttk.Entry(input_frame)
        self.study_goal_notes_entry.grid(row=3, column=1, padx=5, pady=5, sticky="ew")

        # 目標設定実行ボタン
        save_button = ttk.Button(input_frame, text="Set Goal", command=self.set_study_goal_callback)
        save_button.grid(row=4, column=0, columnspan=2, pady=10)

        # 設定済み学習目標の一覧表示エリア
        tree_frame = ttk.LabelFrame(main_frame, text="Current Study Goals", padding=10)
        tree_frame.pack(pady=(0, 10), padx=10, fill="both", expand=True)

        # 学習目標一覧用のテーブルウィジェット
        self.study_goals_tree = ttk.Treeview(tree_frame, 
                                           columns=("ID", "Type", "Subject", "Target", "Notes"), 
                                           show="headings")
        
        # テーブルのカラム設定
        self.study_goals_tree.heading("ID", text="ID")
        self.study_goals_tree.column("ID", width=0, stretch=tk.NO)  # IDは非表示
        self.study_goals_tree.heading("Type", text="Type")          # 目標タイプ（日次/週次）
        self.study_goals_tree.heading("Subject", text="Subject")    # 対象科目
        self.study_goals_tree.heading("Target", text="Target (mins)")  # 目標時間
        self.study_goals_tree.heading("Notes", text="Notes")       # メモ
        self.study_goals_tree.column("Notes", width=250)
        
        # テーブル用スクロールバー
        tree_scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", 
                                      command=self.study_goals_tree.yview)
        self.study_goals_tree.configure(yscroll=tree_scrollbar.set)
        tree_scrollbar.pack(side="right", fill="y")
        self.study_goals_tree.pack(side="left", fill="both", expand=True)

        # 目標操作用ボタンエリア
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(pady=(0, 10), padx=10, fill="x")
        
        # 選択した目標を削除するボタン
        delete_button = ttk.Button(buttons_frame, text="Delete Goal", 
                                  command=self.delete_study_goal_callback)
        delete_button.pack(side="right", padx=5)

    def setup_exam_goals_tab(self, parent_tab):
        """試験目標管理タブのUI構築（入試・模試などの目標設定・達成状況管理）"""
        # メインフレーム（縦型レイアウト）
        main_frame = ttk.Frame(parent_tab)
        main_frame.pack(fill="both", expand=True)

        # 新しい試験目標設定用の入力フォームエリア
        input_frame = ttk.LabelFrame(main_frame, text="Set New Exam Goal", padding=10)
        input_frame.pack(pady=10, padx=10, fill="x")
        input_frame.columnconfigure(1, weight=1)  # 2列目を伸縮可能に設定

        # 試験科目の選択
        ttk.Label(input_frame, text="Subject:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.goal_subject_var = tk.StringVar(value=self.subjects[0])  # デフォルト科目
        self.goal_subject_menu = ttk.OptionMenu(input_frame, self.goal_subject_var, 
                                               self.subjects[0], *self.subjects)
        self.goal_subject_menu.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        # 試験名の入力（例：「第1回模試」「本番入試」など）
        ttk.Label(input_frame, text="Exam Name:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.goal_exam_name_entry = ttk.Entry(input_frame)
        self.goal_exam_name_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        # 試験日程の入力（カレンダー機能付き）
        ttk.Label(input_frame, text="Exam Date:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        
        # カレンダーライブラリが利用可能な場合はカレンツーウィジェットを使用
        if CALENDAR_AVAILABLE:
            self.goal_exam_date_entry = DateEntry(input_frame, width=12, background='darkblue',
                                                 foreground='white', borderwidth=2, 
                                                 date_pattern='yyyy-mm-dd')
        else:
            # カランダーなしの場合は通常のテキストボックス（今日がデフォルト）
            self.goal_exam_date_entry = ttk.Entry(input_frame)
            self.goal_exam_date_entry.insert(0, datetime.now().strftime('%Y-%m-%d'))
        self.goal_exam_date_entry.grid(row=2, column=1, padx=5, pady=5, sticky="ew")

        # 目標点数の入力
        ttk.Label(input_frame, text="Target Score:").grid(row=3, column=0, padx=5, pady=5, sticky="w")
        self.goal_target_score_entry = ttk.Entry(input_frame)
        self.goal_target_score_entry.grid(row=3, column=1, padx=5, pady=5, sticky="ew")

        # メモ・コメント欄（複数行入力可能）
        ttk.Label(input_frame, text="Notes:").grid(row=4, column=0, padx=5, pady=5, sticky="nw")
        self.goal_notes_text = tk.Text(input_frame, height=3, width=40)  # 3行のテキストエリア
        self.goal_notes_text.grid(row=4, column=1, padx=5, pady=5, sticky="ew")

        # 目標保存ボタン
        save_button = ttk.Button(input_frame, text="Save Goal", command=self.add_exam_goal_callback)
        save_button.grid(row=5, column=0, columnspan=2, pady=10)

        # 設定済み試験目標の一覧表示エリア
        tree_frame = ttk.LabelFrame(main_frame, text="Active Goals", padding=10)
        tree_frame.pack(pady=(0, 10), padx=10, fill="both", expand=True)

        # 試験目標一覧用のテーブルウィジェット
        self.goal_tree = ttk.Treeview(tree_frame, 
                                     columns=("ID", "Date", "Subject", "Exam Name", "Target", "Status", "Notes"), 
                                     show="headings")
        
        # テーブルのカラム設定
        self.goal_tree.heading("ID", text="ID")            # 内部ID（非表示）
        self.goal_tree.heading("Date", text="Date")        # 試験日
        self.goal_tree.heading("Subject", text="Subject")  # 科目
        self.goal_tree.heading("Exam Name", text="Exam Name")  # 試験名
        self.goal_tree.heading("Target", text="Target")    # 目標点数
        self.goal_tree.heading("Status", text="Status")    # 達成状況
        self.goal_tree.heading("Notes", text="Notes")      # メモ

        # カラム幅と配置の調整
        self.goal_tree.column("ID", width=30, stretch=tk.NO)         # IDは狭くして非表示
        self.goal_tree.column("Date", width=100)                    # 日付
        self.goal_tree.column("Subject", width=120)                 # 科目名
        self.goal_tree.column("Exam Name", width=150)               # 試験名
        self.goal_tree.column("Target", width=80, anchor="center")   # 目標点数（中央揃え）
        self.goal_tree.column("Status", width=100, anchor="center")  # 状態（中央揃え）
        self.goal_tree.column("Notes", width=150)                   # メモ

        # 達成状況による行の背景色分け
        self.goal_tree.tag_configure('Achieved', background='#d9ead3')      # 達成：緑系
        self.goal_tree.tag_configure('Not Achieved', background='#f4cccc')  # 未達成：赤系

        # テーブル用スクロールバー
        tree_scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.goal_tree.yview)
        self.goal_tree.configure(yscroll=tree_scrollbar.set)
        tree_scrollbar.pack(side="right", fill="y")
        self.goal_tree.pack(side="left", fill="both", expand=True)

        # 目標操作用ボタンエリア
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(pady=(0, 10), padx=10, fill="x")

        # 達成マークボタン（選択した目標を達成済みに変更）
        achieved_button = ttk.Button(buttons_frame, text="Mark as Achieved", 
                                    command=lambda: self.update_goal_status_callback("Achieved"))
        achieved_button.pack(side="left", padx=5)

        # 未達成マークボタン（選択した目標を未達成に変更）
        not_achieved_button = ttk.Button(buttons_frame, text="Mark as Not Achieved", 
                                        command=lambda: self.update_goal_status_callback("Not Achieved"))
        not_achieved_button.pack(side="left", padx=5)

        # 目標削除ボタン（選択した目標を完全に削除）
        delete_button = ttk.Button(buttons_frame, text="Delete Goal", 
                                  command=self.delete_exam_goal_callback)
        delete_button.pack(side="right", padx=5)

    def setup_mock_exam_tab(self, parent_tab):
        """模試結果管理タブのUI構築（模試の点数・偏差値などを記録・管理）"""
        # 模試結果入力用フォームエリア
        input_frame = ttk.LabelFrame(parent_tab, text="Enter Mock Exam Result", padding=10)
        input_frame.pack(pady=10, padx=10, fill="x")

        # グリッドレイアウトの設定（偶数列を伸縮可能に）
        input_frame.columnconfigure(1, weight=1)  # 2列目
        input_frame.columnconfigure(3, weight=1)  # 4列目

        # 模試実施日の入力（カレンダー機能付き）
        ttk.Label(input_frame, text="Date:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        
        # カレンダーライブラリが利用可能な場合はカレンダーウィジェットを使用
        if CALENDAR_AVAILABLE:
            self.mock_date_entry = DateEntry(input_frame, width=12, background='darkblue',
                                           foreground='white', borderwidth=2, 
                                           date_pattern='yyyy-mm-dd')
        else:
            # カレンダーなしの場合は通常のテキストボックス（今日がデフォルト）
            self.mock_date_entry = ttk.Entry(input_frame)
            self.mock_date_entry.insert(0, datetime.now().strftime('%Y-%m-%d'))
        self.mock_date_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        # 模試科目の選択
        ttk.Label(input_frame, text="Subject:").grid(row=0, column=2, padx=5, pady=5, sticky="w")
        self.mock_selected_subject = tk.StringVar(value=self.subjects[0])  # デフォルト科目
        self.mock_subject_menu = ttk.OptionMenu(input_frame, self.mock_selected_subject, 
                                               self.subjects[0], *self.subjects)
        self.mock_subject_menu.grid(row=0, column=3, padx=5, pady=5, sticky="ew")

        # 模試名の入力（例：「第1回全国模試」など）
        ttk.Label(input_frame, text="Exam Name:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.mock_exam_name_entry = ttk.Entry(input_frame)
        self.mock_exam_name_entry.grid(row=1, column=1, columnspan=3, padx=5, pady=5, sticky="ew")

        # 取得点数の入力
        ttk.Label(input_frame, text="Score:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.mock_score_entry = ttk.Entry(input_frame)
        self.mock_score_entry.grid(row=2, column=1, padx=5, pady=5, sticky="ew")

        # 満点（総得点）の入力
        ttk.Label(input_frame, text="Max Score:").grid(row=2, column=2, padx=5, pady=5, sticky="w")
        self.mock_max_score_entry = ttk.Entry(input_frame)
        self.mock_max_score_entry.grid(row=2, column=3, padx=5, pady=5, sticky="ew")

        # 偏差値の入力（模試の難易度や立ち位置を把握するため）
        ttk.Label(input_frame, text="Deviation:").grid(row=3, column=0, padx=5, pady=5, sticky="w")
        self.mock_deviation_entry = ttk.Entry(input_frame)
        self.mock_deviation_entry.grid(row=3, column=1, padx=5, pady=5, sticky="ew")

        # 模試結果保存ボタン
        save_button = ttk.Button(input_frame, text="Save Result", command=self.add_mock_exam_callback)
        save_button.grid(row=4, column=0, columnspan=4, pady=10)

        # 模試結果一覧表示用フレーム
        tree_frame = ttk.Frame(parent_tab)
        tree_frame.pack(pady=5, padx=10, fill="both", expand=True)
        
        # 模試結果一覧用のテーブルウィジェット
        self.mock_tree = ttk.Treeview(tree_frame, 
                                     columns=("ID", "Date", "Subject", "Exam Name", "Score", "Max Score", "Deviation"), 
                                     show="headings")
        
        # テーブルのカラム設定
        self.mock_tree.heading("ID", text="ID")              # 内部ID
        self.mock_tree.heading("Date", text="Date")          # 実施日
        self.mock_tree.heading("Subject", text="Subject")    # 科目
        self.mock_tree.heading("Exam Name", text="Exam Name")  # 模試名
        self.mock_tree.heading("Score", text="Score")        # 取得点数
        self.mock_tree.heading("Max Score", text="Max Score")  # 満点
        self.mock_tree.heading("Deviation", text="Deviation")  # 偏差値

        # カラム幅の調整
        self.mock_tree.column("ID", width=40, stretch=tk.NO)     # IDは狭く
        self.mock_tree.column("Date", width=100)                # 日付
        self.mock_tree.column("Subject", width=100)             # 科目
        self.mock_tree.column("Exam Name", width=150)           # 模試名
        self.mock_tree.column("Score", width=80)                # 点数
        self.mock_tree.column("Max Score", width=80)            # 満点
        self.mock_tree.column("Deviation", width=80)            # 偏差値

        # テーブル用スクロールバー
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.mock_tree.yview)
        self.mock_tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.mock_tree.pack(side="left", fill="both", expand=True)

        # 模試結果操作用ボタンエリア
        buttons_frame = ttk.Frame(parent_tab)
        buttons_frame.pack(pady=5, padx=10, fill="x")
        
        # 選択した模試結果を削除するボタン
        delete_button = ttk.Button(buttons_frame, text="Delete Result", 
                                  command=self.delete_mock_exam_callback)
        delete_button.pack(side="right", padx=5)

    def setup_study_history_tab(self, parent_tab):
        """学習履歴管理タブのUI構築（過去の学習記録を一覧表示・管理）"""
        # 学習履歴一覧表示用フレーム
        tree_frame = ttk.Frame(parent_tab)
        tree_frame.pack(pady=5, padx=10, fill="both", expand=True)

        # 学習履歴一覧用のテーブルウィジェット
        self.study_history_tree = ttk.Treeview(tree_frame, 
                                             columns=("ID", "Date", "Subject", "Minutes"), 
                                             show="headings")
        
        # テーブルのカラム設定
        self.study_history_tree.heading("ID", text="ID")            # 内部ID
        self.study_history_tree.column("ID", width=40, stretch=tk.NO)  # IDは狭くして非伸縮
        self.study_history_tree.heading("Date", text="Date")        # 学習日
        self.study_history_tree.column("Date", width=100)
        self.study_history_tree.heading("Subject", text="Subject")  # 学習科目
        self.study_history_tree.column("Subject", width=150)
        self.study_history_tree.heading("Minutes", text="Minutes")  # 学習時間（分）
        self.study_history_tree.column("Minutes", width=80)

        # テーブル用スクロールバー
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.study_history_tree.yview)
        self.study_history_tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.study_history_tree.pack(side="left", fill="both", expand=True)

        # 学習記録操作用ボタンエリア
        buttons_frame = ttk.Frame(parent_tab)
        buttons_frame.pack(pady=5, padx=10, fill="x")
        
        # 選択した学習記録を削除するボタン
        delete_button = ttk.Button(buttons_frame, text="Delete Record", 
                                  command=self.delete_study_history_callback)
        delete_button.pack(side="right", padx=5)

    def generate_report_callback(self):
        """週間レポート生成のコールバック関数"""
        filename = report_generator.generate_weekly_report()
        if filename:
            messagebox.showinfo("Report Generated", f"Successfully generated report: {filename}")
        else:
            messagebox.showwarning("Report Error", "No data available for the last 7 days to generate a report.")

    # --- Mock Exam Methods ---
    def load_mock_exams(self):
        for item in self.mock_tree.get_children():
            self.mock_tree.delete(item)
        df = database.get_mock_exams()
        for index, row in df.iterrows():
            values = (
                row['id'],
                row['date'],
                row['subject'],
                row['exam_name'],
                '' if pd.isna(row['score']) else int(row['score']),
                '' if pd.isna(row['max_score']) else int(row['max_score']),
                '' if pd.isna(row['deviation_value']) else row['deviation_value']
            )
            self.mock_tree.insert("", "end", values=values, iid=row['id'])

    def add_mock_exam_callback(self):
        if CALENDAR_AVAILABLE and hasattr(self.mock_date_entry, 'get_date'):
            date = self.mock_date_entry.get_date().strftime('%Y-%m-%d')
        else:
            date = self.mock_date_entry.get()
        subject = self.mock_selected_subject.get()
        exam_name = self.mock_exam_name_entry.get()
        score = self.mock_score_entry.get()
        max_score = self.mock_max_score_entry.get()
        deviation = self.mock_deviation_entry.get()

        if not date or not subject or not exam_name:
            messagebox.showwarning("Input Error", "Date, Subject, and Exam Name are required.")
            return

        try:
            if score and not score.isdigit(): raise ValueError("Score must be a number.")
            if max_score and not max_score.isdigit(): raise ValueError("Max Score must be a number.")
            if deviation: float(deviation)
        except ValueError as e:
            messagebox.showwarning("Input Error", str(e))
            return

        database.add_mock_exam(date, subject, exam_name, score, max_score, deviation)
        
        self.mock_exam_name_entry.delete(0, tk.END)
        self.mock_score_entry.delete(0, tk.END)
        self.mock_max_score_entry.delete(0, tk.END)
        self.mock_deviation_entry.delete(0, tk.END)
        
        self.load_mock_exams()
        messagebox.showinfo("Success", "Mock exam result saved successfully.")

    def delete_mock_exam_callback(self):
        selected_item = self.mock_tree.focus()
        if not selected_item:
            messagebox.showwarning("Selection Error", "Please select a result to delete.")
            return

        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete the selected result?"):
            exam_id = int(selected_item)
            database.delete_mock_exam(exam_id)
            self.load_mock_exams()

    # --- Study History Methods ---
    def load_study_history(self):
        for item in self.study_history_tree.get_children():
            self.study_history_tree.delete(item)
        df = database.get_all_records()
        for index, row in df.iterrows():
            self.study_history_tree.insert("", "end", values=(row['id'], row['date'], row['subject'], row['minutes']), iid=row['id'])

    def delete_study_history_callback(self):
        selected_item = self.study_history_tree.focus()
        if not selected_item:
            messagebox.showwarning("Selection Error", "Please select a record to delete.")
            return

        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete the selected record?"):
            record_id = int(selected_item)
            database.delete_study_record(record_id)
            self.load_study_history()
            self.update_progress_display()

    # --- Exam Goal Methods ---
    def load_exam_goals(self):
        for item in self.goal_tree.get_children():
            self.goal_tree.delete(item)
        df = database.get_exam_goals()
        for index, row in df.iterrows():
            tags = (row['status'].replace(' ', ''),) # Create a tag from the status
            self.goal_tree.insert("", "end", values=(row['id'], row['exam_date'], row['subject'], row['exam_name'], row['target_score'], row['status'], row['notes']), iid=row['id'], tags=tags)

    def add_exam_goal_callback(self):
        subject = self.goal_subject_var.get()
        exam_name = self.goal_exam_name_entry.get()
        if CALENDAR_AVAILABLE and hasattr(self.goal_exam_date_entry, 'get_date'):
            exam_date = self.goal_exam_date_entry.get_date().strftime('%Y-%m-%d')
        else:
            exam_date = self.goal_exam_date_entry.get()
        target_score = self.goal_target_score_entry.get()
        notes = self.goal_notes_text.get("1.0", tk.END).strip()

        if not subject or not exam_name or not target_score:
            messagebox.showwarning("Input Error", "Subject, Exam Name, and Target Score are required.")
            return

        try:
            if not target_score.isdigit(): raise ValueError("Target Score must be a number.")
        except ValueError as e:
            messagebox.showwarning("Input Error", str(e))
            return

        database.add_exam_goal(subject, exam_name, exam_date, int(target_score), notes)

        self.goal_exam_name_entry.delete(0, tk.END)
        self.goal_exam_date_entry.delete(0, tk.END)
        self.goal_target_score_entry.delete(0, tk.END)
        self.goal_notes_text.delete("1.0", tk.END)

        self.load_exam_goals()
        messagebox.showinfo("Success", "Exam goal saved successfully.")

    def update_goal_status_callback(self, status):
        selected_item = self.goal_tree.focus()
        if not selected_item:
            messagebox.showwarning("Selection Error", "Please select a goal to update.")
            return
        
        goal_id = int(selected_item)
        database.update_exam_goal_status(goal_id, status)
        self.load_exam_goals()

    def delete_exam_goal_callback(self):
        selected_item = self.goal_tree.focus()
        if not selected_item:
            messagebox.showwarning("Selection Error", "Please select a goal to delete.")
            return

        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete the selected goal?"):
            goal_id = int(selected_item)
            database.delete_exam_goal(goal_id)
            self.load_exam_goals()

    # --- Study Goal Methods ---
    def load_study_goals(self):
        for item in self.study_goals_tree.get_children():
            self.study_goals_tree.delete(item)
        df = database.get_goals()
        for index, row in df.iterrows():
            self.study_goals_tree.insert("", "end", values=(row['id'], row['goal_type'].capitalize(), row['subject'], row['target_minutes'], row['notes']), iid=row['id'])

    def set_study_goal_callback(self):
        goal_type = self.study_goal_type.get()
        subject = self.study_goal_subject.get()
        minutes_str = self.study_goal_minutes_entry.get()
        notes = self.study_goal_notes_entry.get()

        if not minutes_str:
            messagebox.showwarning("Input Error", "Target minutes cannot be empty.")
            return
        try:
            minutes = int(minutes_str)
            if minutes <= 0:
                raise ValueError("Minutes must be a positive number.")
        except ValueError:
            messagebox.showwarning("Input Error", "Please enter a valid positive number for minutes.")
            return

        today = datetime.now().date()
        if goal_type == 'daily':
            start_date = today.strftime('%Y-%m-%d')
        else: # weekly
            start_date = (today - timedelta(days=today.weekday())).strftime('%Y-%m-%d')

        database.set_goal(goal_type, subject, start_date, minutes, notes)
        self.study_goal_minutes_entry.delete(0, tk.END)
        self.study_goal_notes_entry.delete(0, tk.END)
        self.load_study_goals()
        self.update_progress_display()
        messagebox.showinfo("Success", "Study goal has been set successfully.")

    def delete_study_goal_callback(self):
        selected_item = self.study_goals_tree.focus()
        if not selected_item:
            messagebox.showwarning("Selection Error", "Please select a goal to delete.")
            return

        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete the selected goal?"):
            goal_id = int(selected_item)
            database.delete_study_goal(goal_id)
            self.load_study_goals()
            self.update_progress_display()

    def on_subject_change(self, *args):
        self.update_progress_display()

    def reset_ui(self):
        if self.after_id: self.root.after_cancel(self.after_id); self.after_id = None
        self.timer_running = False; self.is_paused = False; self.pomodoro_state = None
        
        for widget in self.button_frame.winfo_children(): widget.pack_forget()
        for widget in self.bottom_button_frame.winfo_children(): widget.pack_forget()

        self.start_button.config(text="Start Pomodoro" if self.pomodoro_mode.get() else "Start")
        self.start_button.pack(side="left", expand=True, padx=5)
        self.analysis_button.pack(side="left", expand=True, padx=5)
        self.report_button.pack(side="left", expand=True, padx=5)
        
        self.subject_menu.config(state="enabled")
        self.pomodoro_check.config(state="enabled")
        self.pomodoro_status_label.config(text="")
        self.timer_label.config(text="25:00" if self.pomodoro_mode.get() else "00:00:00")
        self.update_progress_display()

    def update_progress_display(self):
        """日次目標の進捗表示を更新する関数"""
        subject = self.selected_subject.get()  # 現在選択中の科目を取得
        self.goal_frame.config(text=f"Daily Goal Progress ({subject})")
        today = datetime.now().date()
        
        # 選択科目の今日の目標と進捗を取得
        target, progress = database.get_progress('daily', subject, today)

        if target is None:
            # 個別科目の目標がない場合、「全科目」目標をチェック
            target, progress = database.get_progress('daily', 'All', today)
            if target is not None:
                self.goal_frame.config(text="Daily Goal Progress (All Subjects)")
            else:
                # どちらの目標も設定されていない場合
                self.goal_progress_label.config(text=f'No daily goal set for "{subject}" or "All".')
                self.goal_progressbar['value'] = 0
                self.goal_progressbar['maximum'] = 100
                return

        # 目標と現在の進捗を表示・更新
        self.goal_progress_label.config(text=f"Daily Goal: {progress} / {target} minutes")
        self.goal_progressbar['value'] = progress      # 現在の進捗
        self.goal_progressbar['maximum'] = target      # 目標値

    def save_record(self, duration):
        """学習記録をデータベースに保存する関数"""
        minutes = int(duration.total_seconds() // 60)  # 秒を分に変換
        
        if minutes == 0:
            print("Study time was less than a minute, so it was not recorded.")  # 1分未満は記録しない
            return
            
        # 今日の日付と選択科目で記録を保存
        today_date = datetime.now().strftime('%Y-%m-%d')
        subject = self.selected_subject.get()
        database.add_record(today_date, subject, minutes)
        
        print(f"Record saved: {subject} - {minutes} minutes")  # コンソールに保存内容を表示
        
        # 進捗表示と履歴一覧を更新
        self.update_progress_display()
        self.load_study_history()

    def toggle_pomodoro_mode(self):
        self.reset_ui()

    def start_timer(self):
        """タイマー開始（ポモドーロ/通常モードの切り替え）"""
        if self.pomodoro_mode.get():
            # ポモドーロモードの場合
            self.pomodoro_cycles = 0  # サイクル数をリセット
            self.start_pomodoro_work_session()  # 25分の作業セッション開始
        else:
            # 通常モードの場合
            self.start_normal_timer()  # 自由な時間計測開始

    def start_normal_timer(self):
        if not self.timer_running:
            self.timer_running = True
            self.is_paused = False
            self.start_time = datetime.now()
            self.elapsed_time = timedelta(0)
            self.update_normal_timer()
            self.update_ui_for_running_timer()

    def update_normal_timer(self):
        if self.timer_running and not self.is_paused:
            current_elapsed = self.elapsed_time + (datetime.now() - self.start_time)
            formatted_time = str(current_elapsed).split('.')[0]
            self.timer_label.config(text=formatted_time)
            self.after_id = self.root.after(1000, self.update_normal_timer)

    def start_pomodoro_work_session(self):
        self.pomodoro_state = "Work"
        self.pomodoro_status_label.config(text=f"Work ({self.pomodoro_cycles + 1}/4)")
        self.run_pomodoro_timer(25 * 60)

    def start_pomodoro_break(self):
        self.pomodoro_cycles += 1
        if self.pomodoro_cycles % 4 == 0:
            self.pomodoro_state = "Long Break"
            self.pomodoro_status_label.config(text="Long Break")
            self.run_pomodoro_timer(15 * 60)
        else:
            self.pomodoro_state = "Short Break"
            self.pomodoro_status_label.config(text=f"Short Break ({self.pomodoro_cycles}/4)")
            self.run_pomodoro_timer(5 * 60)

    def run_pomodoro_timer(self, duration_seconds):
        self.timer_running = True
        self.end_time = datetime.now() + timedelta(seconds=duration_seconds)
        self.update_pomodoro_timer()
        self.update_ui_for_running_timer()

    def update_pomodoro_timer(self):
        if not self.timer_running: return
        remaining = self.end_time - datetime.now()
        if remaining.total_seconds() < 0:
            self.root.bell()
            if self.pomodoro_state == "Work":
                self.save_pomodoro_record()
                self.start_pomodoro_break()
            else: self.reset_ui()
            return
        formatted_time = f"{int(remaining.total_seconds() // 60):02d}:{int(remaining.total_seconds() % 60):02d}"
        self.timer_label.config(text=formatted_time)
        self.after_id = self.root.after(1000, self.update_pomodoro_timer)

    def pause_timer(self):
        if self.timer_running and not self.is_paused:
            self.is_paused = True; self.timer_running = False
            self.elapsed_time += datetime.now() - self.start_time
            if self.after_id: self.root.after_cancel(self.after_id); self.after_id = None
            self.update_ui_for_paused_timer()

    def resume_timer(self):
        if not self.timer_running and self.is_paused:
            self.is_paused = False; self.timer_running = True
            self.start_time = datetime.now()
            self.update_normal_timer()
            self.update_ui_for_running_timer(is_resume=True)

    def stop_and_reset_all(self):
        if self.pomodoro_mode.get(): self.reset_ui()
        else:
            if self.timer_running or self.is_paused:
                self.timer_running = False
                if not self.is_paused: self.elapsed_time += datetime.now() - self.start_time
                if self.after_id: self.root.after_cancel(self.after_id)
                self.update_ui_for_stopped_timer()

    def save_and_reset(self):
        self.save_record(self.elapsed_time)
        self.reset_ui()

    def discard_and_reset(self):
        self.reset_ui()

    def save_pomodoro_record(self):
        self.save_record(timedelta(minutes=25))

    def update_ui_for_running_timer(self, is_resume=False):
        if not is_resume: self.start_button.pack_forget(); self.bottom_button_frame.pack_forget()
        self.resume_button.pack_forget()
        self.subject_menu.config(state="disabled")
        self.pomodoro_check.config(state="disabled")
        if not self.pomodoro_mode.get(): self.pause_button.pack(side="left", expand=True, padx=5)
        self.stop_button.pack(side="left", expand=True, padx=5)

    def update_ui_for_paused_timer(self):
        self.pause_button.pack_forget()
        self.resume_button.pack(side="left", expand=True, padx=5)

    def update_ui_for_stopped_timer(self):
        self.pause_button.pack_forget(); self.resume_button.pack_forget(); self.stop_button.pack_forget()
        self.save_button.pack(side="left", expand=True, padx=5)
        self.discard_button.pack(side="left", expand=True, padx=5)

    def open_analysis_window(self):
        """学習データのグラフ分析ウィンドウを開く関数"""
        show_analysis_window(self.root)  # visualize.pyの関数を呼び出し


if __name__ == "__main__":
    root = tk.Tk()
    app = StudyTimerApp(root)
    root.mainloop()
