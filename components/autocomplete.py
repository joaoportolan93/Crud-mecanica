"""Entry com dropdown de autocomplete e debounce de 300ms."""

import customtkinter as ctk


class AutocompleteEntry(ctk.CTkFrame):
    """Campo de busca com dropdown de sugestões.

    Args:
        search_fn: Função que recebe texto e retorna lista de dicts.
        on_select: Callback chamado com o dict do item selecionado.
        display_key: Chave do dict a exibir no dropdown (default 'nome').
        placeholder: Texto placeholder do entry.
    """

    def __init__(
        self,
        master,
        search_fn,
        on_select,
        display_key: str = "nome",
        placeholder: str = "Buscar...",
        **kwargs,
    ) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self._search_fn = search_fn
        self._on_select = on_select
        self._display_key = display_key
        self._after_id: str | None = None
        self._results: list = []
        self._suspend_search = False

        # Entry
        self._var = ctk.StringVar()
        self._var.trace_add("write", self._on_change)

        self.entry = ctk.CTkEntry(
            self, textvariable=self._var,
            placeholder_text=placeholder,
        )
        self.entry.pack(fill="x")

        # Dropdown (Toplevel flutuante)
        self._dropdown: ctk.CTkToplevel | None = None

    def get_text(self) -> str:
        return self._var.get()

    def set_text(self, text: str, trigger_search: bool = False) -> None:
        """Define o texto com ou sem disparar busca."""
        self._suspend_search = not trigger_search
        try:
            self._var.set(text)
        finally:
            self._suspend_search = False

    def clear(self) -> None:
        self.set_text("", trigger_search=False)

    def _on_change(self, *_) -> None:
        """Debounce: espera 300ms após última digitação."""
        if self._suspend_search:
            return
        if self._after_id:
            self.after_cancel(self._after_id)
        self._after_id = self.after(300, self._do_search)

    def _do_search(self) -> None:
        text = self._var.get().strip()
        if len(text) < 2:
            self._hide_dropdown()
            return
        try:
            self._results = self._search_fn(text)
        except Exception:
            self._results = []
        if self._results:
            self._show_dropdown()
        else:
            self._hide_dropdown()

    def _show_dropdown(self) -> None:
        self._hide_dropdown()

        self._dropdown = ctk.CTkToplevel(self)
        self._dropdown.overrideredirect(True)
        self._dropdown.attributes("-topmost", True)

        # Posicionar abaixo do entry
        x = self.entry.winfo_rootx()
        y = self.entry.winfo_rooty() + self.entry.winfo_height()
        w = self.entry.winfo_width()
        max_h = min(len(self._results) * 32 + 4, 200)
        self._dropdown.geometry(f"{w}x{max_h}+{x}+{y}")

        scroll = ctk.CTkScrollableFrame(
            self._dropdown, fg_color=("white", "gray20"),
            border_width=1, border_color=("gray75", "gray30"),
        )
        scroll.pack(fill="both", expand=True)

        for item in self._results[:20]:
            display = str(item.get(self._display_key, item))
            # Adicionar info extra se disponível
            extra = ""
            if "cpf_cnpj" in item and item["cpf_cnpj"]:
                extra = f"  ({item['cpf_cnpj']})"
            elif "placa" in item and item["placa"]:
                extra = f"  [{item['placa']}]"

            btn = ctk.CTkButton(
                scroll,
                text=display + extra,
                anchor="w",
                height=28,
                fg_color="transparent",
                text_color=("gray10", "gray90"),
                hover_color=("gray85", "gray30"),
                font=ctk.CTkFont(size=13),
                command=lambda i=item, d=display: self._select(i, d),
            )
            btn.pack(fill="x", padx=2, pady=1)

        # Fechar ao clicar fora
        self._dropdown.bind("<FocusOut>", lambda e: self.after(200, self._hide_dropdown))

    def _select(self, item, display: str) -> None:
        self.set_text(display, trigger_search=False)
        self._hide_dropdown()
        self._on_select(item)

    def _hide_dropdown(self) -> None:
        if self._dropdown:
            try:
                self._dropdown.destroy()
            except Exception:
                pass
            self._dropdown = None
