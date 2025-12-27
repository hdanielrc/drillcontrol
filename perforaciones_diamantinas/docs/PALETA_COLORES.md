# Paleta de Colores - DrillControl System

## 🎨 Colores Principales

### Azul Oscuro Principal
- **HEX:** `#084163`
- **RGB:** `rgb(8, 65, 99)`
- **Variable CSS:** `--primary-dark` o `--dark-color`
- **Uso:** Navegación principal, encabezados importantes, fondos oscuros

### Azul Medio Principal  
- **HEX:** `#0470AC`
- **RGB:** `rgb(4, 112, 172)`
- **Variable CSS:** `--primary-medium` o `--primary-color`
- **Uso:** Botones primarios, enlaces, elementos interactivos principales

---

## 🎨 Colores Secundarios

### Azul Claro Secundario
- **HEX:** `#06AAFF`
- **RGB:** `rgb(6, 170, 255)`
- **Variable CSS:** `--secondary-blue` o `--info-color`
- **Uso:** Información, notificaciones, estados informativos

### Amarillo Secundario
- **HEX:** `#FFC248`
- **RGB:** `rgb(255, 194, 72)`
- **Variable CSS:** `--secondary-yellow` o `--warning-color`
- **Uso:** Alertas, advertencias, resaltados importantes

### Verde Secundario
- **HEX:** `#7AD57C`
- **RGB:** `rgb(122, 213, 124)`
- **Variable CSS:** `--secondary-green` o `--success-color`
- **Uso:** Éxito, confirmaciones, estados positivos

### Gris Claro Secundario
- **HEX:** `#E2E5F1`
- **RGB:** `rgb(226, 229, 241)`
- **Variable CSS:** `--secondary-gray` o `--light-color`
- **Uso:** Fondos, separadores, elementos neutrales

---

## 📋 Guía de Uso

### Navegación y Headers
```html
<nav style="background-color: var(--primary-dark);">...</nav>
<h1 style="color: var(--primary-dark);">Título Principal</h1>
```

### Botones Principales
```html
<button class="btn" style="background-color: var(--primary-medium);">Acción Principal</button>
<button class="btn" style="background-color: var(--secondary-blue);">Información</button>
```

### Estados y Notificaciones
```html
<div class="alert" style="background-color: var(--success-color);">Operación exitosa</div>
<div class="alert" style="background-color: var(--warning-color);">Advertencia</div>
<div class="alert" style="background-color: var(--info-color);">Información</div>
```

### Fondos y Secciones
```html
<section style="background-color: var(--light-color);">Contenido de sección</section>
```

---

## 🔧 Variables CSS Disponibles

### En archivo: `drilling/static/css/style.css`

```css
:root {
    /* Colores Primarios */
    --primary-dark: #084163;
    --primary-medium: #0470AC;
    
    /* Colores Secundarios */
    --secondary-blue: #06AAFF;
    --secondary-yellow: #FFC248;
    --secondary-green: #7AD57C;
    --secondary-gray: #E2E5F1;
    
    /* Alias Bootstrap-compatible */
    --primary-color: #0470AC;
    --secondary-color: #084163;
    --success-color: #7AD57C;
    --warning-color: #FFC248;
    --info-color: #06AAFF;
    --light-color: #E2E5F1;
    --dark-color: #084163;
}
```

---

## 🎯 Ejemplos de Aplicación

### 1. Navbar Principal
```html
<nav class="navbar" style="background-color: var(--primary-dark); color: white;">
    <a class="navbar-brand" style="color: white;">DrillControl</a>
    <button class="btn" style="background-color: var(--primary-medium);">Dashboard</button>
</nav>
```

### 2. Cards y Paneles
```html
<div class="card" style="border-left: 4px solid var(--primary-medium);">
    <div class="card-header" style="background-color: var(--light-color); color: var(--dark-color);">
        Panel de Control
    </div>
    <div class="card-body">
        Contenido...
    </div>
</div>
```

### 3. Badges de Estado
```html
<span class="badge" style="background-color: var(--success-color);">Activo</span>
<span class="badge" style="background-color: var(--warning-color);">Pendiente</span>
<span class="badge" style="background-color: var(--info-color);">En Proceso</span>
```

---

## 📌 Notas Importantes

1. **Siempre usar variables CSS** en lugar de valores hexadecimales directos
2. **Consistencia:** Mantener el uso de colores según su propósito
3. **Accesibilidad:** Verificar contraste de texto sobre fondos
4. **Responsive:** Los colores deben verse bien en modo claro y oscuro

---

## 🔄 Actualización de Templates Existentes

Al actualizar templates existentes, reemplazar:
- `#0d6efd` → `var(--primary-medium)`
- `#667eea`, `#764ba2` → `var(--primary-dark)`
- `#198754` → `var(--success-color)`
- `#ffc107` → `var(--warning-color)`
- `#0dcaf0` → `var(--info-color)`
- `#f8f9fa` → `var(--light-color)`
