#!/usr/bin/env python3
import os
import subprocess
import sys


def merge(files, output_path):
    result = subprocess.run(["pdfunite", *files, output_path], capture_output=True, text=True)
    return result.returncode == 0, result.stderr


# --------------------------------------------------------------------------
# Interface graphique (tkinter) : liste réordonnable par glisser-déposer,
# avec croix de suppression par élément et ajout de fichiers à la volée.
# Le thème (clair/sombre) suit les préférences GNOME pour coller au style
# Nautilus, et les boutons sont dessinés avec des coins arrondis.
# --------------------------------------------------------------------------

ROW_HEIGHT = 40
ROW_GAP = 6
ROW_TOTAL = ROW_HEIGHT + ROW_GAP

LIGHT_PALETTE = {
    "bg": "#fafafa",
    "card_bg": "#ffffff",
    "border": "#dedede",
    "accent": "#3584e4",
    "accent_hover": "#2b6bc4",
    "text": "#202020",
    "subtext": "#7a7a7a",
    "danger": "#e01b24",
    "secondary_bg": "#e9e9e9",
    "secondary_hover": "#dcdcdc",
}

DARK_PALETTE = {
    "bg": "#242424",
    "card_bg": "#303030",
    "border": "#3d3d3d",
    "accent": "#3584e4",
    "accent_hover": "#4a93ea",
    "text": "#eeeeec",
    "subtext": "#9a9a9a",
    "danger": "#ff7b63",
    "secondary_bg": "#3a3a3a",
    "secondary_hover": "#454545",
}


