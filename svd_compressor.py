"""
Compresor de Imágenes mediante Descomposición en Valores Singulares (SVD)
MATE1187 — Álgebra Lineal para la Computación
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from io import BytesIO
import threading
import numpy as np
from PIL import Image
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import os

try:
    import cairosvg
except ImportError:
    cairosvg = None


class SVDImageCompressor:
    def __init__(self, root):
        self.root = root
        self.root.title("Compresor de Imágenes — SVD | MATE1187")
        self.root.geometry("1280x820")
        self.root.minsize(900, 600)

        self.image_array = None
        self.image_path = None
        self.image_mode = None       # 'grayscale' or 'rgb'
        self.image_source = None     # 'raster' or 'svg'
        self.is_loading = False

        # SVD components (grayscale)
        self.U = self.S = self.Vt = None

        # SVD components per channel (RGB)
        self.U_ch = self.S_ch = self.Vt_ch = None
        self.controls = []

        self._build_ui()

    # ------------------------------------------------------------------ UI --

    def _build_ui(self):
        self._build_toolbar()

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

        self.tab_compare = ttk.Frame(self.notebook)
        self.tab_multi   = ttk.Frame(self.notebook)
        self.tab_metrics = ttk.Frame(self.notebook)
        self.tab_graphs  = ttk.Frame(self.notebook)

        self.notebook.add(self.tab_compare, text="  Comparación  ")
        self.notebook.add(self.tab_multi,   text="  k = 5, 20, 50, 100  ")
        self.notebook.add(self.tab_metrics, text="  Métricas  ")
        self.notebook.add(self.tab_graphs,  text="  Análisis  ")

        # Canvas placeholders
        self.canvas_compare = None
        self.canvas_multi   = None
        self.canvas_graphs  = None

        self._build_metrics_tab()
        self._build_status_bar()

    def _build_toolbar(self):
        bar = ttk.Frame(self.root, padding=(8, 6))
        bar.pack(fill=tk.X)

        self.load_button = ttk.Button(bar, text="Cargar imagen", command=self.load_image)
        self.load_button.pack(side=tk.LEFT, padx=4)
        self.controls.append(self.load_button)

        ttk.Separator(bar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8)

        ttk.Label(bar, text="k:").pack(side=tk.LEFT)
        self.k_var = tk.IntVar(value=20)
        self.k_spin = ttk.Spinbox(bar, from_=1, to=500, textvariable=self.k_var, width=6)
        self.k_spin.pack(side=tk.LEFT, padx=4)
        self.controls.append(self.k_spin)

        self.compress_button = ttk.Button(bar, text="Comprimir", command=self.compress)
        self.compress_button.pack(side=tk.LEFT, padx=4)
        self.controls.append(self.compress_button)

        ttk.Separator(bar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8)

        self.compare_button = ttk.Button(bar, text="Comparar k=5,20,50,100", command=self.compare_k_values)
        self.compare_button.pack(side=tk.LEFT, padx=4)
        self.controls.append(self.compare_button)

        self.analysis_button = ttk.Button(bar, text="Gráficos de análisis", command=self.show_analysis)
        self.analysis_button.pack(side=tk.LEFT, padx=4)
        self.controls.append(self.analysis_button)

        self.info_label = ttk.Label(bar, text="Ninguna imagen cargada", foreground="#555")
        self.info_label.pack(side=tk.RIGHT, padx=8)

    def _build_metrics_tab(self):
        frame = ttk.Frame(self.tab_metrics)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.metrics_text = tk.Text(
            frame,
            font=("Courier New", 11),
            state=tk.DISABLED,
            wrap=tk.NONE,
            bg="#1e1e2e",
            fg="#cdd6f4",
            insertbackground="white",
        )
        sb_y = ttk.Scrollbar(frame, command=self.metrics_text.yview)
        sb_x = ttk.Scrollbar(frame, orient=tk.HORIZONTAL, command=self.metrics_text.xview)
        self.metrics_text.configure(yscrollcommand=sb_y.set, xscrollcommand=sb_x.set)

        sb_y.pack(side=tk.RIGHT, fill=tk.Y)
        sb_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.metrics_text.pack(fill=tk.BOTH, expand=True)

    def _build_status_bar(self):
        self.status_var = tk.StringVar(value="Listo")
        bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        bar.pack(fill=tk.X, side=tk.BOTTOM)

    # ---------------------------------------------------------- Image load --

    def load_image(self):
        if self.is_loading:
            return

        path = filedialog.askopenfilename(
            title="Seleccionar imagen",
            filetypes=[
                ("Imágenes", "*.svg *.png *.jpg *.jpeg *.bmp *.tiff *.webp"),
                ("SVG", "*.svg"),
                ("Raster", "*.png *.jpg *.jpeg *.bmp *.tiff *.webp"),
                ("Todos los archivos", "*.*"),
            ],
        )
        if not path:
            return

        self._set_loading(True)
        self.status_var.set("Cargando imagen...")

        thread = threading.Thread(target=self._load_image_worker, args=(path,), daemon=True)
        thread.start()

    def _load_image_worker(self, path):
        try:
            self.root.after(0, self.status_var.set, "Leyendo archivo...")
            image_array, image_mode, image_source = self._load_image_array(path)
            self.root.after(0, self.status_var.set, "Calculando SVD...")
            svd_data = self._compute_svd(image_array, image_mode)
        except Exception as exc:
            self.root.after(0, self._load_failed, exc)
            return

        self.root.after(0, self._load_finished, path, image_array, image_mode, image_source, svd_data)

    def _load_image_array(self, path):
        ext = os.path.splitext(path)[1].lower()
        source = "svg" if ext == ".svg" else "raster"

        if source == "svg":
            if cairosvg is None:
                raise RuntimeError("Para cargar SVG instala la dependencia: pip install -r requirements.txt")
            png_bytes = cairosvg.svg2png(url=path)
            img = Image.open(BytesIO(png_bytes))
        else:
            img = Image.open(path)

        img.load()

        if img.mode == "L":
            image_mode = "grayscale"
            image_array = np.array(img, dtype=float)
        else:
            if img.mode in ("RGBA", "LA") or ("transparency" in img.info):
                rgba = img.convert("RGBA")
                background = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
                img = Image.alpha_composite(background, rgba).convert("RGB")
            else:
                img = img.convert("RGB")
            image_mode = "rgb"
            image_array = np.array(img, dtype=float)

        if image_array.size == 0 or min(image_array.shape[:2]) < 1:
            raise ValueError("La imagen no tiene dimensiones válidas.")

        return image_array, image_mode, source

    def _compute_svd(self, image_array, image_mode):
        if image_mode == "grayscale":
            return np.linalg.svd(image_array, full_matrices=False)

        channels = []
        for c in range(3):
            channels.append(np.linalg.svd(image_array[:, :, c], full_matrices=False))
        return channels

    def _load_finished(self, path, image_array, image_mode, image_source, svd_data):
        self.image_path = path
        self.image_array = image_array
        self.image_mode = image_mode
        self.image_source = image_source

        if image_mode == "grayscale":
            self.U, self.S, self.Vt = svd_data
            self.U_ch = self.S_ch = self.Vt_ch = None
        else:
            self.U_ch = [parts[0] for parts in svd_data]
            self.S_ch = [parts[1] for parts in svd_data]
            self.Vt_ch = [parts[2] for parts in svd_data]
            self.U = self.S = self.Vt = None

        h, w = self.image_array.shape[:2]
        max_k = min(h, w)
        self.k_spin.config(to=max_k)
        if self._get_requested_k() > max_k:
            self.k_var.set(min(20, max_k))

        mode_str = "Escala de grises" if self.image_mode == "grayscale" else "RGB"
        source_str = "SVG renderizado" if self.image_source == "svg" else "Raster"
        self.info_label.config(
            text=f"{os.path.basename(path)}  |  {source_str}  |  {mode_str}  |  {w}x{h} px  |  rango <= {max_k}"
        )
        self.status_var.set("SVD calculada. Listo.")
        self._set_loading(False)
        self.compress()

    def _load_failed(self, exc):
        self._set_loading(False)
        self.status_var.set("No se pudo cargar la imagen.")
        messagebox.showerror("Error al cargar imagen", f"No se pudo abrir o convertir el archivo.\n\nDetalle: {exc}")

    def _set_loading(self, loading):
        self.is_loading = loading
        state = tk.DISABLED if loading else tk.NORMAL
        for control in self.controls:
            control.config(state=state)

    # --------------------------------------------------------------- SVD ---

    def _svd_grayscale(self):
        self.U, self.S, self.Vt = np.linalg.svd(self.image_array, full_matrices=False)

    def _svd_rgb(self):
        self.U_ch, self.S_ch, self.Vt_ch = [], [], []
        for c in range(3):
            U, S, Vt = np.linalg.svd(self.image_array[:, :, c], full_matrices=False)
            self.U_ch.append(U)
            self.S_ch.append(S)
            self.Vt_ch.append(Vt)

    def _get_requested_k(self):
        try:
            return int(self.k_var.get())
        except (tk.TclError, ValueError):
            return 1

    def _max_k(self):
        if self.image_array is None:
            return 1
        return min(self.image_array.shape[:2])

    def _clamp_k(self, k):
        return min(max(1, int(k)), self._max_k())

    def _reconstruct(self, k):
        k = self._clamp_k(k)
        if self.image_mode == "grayscale":
            rec = (self.U[:, :k] * self.S[:k]) @ self.Vt[:k, :]
            return np.clip(rec, 0, 255)
        else:
            channels = []
            for c in range(3):
                ch = (self.U_ch[c][:, :k] * self.S_ch[c][:k]) @ self.Vt_ch[c][:k, :]
                channels.append(np.clip(ch, 0, 255))
            return np.stack(channels, axis=2)

    # ----------------------------------------------------------- Metrics ---

    def _metrics(self, k, rec=None):
        k = self._clamp_k(k)
        if rec is None:
            rec = self._reconstruct(k)
        orig = self.image_array
        m, n = orig.shape[:2]

        if self.image_mode == "grayscale":
            error = np.linalg.norm(orig - rec, "fro")
            total_energy   = float(np.sum(self.S ** 2))
            captured_energy = float(np.sum(self.S[:k] ** 2))
            orig_vals = m * n
            comp_vals = k * (m + n + 1)
        else:
            error = float(np.sqrt(sum(
                np.linalg.norm(orig[:, :, c] - rec[:, :, c], "fro") ** 2
                for c in range(3)
            )))
            total_energy   = float(sum(np.sum(self.S_ch[c] ** 2) for c in range(3)))
            captured_energy = float(sum(np.sum(self.S_ch[c][:k] ** 2) for c in range(3)))
            orig_vals = m * n * 3
            comp_vals = k * (m + n + 1) * 3

        ratio   = comp_vals / orig_vals
        raw_pct_comp = (1 - ratio) * 100
        pct_comp = max(0, raw_pct_comp)
        pct_energy = 100 * captured_energy / total_energy if total_energy else 0

        return {
            "k": k,
            "error": error,
            "compression_pct": pct_comp,
            "raw_compression_pct": raw_pct_comp,
            "has_savings": ratio < 1,
            "ratio": ratio,
            "orig_vals": orig_vals,
            "comp_vals": comp_vals,
            "energy_pct": pct_energy,
        }

    def _compression_label(self, met):
        if met["has_savings"]:
            return f"{met['compression_pct']:.1f}%"
        return "sin ahorro real"

    # ------------------------------------------------------- Compress tab --

    def compress(self):
        if self.image_array is None:
            messagebox.showwarning("Sin imagen", "Primero carga una imagen.")
            return
        k = self._clamp_k(self._get_requested_k())
        if k != self._get_requested_k():
            self.k_var.set(k)
        self._render_comparison(k)
        self._render_metrics(k)

    def _render_comparison(self, k):
        k = self._clamp_k(k)
        rec = self._reconstruct(k)
        met = self._metrics(k, rec=rec)

        fig, axes = plt.subplots(1, 2, figsize=(10, 4.5))
        fig.patch.set_facecolor("#f0f0f0")
        fig.suptitle(f"Compresión SVD  -  k = {k}", fontsize=13, fontweight="bold")

        if self.image_mode == "grayscale":
            axes[0].imshow(self.image_array, cmap="gray", vmin=0, vmax=255)
            axes[1].imshow(rec, cmap="gray", vmin=0, vmax=255)
        else:
            axes[0].imshow(self.image_array.astype(np.uint8))
            axes[1].imshow(rec.astype(np.uint8))

        axes[0].set_title("Original", fontsize=11)
        axes[0].axis("off")
        axes[1].set_title(
            f"SVD  k = {k}\nError: {met['error']:.1f}  |  Ahorro: {self._compression_label(met)}  |  Energía: {met['energy_pct']:.2f}%",
            fontsize=10,
        )
        axes[1].axis("off")
        fig.tight_layout()

        self._embed_figure(fig, self.tab_compare, "_canvas_compare")
        plt.close(fig)

        self.status_var.set(
            f"k={k}  |  Error={met['error']:.2f}  |  Ahorro={self._compression_label(met)}  |  Energía capturada={met['energy_pct']:.2f}%"
        )

    def _render_metrics(self, k):
        k = self._clamp_k(k)
        met = self._metrics(k)
        m, n = self.image_array.shape[:2]

        if self.image_mode == "grayscale":
            max_k = min(m, n)
            s_vals = self.S
        else:
            max_k = min(m, n)
            s_vals = self.S_ch[0]

        lines = [
            "=" * 56,
            "  MÉTRICAS DE COMPRESIÓN SVD",
            "=" * 56,
            f"  Imagen       : {os.path.basename(self.image_path)}",
            f"  Modo         : {'Escala de grises' if self.image_mode == 'grayscale' else 'RGB (3 canales)'}",
            f"  Dimensiones  : {n} × {m} px",
            f"  Rango máximo : {max_k}",
            "-" * 56,
            f"  k utilizado  : {k}",
            f"  Error Frobenius       : {met['error']:.4f}",
            f"  Energía capturada     : {met['energy_pct']:.4f} %",
            f"  Valores originales    : {met['orig_vals']:,}",
            f"  Valores comprimidos   : {met['comp_vals']:,}",
            f"  Ratio de compresión   : {met['ratio']:.6f}",
            f"  % Ahorro              : {met['compression_pct']:.2f} %",
            f"  Estado                : {'con ahorro real' if met['has_savings'] else 'sin ahorro real'}",
            "-" * 56,
            "  Primeros valores singulares (canal R o gris):",
        ]
        top = min(15, len(s_vals))
        for i in range(top):
            bar_len = int(s_vals[i] / s_vals[0] * 20) if s_vals[0] else 0
            bar = "█" * bar_len
            lines.append(f"    σ_{i+1:>3} = {s_vals[i]:>10.2f}  {bar}")
        lines.append("=" * 56)

        self.metrics_text.config(state=tk.NORMAL)
        self.metrics_text.delete("1.0", tk.END)
        self.metrics_text.insert(tk.END, "\n".join(lines))
        self.metrics_text.config(state=tk.DISABLED)

    # --------------------------------------------------- Multi-k tab ------

    def compare_k_values(self):
        if self.image_array is None:
            messagebox.showwarning("Sin imagen", "Primero carga una imagen.")
            return

        self.status_var.set("Reconstruyendo para k = 5, 20, 50, 100…")
        self.root.update_idletasks()

        k_vals = [5, 20, 50, 100]
        max_k = min(self.image_array.shape[:2])
        k_vals = [k for k in k_vals if k <= max_k]

        n_cols = len(k_vals) + 1
        fig, axes = plt.subplots(1, n_cols, figsize=(3 * n_cols, 4))
        fig.suptitle("Comparación visual - distintos valores de k", fontsize=13, fontweight="bold")
        axes = np.atleast_1d(axes)

        if self.image_mode == "grayscale":
            axes[0].imshow(self.image_array, cmap="gray", vmin=0, vmax=255)
        else:
            axes[0].imshow(self.image_array.astype(np.uint8))
        axes[0].set_title("Original\n(sin compresión)", fontsize=9)
        axes[0].axis("off")

        for i, k in enumerate(k_vals):
            rec = self._reconstruct(k)
            met = self._metrics(k, rec=rec)
            if self.image_mode == "grayscale":
                axes[i + 1].imshow(rec, cmap="gray", vmin=0, vmax=255)
            else:
                axes[i + 1].imshow(rec.astype(np.uint8))
            axes[i + 1].set_title(
                f"k = {k}\n{self._compression_label(met)}\nError: {met['error']:.0f}",
                fontsize=9,
            )
            axes[i + 1].axis("off")

        fig.tight_layout()
        self._embed_figure(fig, self.tab_multi, "_canvas_multi")
        plt.close(fig)

        self.notebook.select(self.tab_multi)
        self.status_var.set("Comparación de k completada.")

    # --------------------------------------------------- Analysis tab -----

    def show_analysis(self):
        if self.image_array is None:
            messagebox.showwarning("Sin imagen", "Primero carga una imagen.")
            return

        self.status_var.set("Calculando gráficos de análisis…")
        self.root.update_idletasks()

        m, n = self.image_array.shape[:2]
        max_k = min(m, n)
        step  = max(1, max_k // 200)
        k_range = list(range(1, max_k + 1, step))

        errors, compressions, energies = [], [], []
        for k in k_range:
            met = self._metrics(k)
            errors.append(met["error"])
            compressions.append(met["compression_pct"])
            energies.append(met["energy_pct"])

        s_vals = self.S if self.image_mode == "grayscale" else self.S_ch[0]

        fig, axes = plt.subplots(2, 2, figsize=(11, 7))
        fig.suptitle("Análisis de Compresión SVD", fontsize=13, fontweight="bold")

        # 1. Singular value spectrum
        display_n = min(100, len(s_vals))
        axes[0, 0].semilogy(range(1, display_n + 1), s_vals[:display_n], "b-o", markersize=2)
        axes[0, 0].set_title("Espectro de Valores Singulares")
        axes[0, 0].set_xlabel("Índice i")
        axes[0, 0].set_ylabel("σᵢ  (escala logarítmica)")
        axes[0, 0].grid(True, alpha=0.3)

        # 2. Reconstruction error vs k
        axes[0, 1].plot(k_range, errors, "r-", linewidth=1.5)
        current_k = self._clamp_k(self._get_requested_k())

        axes[0, 1].axvline(current_k, color="gray", ls="--", label=f"k actual = {current_k}")
        axes[0, 1].set_title("Error de Reconstrucción vs k")
        axes[0, 1].set_xlabel("k")
        axes[0, 1].set_ylabel("Error (norma de Frobenius)")
        axes[0, 1].legend(fontsize=8)
        axes[0, 1].grid(True, alpha=0.3)

        # 3. Compression % vs k
        axes[1, 0].plot(k_range, compressions, "g-", linewidth=1.5)
        axes[1, 0].axvline(current_k, color="gray", ls="--", label=f"k actual = {current_k}")
        axes[1, 0].set_title("Porcentaje de Ahorro vs k")
        axes[1, 0].set_xlabel("k")
        axes[1, 0].set_ylabel("% Ahorro de almacenamiento")
        axes[1, 0].legend(fontsize=8)
        axes[1, 0].grid(True, alpha=0.3)

        # 4. Captured energy vs k
        axes[1, 1].plot(k_range, energies, "m-", linewidth=1.5)
        axes[1, 1].axhline(99, color="orange", ls="--", label="99 % energía")
        axes[1, 1].axhline(95, color="red",    ls="--", label="95 % energía")
        axes[1, 1].axvline(current_k, color="gray", ls=":", label=f"k actual = {current_k}")
        axes[1, 1].set_title("Energía Capturada vs k")
        axes[1, 1].set_xlabel("k")
        axes[1, 1].set_ylabel("% Energía capturada (σᵢ²)")
        axes[1, 1].legend(fontsize=8)
        axes[1, 1].grid(True, alpha=0.3)

        fig.tight_layout()
        self._embed_figure(fig, self.tab_graphs, "_canvas_graphs")
        plt.close(fig)

        self.notebook.select(self.tab_graphs)
        self.status_var.set("Gráficos de análisis generados.")

    # -------------------------------------------------- Helper: embed fig --

    def _embed_figure(self, fig, parent, attr):
        old = getattr(self, attr, None)
        if old is not None:
            old.get_tk_widget().destroy()
        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        setattr(self, attr, canvas)


# --------------------------------------------------------------------------- #

if __name__ == "__main__":
    root = tk.Tk()
    app = SVDImageCompressor(root)
    root.mainloop()
