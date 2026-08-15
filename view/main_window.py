# -*- coding: utf-8 -*-
"""
Archiver（棚卸ツール） メインウィンドウ。

流れ：
    起動 → UI表示 → ①～④のどれを実行したいか選択 → フォルダ指定
    → ②の場合のみタグ候補を表示して選択（複数選択可）
    → ④の場合のみ既存のtags_output_xxx.csvを指定
    → 実行 → 完了後にダイアログ表示（CSVは実行時に生成・更新済み）

View は controller のメソッドのみを呼び出し、model には直接アクセスしない。
"""
from tkinter import filedialog, messagebox

import customtkinter as ctk

from version import __version__
from view.style import font

ACTIONS = [
    ("count", "①タグの件数カウント（all_tags_count.csv）"),
    ("extract", "②指定タグの情報を抽出（tags_output_タグ名.csv）"),
    ("index", "③索引ファイルの生成（index.csv）"),
    ("merge", "④継続的な統合（既存のtags_output_タグ名.csvを更新）"),
]


class MainWindow(ctk.CTk):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller

        self.title(f"Archiver - 棚卸ツール (v{__version__})")
        self.geometry("780x780")
        self.resizable(True, True)

        self.action_var = ctk.StringVar(value=ACTIONS[0][0])
        self.tag_check_vars = {}  # tag -> BooleanVar（②のタグ選択用）

        ctk.CTkLabel(
            self, text="棚卸ツール", font=font(19, "bold")
        ).pack(pady=(20, 4))
        ctk.CTkLabel(
            self,
            text="実行したい処理・対象フォルダを選んで「実行」を押してください。",
            text_color="gray",
            font=font(13),
        ).pack(pady=(0, 10))

        # --- 1. 処理の選択 ---
        action_frame = ctk.CTkFrame(self)
        action_frame.pack(fill="x", padx=20, pady=10)
        ctk.CTkLabel(
            action_frame, text="実行する処理", font=font(14, "bold")
        ).pack(anchor="w", padx=12, pady=(10, 4))
        for value, label in ACTIONS:
            ctk.CTkRadioButton(
                action_frame,
                text=label,
                value=value,
                variable=self.action_var,
                font=font(13),
                command=self._on_action_changed,
            ).pack(anchor="w", padx=20, pady=4)
        ctk.CTkFrame(action_frame, fg_color="transparent", height=6).pack()

        # --- 2. フォルダ指定 ---
        folder_frame = ctk.CTkFrame(self)
        folder_frame.pack(fill="x", padx=20, pady=10)
        ctk.CTkLabel(
            folder_frame, text="対象フォルダ（output.csv / tags.txt をサブフォルダも含めて探索します）",
            font=font(14, "bold"),
        ).pack(anchor="w", padx=12, pady=(10, 4))

        folder_row = ctk.CTkFrame(folder_frame, fg_color="transparent")
        folder_row.pack(fill="x", padx=12, pady=(0, 10))
        self.folder_entry = ctk.CTkEntry(folder_row, font=font(13))
        self.folder_entry.pack(side="left", fill="x", expand=True)
        self.folder_entry.insert(0, self.controller.default_folder())
        self.folder_entry.bind("<KeyRelease>", lambda e: self._on_folder_changed())

        ctk.CTkButton(
            folder_row, text="参照...", width=90, font=font(13),
            command=self._browse_folder,
        ).pack(side="left", padx=(8, 0))

        # --- 3. タグ候補（②選択時のみ表示） ---
        self.tag_section = ctk.CTkFrame(self)
        self.tag_section_visible = False

        tag_header_row = ctk.CTkFrame(self.tag_section, fg_color="transparent")
        tag_header_row.pack(fill="x", padx=12, pady=(10, 4))
        ctk.CTkLabel(
            tag_header_row, text="タグ候補（複数選択可）", font=font(14, "bold")
        ).pack(side="left")
        ctk.CTkButton(
            tag_header_row, text="タグ候補を読み込む", width=160, font=font(12),
            command=self._load_tag_candidates,
        ).pack(side="right")

        self.tag_scroll = ctk.CTkScrollableFrame(self.tag_section, height=160)
        self.tag_scroll.pack(fill="x", padx=12, pady=(0, 10))

        self.tag_hint_label = ctk.CTkLabel(
            self.tag_section, text="", text_color="gray", font=font(12),
        )
        self.tag_hint_label.pack(anchor="w", padx=12, pady=(0, 6))

        # --- 4. 既存ファイル指定（④選択時のみ表示） ---
        self.merge_section = ctk.CTkFrame(self)
        self.merge_section_visible = False

        ctk.CTkLabel(
            self.merge_section,
            text="更新対象の既存ファイル（tags_output_タグ名.csv）",
            font=font(14, "bold"),
        ).pack(anchor="w", padx=12, pady=(10, 4))

        merge_row = ctk.CTkFrame(self.merge_section, fg_color="transparent")
        merge_row.pack(fill="x", padx=12, pady=(0, 4))
        self.merge_file_entry = ctk.CTkEntry(merge_row, font=font(13))
        self.merge_file_entry.pack(side="left", fill="x", expand=True)
        self.merge_file_entry.bind("<KeyRelease>", lambda e: self._on_merge_file_changed())

        ctk.CTkButton(
            merge_row, text="参照...", width=90, font=font(13),
            command=self._browse_merge_file,
        ).pack(side="left", padx=(8, 0))

        self.merge_tags_label = ctk.CTkLabel(
            self.merge_section, text="", font=font(13, "bold"), text_color="#a13d3d",
        )
        self.merge_tags_label.pack(anchor="w", padx=12, pady=(2, 0))

        ctk.CTkLabel(
            self.merge_section,
            text="ファイル内の『最終記録日』以降（同日を含む）で、ファイル名から復元した"
                 "タグに一致する情報のみを、フォルダ側のoutput.csvから追加します。",
            text_color="gray",
            font=font(12),
            wraplength=700,
            justify="left",
        ).pack(anchor="w", padx=12, pady=(0, 10))

        # --- 5. 実行 ---
        bottom = ctk.CTkFrame(self)
        bottom.pack(fill="x", padx=20, pady=16)
        self.status_label = ctk.CTkLabel(bottom, text="", font=font(12))
        self.status_label.pack(side="left")
        self.run_btn = ctk.CTkButton(
            bottom, text="実行", font=font(14, "bold"),
            command=self._run,
        )
        self.run_btn.pack(side="right")

        self._on_action_changed()

    # ------------------------------------------------------------
    def _browse_folder(self):
        selected = filedialog.askdirectory(
            initialdir=self.folder_entry.get() or self.controller.default_folder()
        )
        if selected:
            self.folder_entry.delete(0, "end")
            self.folder_entry.insert(0, selected)
        self._on_folder_changed()

    def _browse_merge_file(self):
        selected = filedialog.askopenfilename(
            initialdir=self.controller.default_folder(),
            filetypes=[("Archiver 抽出ファイル", "tags_output_*.csv"), ("すべてのファイル", "*.*")],
        )
        if selected:
            self.merge_file_entry.delete(0, "end")
            self.merge_file_entry.insert(0, selected)
        self._on_merge_file_changed()

    def _on_merge_file_changed(self):
        path = self.merge_file_entry.get().strip()
        tags = self.controller.preview_tags_from_existing_file(path)
        if not path:
            self.merge_tags_label.configure(text="")
        elif not self.controller.is_valid_existing_extract_file(path):
            self.merge_tags_label.configure(
                text="※ tags_output_タグ名.csv 形式の有効なファイルを指定してください。"
            )
        elif tags:
            self.merge_tags_label.configure(
                text=f"検出したタグ（ファイル名から復元）：{', '.join(tags)}"
            )
        else:
            self.merge_tags_label.configure(
                text="※ ファイル名からタグを復元できませんでした。"
            )
        self._update_run_button_state()

    def _on_action_changed(self):
        action = self.action_var.get()

        is_extract = action == "extract"
        if is_extract and not self.tag_section_visible:
            self.tag_section.pack(fill="x", padx=20, pady=10, before=self._bottom_frame())
            self.tag_section_visible = True
        elif not is_extract and self.tag_section_visible:
            self.tag_section.pack_forget()
            self.tag_section_visible = False

        is_merge = action == "merge"
        if is_merge and not self.merge_section_visible:
            self.merge_section.pack(fill="x", padx=20, pady=10, before=self._bottom_frame())
            self.merge_section_visible = True
            self._on_merge_file_changed()
        elif not is_merge and self.merge_section_visible:
            self.merge_section.pack_forget()
            self.merge_section_visible = False

        self._update_run_button_state()

    def _bottom_frame(self):
        # bottomフレームは最後に作られているので、常に最後の子として扱う
        return self.winfo_children()[-1]

    def _on_folder_changed(self):
        self._update_run_button_state()

    def _load_tag_candidates(self):
        folder = self.folder_entry.get().strip()
        if not self.controller.is_valid_folder(folder):
            messagebox.showwarning("Archiver", "有効なフォルダを指定してください。")
            return

        for w in self.tag_scroll.winfo_children():
            w.destroy()
        self.tag_check_vars = {}

        tags = self.controller.load_tag_candidates(folder)
        if not tags:
            self.tag_hint_label.configure(
                text="このフォルダ配下に tags.txt が見つからないか、タグが登録されていません。"
            )
        else:
            self.tag_hint_label.configure(
                text=f"{len(tags)}件のタグ候補が見つかりました。使いたいタグにチェックしてください。"
            )
            for tag in tags:
                var = ctk.BooleanVar(value=False)
                ctk.CTkCheckBox(
                    self.tag_scroll, text=tag, variable=var, font=font(13),
                    command=self._update_run_button_state,
                ).pack(anchor="w", padx=6, pady=3)
                self.tag_check_vars[tag] = var

        self._update_run_button_state()

    def _selected_tags(self):
        return [tag for tag, var in self.tag_check_vars.items() if var.get()]

    def _update_run_button_state(self):
        folder = self.folder_entry.get().strip()
        ready = self.controller.is_valid_folder(folder)

        action = self.action_var.get()
        if action == "extract":
            ready = ready and len(self._selected_tags()) > 0
        elif action == "merge":
            merge_file = self.merge_file_entry.get().strip()
            ready = ready and self.controller.is_valid_existing_extract_file(merge_file)

        self.run_btn.configure(state="normal" if ready else "disabled")

    def _run(self):
        folder = self.folder_entry.get().strip()
        action = self.action_var.get()

        try:
            if action == "count":
                result = self.controller.run_count(folder)
                msg = (
                    f"タグの件数カウントが完了しました。\n\n"
                    f"対象CSV数：{result['csv_file_count']}件\n"
                    f"集計タグ数：{result['tag_count']}件\n\n"
                    f"出力先：{result['output_path']}"
                )
            elif action == "extract":
                selected = self._selected_tags()
                result = self.controller.run_extract(folder, selected)
                msg = (
                    f"タグ指定抽出が完了しました。\n\n"
                    f"選択タグ：{', '.join(selected)}\n"
                    f"対象CSV数：{result['csv_file_count']}件\n"
                    f"抽出件数：{result['matched_count']}件\n\n"
                    f"出力先：{result['output_path']}"
                )
            elif action == "merge":
                merge_file = self.merge_file_entry.get().strip()
                result = self.controller.run_merge(merge_file, folder)
                msg = (
                    f"継続的な統合が完了しました。\n\n"
                    f"対象タグ：{', '.join(result['tags']) or '(復元できませんでした)'}\n"
                    f"取込み基準日（更新前の最終記録日）：{result['previous_last_date'] or '(なし)'}\n"
                    f"追加件数：{result['added_count']}件\n"
                    f"合計件数：{result['total_count']}件\n\n"
                    f"出力先：{result['output_path']}"
                )
            else:  # index
                result = self.controller.run_index(folder)
                msg = (
                    f"索引ファイルの生成が完了しました。\n\n"
                    f"対象CSV数：{result['csv_file_count']}件\n"
                    f"タグ数：{result['tag_count']}件\n\n"
                    f"出力先：{result['output_path']}"
                )
        except Exception as e:  # noqa: BLE001
            messagebox.showerror("Archiver", f"処理中にエラーが発生しました。\n{e}")
            return

        self.status_label.configure(text="完了しました")
        messagebox.showinfo("Archiver - 完了", msg)
