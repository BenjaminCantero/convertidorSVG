# Compresor de Imágenes mediante SVD

Aplicación de escritorio en Python que comprime imágenes digitales usando **Descomposición en Valores Singulares (SVD)**. Desarrollada para el curso MATE1187 — Álgebra Lineal para la Computación.

---

## Cómo funciona

### El fundamento matemático

Cualquier matriz A (como la de píxeles de una imagen) puede factorizarse como:

```
A = U · Σ · Vᵀ
```

donde:
- **U** — vectores singulares izquierdos (direcciones principales de la imagen de salida)
- **Σ** — diagonal con los valores singulares σ₁ ≥ σ₂ ≥ … ≥ 0, que miden cuánta información aporta cada componente
- **Vᵀ** — vectores singulares derechos (direcciones principales de la fuente)

La clave de la compresión es la **aproximación de rango k**:

```
Aₖ = U_k · Σ_k · Vₖᵀ
```

Al quedarse sólo con los primeros k valores singulares (los más grandes), se reconstruye la imagen usando k · (m + n + 1) valores en lugar de los m · n originales. El teorema de Eckart–Young garantiza que esta es la mejor aproximación posible de rango k.

### Representación de imágenes

- **Escala de grises:** una sola matriz m × n donde cada entrada es la intensidad del píxel (0–255). Se aplica una SVD.
- **RGB:** tres matrices m × n, una por canal (R, G, B). Se aplica SVD de forma independiente a cada canal.

---

## Instalación

**Requisitos:** Python 3.8 o superior.

```bash
pip install numpy pillow matplotlib
```

---

## Uso

```bash
python3 svd_compressor.py
```

### Pasos básicos

1. Clic en **"Cargar imagen"** y selecciona cualquier archivo PNG, JPG, BMP o TIFF.
2. La SVD se calcula automáticamente al cargar.
3. Elige un valor de **k** con el spinbox y pulsa **"Comprimir"** para ver la reconstrucción.
4. Usa **"Comparar k = 5, 20, 50, 100"** para ver cuatro niveles de compresión a la vez.
5. Usa **"Gráficos de análisis"** para ver las métricas en función de k.

---

## Pestañas de la interfaz

| Pestaña | Contenido |
|---|---|
| **Comparación** | Imagen original vs imagen reconstruida para el k elegido, con error y % de compresión |
| **k = 5, 20, 50, 100** | Comparación visual lado a lado para cuatro valores de k predefinidos |
| **Métricas** | Tabla con error de Frobenius, energía capturada, tamaño original y comprimido, % ahorro y los mayores valores singulares |
| **Análisis** | Cuatro gráficos: espectro de σᵢ, error vs k, % compresión vs k y energía capturada vs k |

---

## Métricas calculadas

| Métrica | Definición |
|---|---|
| **Error de Frobenius** | ‖A − Aₖ‖_F = √(σ²_{k+1} + … + σ²_r) — error cuadrático total píxel a píxel |
| **Energía capturada** | Σᵢ₌₁ᵏ σᵢ² / Σᵢ σᵢ² × 100 % — fracción de la información conservada |
| **Valores almacenados** | Original: m·n (o m·n·3 en RGB). Comprimido: k·(m+n+1) por canal |
| **% Compresión** | (1 − tamaño_comprimido / tamaño_original) × 100 |

---

## Dependencias

| Librería | Uso |
|---|---|
| `numpy` | Cálculo de SVD (`np.linalg.svd`) y operaciones matriciales |
| `Pillow` | Carga y conversión de imágenes a arrays |
| `matplotlib` | Visualización de imágenes y gráficos, embebido en tkinter |
| `tkinter` | Interfaz gráfica (incluida en Python estándar) |

---

## Integrantes

- Benjamin Cantero
- Eduardo Dominguez
- Juan Pablo Valdebenito
- Ricardo Garces

