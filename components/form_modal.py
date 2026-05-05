"""Modal de formulário reutilizável para CRUD."""

import customtkinter as ctk

from components.validation import attach_numeric_validation, normalize_numeric_text


class FormModal(ctk.CTkToplevel):
    """Janela modal com campos de formulário dinâmicos.

    Args:
        title: Título da janela.
        fields: Lista de dicts descrevendo os campos:
            - key: nome do campo (retornado no dict de resultado)
            - label: texto exibido
            - required: bool (default False)
            - type: 'text' (default), 'select', 'textarea'
            - input_mode: 'text' (default), 'digits', 'integer', 'decimal'
            - options: lista de opções (para type='select')
            - default: valor inicial
        on_save: Callback chamado com dict {key: valor} ao salvar.
        initial_data: Dict com valores iniciais (para edição).
    """

    def __init__(
        self,
        master,
        title: str,
        fields: list[dict],
        on_save,
        initial_data: dict | None = None,
    ) -> None:
        super().__init__(master)
        self.title(title)
        self.fields = fields
        self.on_save = on_save
        self._widgets: dict[str, ctk.CTkBaseClass] = {}

        # Centralizar e dimensionar
        self.geometry("500x600")
        self.resizable(False, True)
        self.transient(master)
        self.grab_set()

        # Scroll para formulários longos
        scroll = ctk.CTkScrollableFrame(self)
        scroll.pack(fill="both", expand=True, padx=20, pady=(20, 10))

        # Gerar campos
        for field in fields:
            key = field["key"]
            label_text = field["label"]
            if field.get("required"):
                label_text += " *"

            ctk.CTkLabel(
                scroll, text=label_text,
                font=ctk.CTkFont(size=13, weight="bold"),
                anchor="w",
            ).pack(fill="x", pady=(10, 2))

            field_type = field.get("type", "text")
            input_mode = field.get("input_mode", "text")
            default = (initial_data or {}).get(key, field.get("default", ""))

            if field_type == "select":
                options = field.get("options", [""])
                var = ctk.StringVar(value=str(default) if default else options[0])
                widget = ctk.CTkOptionMenu(scroll, variable=var, values=options)
                widget.pack(fill="x")
                self._widgets[key] = var

            elif field_type == "textarea":
                widget = ctk.CTkTextbox(scroll, height=80)
                widget.pack(fill="x")
                if default:
                    widget.insert("1.0", str(default))
                self._widgets[key] = widget

            else:  # text
                widget = ctk.CTkEntry(scroll, placeholder_text=field.get("placeholder", ""))
                if input_mode != "text":
                    attach_numeric_validation(widget, input_mode)
                widget.pack(fill="x")
                if default:
                    widget.insert(0, str(default))
                self._widgets[key] = widget

        # Label de erro (hidden)
        self._error_label = ctk.CTkLabel(
            self, text="", text_color="#ea4335",
            font=ctk.CTkFont(size=12),
        )
        self._error_label.pack(padx=20, pady=(5, 0))

        # Botões
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=(5, 20))

        ctk.CTkButton(
            btn_frame, text="Cancelar", width=100,
            fg_color="gray50", hover_color="gray40",
            command=self.destroy,
        ).pack(side="right", padx=(10, 0))

        ctk.CTkButton(
            btn_frame, text="Salvar", width=100,
            command=self._on_save_click,
        ).pack(side="right")

    def _get_values(self) -> dict:
        """Coleta os valores de todos os campos do formulário."""
        result = {}
        for field in self.fields:
            key = field["key"]
            widget = self._widgets[key]
            if isinstance(widget, ctk.StringVar):
                result[key] = widget.get()
            elif isinstance(widget, ctk.CTkTextbox):
                result[key] = widget.get("1.0", "end-1c").strip()
            else:
                field = next((f for f in self.fields if f["key"] == key), {})
                result[key] = normalize_numeric_text(widget.get(), field.get("input_mode", "text"))
        return result

    def _on_save_click(self) -> None:
        """Valida campos obrigatórios e chama on_save."""
        values = self._get_values()

        # Validar obrigatórios
        for field in self.fields:
            if field.get("required") and not values.get(field["key"]):
                self._error_label.configure(
                    text=f"O campo '{field['label']}' é obrigatório."
                )
                return

        self._error_label.configure(text="")

        try:
            self.on_save(values)
            self.destroy()
        except Exception as e:
            self._error_label.configure(text=f"Erro: {e}")
