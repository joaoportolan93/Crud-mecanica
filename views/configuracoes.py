"""Tela de Configurações — dados da oficina + versão + atualização."""

import webbrowser
import customtkinter as ctk
from constants import APP_VERSION
from updater import verificar_atualizacao
from components.cards import NotificationBanner
from components.layout import PAGE_PADX, PAGE_TOP_PADY, SECTION_GAP


class ConfiguracoesView(ctk.CTkFrame):

    def __init__(self, master, repos, app) -> None:
        super().__init__(master, fg_color="transparent")
        self.repos = repos
        self.app = app

        ctk.CTkLabel(self, text="Configurações", font=ctk.CTkFont(size=24, weight="bold")).pack(anchor="w", padx=PAGE_PADX, pady=(PAGE_TOP_PADY, SECTION_GAP))

        form = ctk.CTkFrame(self, fg_color="transparent")
        form.pack(fill="x", padx=PAGE_PADX)

        self._fields: dict[str, ctk.CTkEntry] = {}
        campos = [
            ("nome_oficina", "Nome da Oficina"),
            ("telefone_oficina", "Telefone"),
            ("endereco_oficina", "Endereço"),
            ("cnpj_oficina", "CNPJ"),
        ]
        for key, label in campos:
            ctk.CTkLabel(form, text=label, font=ctk.CTkFont(size=13, weight="bold"), anchor="w").pack(fill="x", pady=(10, 2))
            entry = ctk.CTkEntry(form, placeholder_text=label)
            entry.pack(fill="x")
            self._fields[key] = entry

        ctk.CTkButton(form, text="💾 Salvar Configurações", width=200, command=self._salvar).pack(anchor="w", pady=15)

        self._msg = ctk.CTkLabel(form, text="", font=ctk.CTkFont(size=12))
        self._msg.pack(anchor="w")

        # Separador
        ctk.CTkFrame(self, height=1, fg_color="gray40").pack(fill="x", padx=PAGE_PADX, pady=SECTION_GAP)

        # Info de versão
        info = ctk.CTkFrame(self, fg_color="transparent")
        info.pack(fill="x", padx=PAGE_PADX)
        ctk.CTkLabel(info, text="Sobre o Sistema", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(info, text=f"Versão: {APP_VERSION}", font=ctk.CTkFont(size=13)).pack(anchor="w", pady=5)
        ctk.CTkLabel(info, text="Python + SQLite + CustomTkinter", text_color="gray50").pack(anchor="w")

        # Banner de atualização
        self._update_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._update_frame.pack(fill="x", padx=PAGE_PADX, pady=SECTION_GAP)

    def refresh(self) -> None:
        try:
            dados = self.repos.config.get_dados_oficina()
            for key, entry in self._fields.items():
                entry.delete(0, "end")
                val = dados.get(key.replace("_oficina", ""), "")
                if val:
                    entry.insert(0, val)
        except Exception:
            pass

        # Verificar atualização
        for w in self._update_frame.winfo_children():
            w.destroy()
        import threading
        def check():
            r = verificar_atualizacao()
            if r["tem_atualizacao"]:
                self.after(0, lambda: NotificationBanner(
                    self._update_frame, f"Nova versão disponível: {r['versao_nova']}",
                    action_text="Ver atualização", action_callback=lambda: webbrowser.open(r["url_download"]),
                ).pack(fill="x"))
        threading.Thread(target=check, daemon=True).start()

    def _salvar(self) -> None:
        try:
            for key, entry in self._fields.items():
                self.repos.config.set(key, entry.get().strip())
            self._msg.configure(text="✅ Configurações salvas!", text_color="#34a853")
        except Exception as e:
            self._msg.configure(text=f"Erro: {e}", text_color="#ea4335")
