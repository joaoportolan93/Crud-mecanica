"""Tabela de dados scrollável e configurável."""

import customtkinter as ctk

from components.layout import TABLE_INNER_PADX, TABLE_INNER_PADY


class DataTable(ctk.CTkFrame):
    """Tabela com header fixo, corpo scrollável e clique por linha.

    Args:
        columns: Lista de dicts com 'key', 'label' e 'width' (opcional).
        on_row_click: Callback chamado com o dict da linha clicada.
    """

    def __init__(
        self,
        master,
        columns: list[dict],
        on_row_click=None,
        **kwargs,
    ) -> None:
        super().__init__(master, **kwargs)
        self.columns = columns
        self.on_row_click = on_row_click
        self._rows_data: list[dict] = []

        # Header
        self.header = ctk.CTkFrame(self, height=36, corner_radius=0)
        self.header.pack(fill="x")
        self.header.grid_columnconfigure(
            list(range(len(columns))),
            weight=1,
        )

        for i, col in enumerate(columns):
            ctk.CTkLabel(
                self.header,
                text=col["label"],
                font=ctk.CTkFont(size=12, weight="bold"),
                anchor="w",
                width=col.get("width", 120),
            ).grid(row=0, column=i, padx=(TABLE_INNER_PADX, 5), pady=TABLE_INNER_PADY + 2, sticky="w")

        # Corpo scrollável
        self.body = ctk.CTkScrollableFrame(
            self, corner_radius=0,
            fg_color="transparent",
        )
        self.body.pack(fill="both", expand=True)
        self.body.grid_columnconfigure(
            list(range(len(columns))),
            weight=1,
        )

        # Mensagem de vazio
        self._empty_label = ctk.CTkLabel(
            self.body, text="Nenhum registro encontrado.",
            text_color="gray50", font=ctk.CTkFont(size=13),
        )

    def set_data(self, rows: list[dict]) -> None:
        """Define os dados da tabela, recriando todas as linhas."""
        self._rows_data = rows

        # Limpar linhas anteriores
        for widget in self.body.winfo_children():
            widget.destroy()

        if not rows:
            self._empty_label = ctk.CTkLabel(
                self.body, text="Nenhum registro encontrado.",
                text_color="gray50", font=ctk.CTkFont(size=13),
            )
            self._empty_label.grid(row=0, column=0, columnspan=len(self.columns), pady=30)
            return

        for row_idx, row_data in enumerate(rows):
            # Cor alternada para legibilidade
            bg = ("gray92", "gray17") if row_idx % 2 == 0 else ("gray97", "gray14")

            row_frame = ctk.CTkFrame(
                self.body, fg_color=bg, corner_radius=4, height=34,
            )
            row_frame.grid(
                row=row_idx, column=0, columnspan=len(self.columns),
                sticky="ew", padx=2, pady=1,
            )
            row_frame.grid_columnconfigure(
                list(range(len(self.columns))), weight=1,
            )

            for col_idx, col in enumerate(self.columns):
                value = row_data.get(col["key"], "")
                label = ctk.CTkLabel(
                    row_frame,
                    text=str(value) if value is not None else "",
                    anchor="w",
                    fg_color="transparent",
                    width=col.get("width", 120),
                    font=ctk.CTkFont(size=13),
                )
                label.grid(
                    row=0, column=col_idx, padx=(TABLE_INNER_PADX, 5), pady=TABLE_INNER_PADY, sticky="w",
                )

                # Bind clique
                if self.on_row_click:
                    label.bind(
                        "<Button-1>",
                        lambda e, d=row_data: self.on_row_click(d),
                    )
                    label.configure(cursor="hand2")

            if self.on_row_click:
                row_frame.bind(
                    "<Button-1>",
                    lambda e, d=row_data: self.on_row_click(d),
                )
                row_frame.configure(cursor="hand2")
