"""Componentes visuais: MetricCard, StatusBadge, NotificationBanner, ConfirmDialog."""

import customtkinter as ctk


# ── Paleta de cores (funciona em light e dark mode) ─────────

STATUS_COLORS = {
    "ABERTA":       ("#e3f2fd", "#1565c0", "#1e88e5"),  # bg_light, bg_dark, fg
    "EM_ANDAMENTO": ("#fff3e0", "#e65100", "#fb8c00"),
    "CONCLUIDA":    ("#e8f5e9", "#2e7d32", "#43a047"),
    "CANCELADA":    ("#fce4ec", "#c62828", "#ef5350"),
}

ALERT_COLORS = {
    "info":    "#1a73e8",
    "success": "#34a853",
    "warning": "#f9ab00",
    "danger":  "#ea4335",
}


class MetricCard(ctk.CTkFrame):
    """Card de métrica para o dashboard."""

    def __init__(
        self,
        master,
        title: str,
        value: str = "0",
        icon: str = "📊",
        accent_color: str = "#1a73e8",
        **kwargs,
    ) -> None:
        super().__init__(master, corner_radius=12, **kwargs)

        self.configure(border_width=1, border_color=("gray80", "gray30"))

        # Ícone
        ctk.CTkLabel(
            self, text=icon,
            font=ctk.CTkFont(size=28),
        ).pack(anchor="w", padx=15, pady=(15, 5))

        # Valor
        self._value_label = ctk.CTkLabel(
            self, text=str(value),
            font=ctk.CTkFont(size=30, weight="bold"),
            text_color=accent_color,
        )
        self._value_label.pack(anchor="w", padx=15)

        # Título
        ctk.CTkLabel(
            self, text=title,
            font=ctk.CTkFont(size=13),
            text_color="gray50",
        ).pack(anchor="w", padx=15, pady=(2, 15))

    def set_value(self, value) -> None:
        self._value_label.configure(text=str(value))


class StatusBadge(ctk.CTkLabel):
    """Badge colorida para status da OS."""

    def __init__(self, master, status: str, **kwargs) -> None:
        colors = STATUS_COLORS.get(status, STATUS_COLORS["ABERTA"])
        labels = {
            "ABERTA": "Aberta",
            "EM_ANDAMENTO": "Em Andamento",
            "CONCLUIDA": "Concluída",
            "CANCELADA": "Cancelada",
        }
        super().__init__(
            master,
            text=f" {labels.get(status, status)} ",
            fg_color=(colors[0], colors[1]),
            text_color=(colors[1], "white"),
            corner_radius=6,
            font=ctk.CTkFont(size=11, weight="bold"),
            padx=8,
            pady=2,
            **kwargs,
        )


class NotificationBanner(ctk.CTkFrame):
    """Faixa de notificação dismissível no topo da tela."""

    def __init__(
        self,
        master,
        message: str,
        banner_type: str = "info",
        action_text: str | None = None,
        action_callback=None,
        **kwargs,
    ) -> None:
        color = ALERT_COLORS.get(banner_type, ALERT_COLORS["info"])
        super().__init__(master, fg_color=color, corner_radius=0, **kwargs)

        ctk.CTkLabel(
            self, text=f"  {message}",
            text_color="white",
            font=ctk.CTkFont(size=13),
        ).pack(side="left", padx=(10, 5), pady=6)

        if action_text and action_callback:
            ctk.CTkButton(
                self, text=action_text,
                fg_color="white", text_color=color,
                hover_color="gray90",
                font=ctk.CTkFont(size=12, weight="bold"),
                height=28, width=140,
                corner_radius=6,
                command=action_callback,
            ).pack(side="left", padx=5, pady=4)

        ctk.CTkButton(
            self, text="✕", width=30, height=28,
            fg_color="transparent", text_color="white",
            hover_color="gray40",
            command=self.destroy,
        ).pack(side="right", padx=5, pady=4)


class ConfirmDialog(ctk.CTkToplevel):
    """Diálogo de confirmação simples."""

    def __init__(
        self,
        master,
        title: str = "Confirmar",
        message: str = "Tem certeza?",
        on_confirm=None,
    ) -> None:
        super().__init__(master)
        self.title(title)
        self.geometry("400x180")
        self.resizable(False, False)
        self.transient(master.winfo_toplevel())
        self.grab_set()

        ctk.CTkLabel(
            self, text=message,
            font=ctk.CTkFont(size=14),
            wraplength=350,
        ).pack(pady=(30, 20), padx=20)

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=(0, 20))

        ctk.CTkButton(
            btn_frame, text="Cancelar", width=100,
            fg_color="gray50", hover_color="gray40",
            command=self.destroy,
        ).pack(side="left", padx=10)

        ctk.CTkButton(
            btn_frame, text="Confirmar", width=100,
            fg_color="#ea4335", hover_color="#c62828",
            command=lambda: (on_confirm() if on_confirm else None, self.destroy()),
        ).pack(side="left", padx=10)