def detect_dark_mode():
    try:
        result = subprocess.run(
            ["gsettings", "get", "org.gnome.desktop.interface", "color-scheme"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if "dark" in result.stdout.lower():
            return True
    except Exception:
        pass
    try:
        result = subprocess.run(
            ["gsettings", "get", "org.gnome.desktop.interface", "gtk-theme"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if "dark" in result.stdout.lower():
            return True
    except Exception:
        pass
    return False


class RoundedButton:
    """Bouton avec coins arrondis dessiné sur un Canvas (style GNOME/Nautilus)."""

    def __init__(self, parent, text, command, colors, kind="secondary", padx=16, pady=9):
        import tkinter as tk

        self.tk = tk
        self.command = command
        self.colors = colors
        self.kind = kind

        if kind == "accent":
            self.fill = colors["accent"]
            self.hover_fill = colors["accent_hover"]
            self.fg = "#ffffff"
        else:
            self.fill = colors["secondary_bg"]
            self.hover_fill = colors["secondary_hover"]
            self.fg = colors["text"]

        font = ("Sans", 10, "bold" if kind == "accent" else "normal")
        helper = tk.Label(parent, text=text, font=font)
        helper.update_idletasks()
        text_w = helper.winfo_reqwidth()
        text_h = helper.winfo_reqheight()
        helper.destroy()

        self.width = text_w + padx * 2
        self.height = text_h + pady * 2
        radius = self.height // 2

        self.canvas = tk.Canvas(
            parent,
            width=self.width,
            height=self.height,
            highlightthickness=0,
            bg=colors["bg"],
            cursor="hand2",
        )
        self.shape = self._round_rect(2, 2, self.width - 2, self.height - 2, radius, self.fill)
        self.label = self.canvas.create_text(
            self.width / 2, self.height / 2, text=text, fill=self.fg, font=font
        )

        for tag_handler in ("<Button-1>", "<Enter>", "<Leave>"):
            self.canvas.tag_bind(self.shape, tag_handler, self._on_event(tag_handler))
            self.canvas.tag_bind(self.label, tag_handler, self._on_event(tag_handler))

    def _on_event(self, kind):
        def handler(event):
            if kind == "<Button-1>":
                self.command()
            elif kind == "<Enter>":
                self.canvas.itemconfigure(self.shape, fill=self.hover_fill)
            elif kind == "<Leave>":
                self.canvas.itemconfigure(self.shape, fill=self.fill)

        return handler

    def _round_rect(self, x1, y1, x2, y2, r, fill):
        points = [
            x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
            x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
            x1, y2, x1, y2 - r, x1, y1 + r, x1, y1,
        ]
        return self.canvas.create_polygon(points, smooth=True, fill=fill, outline=fill)

    def pack(self, **kwargs):
        self.canvas.pack(**kwargs)


class PdfMergerApp:
    def __init__(self):
        import tkinter as tk
        from tkinter import ttk

        self.tk = tk
        self.files = []
        self.row_frames = []
        self.drag_frame = None
        self.drag_grab_y = 0
        self.colors = DARK_PALETTE if detect_dark_mode() else LIGHT_PALETTE
        c = self.colors

        self.root = tk.Tk()
        self.root.title("Fusion de PDF")
        self.root.geometry("560x560")
        self.root.minsize(440, 360)
        self.root.configure(bg=c["bg"])

        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure(
            "Title.TLabel", background=c["bg"], foreground=c["text"], font=("Sans", 16, "bold")
        )
        style.configure(
            "Subtitle.TLabel", background=c["bg"], foreground=c["subtext"], font=("Sans", 10)
        )
        style.configure("Card.TFrame", background=c["bg"])
        style.configure(
            "Thin.Vertical.TScrollbar",
            background=c["subtext"],
            troughcolor=c["bg"],
            bordercolor=c["bg"],
            arrowsize=0,
            gripcount=0,
            relief="flat",
            borderwidth=0,
            width=8,
        )
        style.map(
            "Thin.Vertical.TScrollbar",
            background=[("active", c["accent"])],
        )

        header = ttk.Frame(self.root, style="Card.TFrame")
        header.pack(fill=tk.X, padx=24, pady=(22, 4))
        ttk.Label(header, text="Fusionner des PDF", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            header,
            text="Ajoute des fichiers, glisse-dépose pour les réordonner.",
            style="Subtitle.TLabel",
        ).pack(anchor="w", pady=(2, 0))

        toolbar = ttk.Frame(self.root, style="Card.TFrame")
        toolbar.pack(fill=tk.X, padx=24, pady=(14, 10))
        RoundedButton(
            toolbar, "+ Ajouter des fichiers PDF", self.add_files, c, kind="secondary"
        ).pack(side=tk.LEFT)

        list_frame = tk.Frame(self.root, bg=c["bg"])
        list_frame.pack(fill=tk.BOTH, expand=True, padx=24)

        self.canvas = tk.Canvas(list_frame, highlightthickness=0, bg=c["bg"])
        scrollbar = ttk.Scrollbar(
            list_frame, orient="vertical", command=self.canvas.yview, style="Thin.Vertical.TScrollbar"
        )
        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, padx=(2, 0))
        self.canvas.bind_all(
            "<MouseWheel>",
            lambda e: self.canvas.yview_scroll(-1 if e.delta > 0 else 1, "units"),
        )
        self.canvas.bind_all(
            "<Button-4>", lambda e: self.canvas.yview_scroll(-1, "units")
        )
        self.canvas.bind_all(
            "<Button-5>", lambda e: self.canvas.yview_scroll(1, "units")
        )

        self.rows_container = tk.Frame(self.canvas, bg=c["bg"])
        self.rows_container.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )
        self.canvas_window = self.canvas.create_window(
            (0, 0), window=self.rows_container, anchor="nw"
        )
        self.canvas.bind(
            "<Configure>",
            lambda e: self.canvas.itemconfigure(self.canvas_window, width=e.width),
        )

        footer = ttk.Frame(self.root, style="Card.TFrame")
        footer.pack(fill=tk.X, padx=24, pady=20)
        self.count_label = ttk.Label(footer, text="", style="Subtitle.TLabel")
        self.count_label.pack(side=tk.LEFT)
        RoundedButton(
            footer, "Fusionner et enregistrer", self.merge_and_save, c, kind="accent"
        ).pack(side=tk.RIGHT)

        self.rebuild_rows()

    # -- gestion de la liste ------------------------------------------------

    def add_files(self):
        result = subprocess.run(
            [
                "zenity",
                "--file-selection",
                "--multiple",
                "--separator=\n",
                "--file-filter=PDF | *.pdf",
                "--title=Sélectionner des fichiers PDF",
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return
        paths = [line for line in result.stdout.splitlines() if line]
        if not paths:
            return
        self.files.extend(paths)
        self.rebuild_rows()

    def remove_file_by_frame(self, frame):
        index = self.row_frames.index(frame)
        del self.files[index]
        del self.row_frames[index]
        frame.destroy()
        self.rebuild_rows(create=False)

    def rebuild_rows(self, create=True):
        """(Re)construit les widgets de ligne. N'est appelé qu'à l'ajout ou
        la suppression d'un fichier — jamais pendant un glisser-déposer, pour
        éviter tout scintillement."""
        self.count_label.configure(
            text=f"{len(self.files)} fichier(s)" if self.files else ""
        )

        if not self.files:
            for widget in self.rows_container.winfo_children():
                widget.destroy()
            self.row_frames = []
            self.rows_container.configure(height=1)
            self.tk.Label(
                self.rows_container,
                text="Aucun fichier ajouté pour l'instant",
                fg=self.colors["subtext"],
                bg=self.colors["bg"],
                font=("Sans", 10),
            ).place(x=0, y=20, relwidth=1)
            self.rows_container.configure(height=80)
            return

        if create:
            for widget in self.rows_container.winfo_children():
                widget.destroy()
            self.row_frames = [self.build_row(path) for path in self.files]

        self.rows_container.configure(height=len(self.files) * ROW_TOTAL)
        self.position_rows()

    def position_rows(self, skip=None):
        for index, frame in enumerate(self.row_frames):
            frame.number_label.configure(text=str(index + 1))
            if frame is skip:
                continue
            frame.place(x=0, y=index * ROW_TOTAL, relwidth=1, height=ROW_HEIGHT)

    def build_row(self, path):
        tk = self.tk
        c = self.colors
        row = tk.Frame(self.rows_container, bg=c["card_bg"], highlightthickness=1, highlightbackground=c["border"])

        number = tk.Label(
            row, text="", bg=c["card_bg"], fg=c["subtext"], font=("Sans", 9, "bold"), width=2
        )
        number.pack(side=tk.LEFT, padx=(10, 4))
        row.number_label = number

        handle = tk.Label(row, text="☰", cursor="fleur", bg=c["card_bg"], fg=c["subtext"], width=2)
        handle.pack(side=tk.LEFT)

        name_label = tk.Label(
            row,
            text=os.path.basename(path),
            anchor="w",
            bg=c["card_bg"],
            fg=c["text"],
            font=("Sans", 10),
        )
        name_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(4, 4))

        delete_btn = tk.Label(
            row, text="✕", fg=c["danger"], bg=c["card_bg"], cursor="hand2", font=("Sans", 11)
        )
        delete_btn.pack(side=tk.RIGHT, padx=12)
        delete_btn.bind("<Button-1>", lambda e, f=row: self.remove_file_by_frame(f))

        for widget in (row, number, handle, name_label):
            widget.bind("<ButtonPress-1>", lambda e, f=row: self.start_drag(f))
            widget.bind("<B1-Motion>", self.on_drag)
            widget.bind("<ButtonRelease-1>", self.end_drag)

        return row

    # -- glisser-déposer ------------------------------------------------

    def start_drag(self, frame):
        self.drag_frame = frame
        self.drag_grab_y = self.root.winfo_pointery() - frame.winfo_rooty()
        frame.lift()

    def on_drag(self, event):
        if self.drag_frame is None:
            return
        rel_y = (
            self.root.winfo_pointery()
            - self.rows_container.winfo_rooty()
            - self.drag_grab_y
        )
        max_y = max(0, (len(self.row_frames) - 1) * ROW_TOTAL)
        rel_y = max(0, min(max_y, rel_y))
        self.drag_frame.place(x=0, y=rel_y, relwidth=1, height=ROW_HEIGHT)

        new_index = max(
            0, min(len(self.row_frames) - 1, round(rel_y / ROW_TOTAL))
        )
        cur_index = self.row_frames.index(self.drag_frame)
        if new_index != cur_index:
            frame = self.row_frames.pop(cur_index)
            path = self.files.pop(cur_index)
            self.row_frames.insert(new_index, frame)
            self.files.insert(new_index, path)
            self.position_rows(skip=self.drag_frame)

    def end_drag(self, event):
        self.drag_frame = None
        self.position_rows()

    # -- fusion ------------------------------------------------

    def merge_and_save(self):
        from tkinter import messagebox

        if len(self.files) < 2:
            messagebox.showwarning("Attention", "Ajoute au moins 2 fichiers PDF à fusionner.")
            return

        result = subprocess.run(
            [
                "zenity",
                "--file-selection",
                "--save",
                "--confirm-overwrite",
                "--filename=merged.pdf",
                "--title=Enregistrer le PDF fusionné",
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return
        output_path = result.stdout.strip()
        if not output_path:
            return
        if not output_path.lower().endswith(".pdf"):
            output_path += ".pdf"

        ok, error = merge(self.files, output_path)
        if not ok:
            messagebox.showerror("Erreur", f"Échec de la fusion :\n{error}")
            return

        messagebox.showinfo("Succès", f"PDF fusionné enregistré :\n{output_path}")

    def run(self):
        self.root.mainloop()


def run_gui():
    PdfMergerApp().run()


# --------------------------------------------------------------------------
# Mode ligne de commande
# --------------------------------------------------------------------------


def run_cli(args):
    *files, output_path = args
    if len(files) < 2:
        print("Erreur : il faut au moins 2 fichiers PDF à fusionner.", file=sys.stderr)
        print(f"Usage : {sys.argv[0]} fichier1.pdf fichier2.pdf [...] sortie.pdf", file=sys.stderr)
        sys.exit(1)

    ok, error = merge(files, output_path)
    if not ok:
        print(f"Échec de la fusion :\n{error}", file=sys.stderr)
        sys.exit(1)

    print(f"PDF fusionné enregistré : {output_path}")


def print_help():
    print(f"Usage : {sys.argv[0]} [fichier1.pdf fichier2.pdf [...] sortie.pdf]")
    print()
    print("Sans argument : ouvre l'interface graphique pour sélectionner,")
    print("réorganiser (glisser-déposer) et fusionner les PDF.")
    print()
    print("Avec arguments : fusionne les fichiers PDF donnés (au moins 2) dans")
    print("l'ordre indiqué, le dernier argument étant le fichier de sortie.")
    print()
    print("Options :")
    print("  -h, --help    Affiche cette aide et quitte")


def main():
    args = sys.argv[1:]
    if "-h" in args or "--help" in args:
        print_help()
        return
    if args:
        run_cli(args)
    else:
        run_gui()


if __name__ == "__main__":
    main()