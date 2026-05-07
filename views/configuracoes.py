"""Tela de Configurações — dados da oficina + atualização cacheada."""

from __future__ import annotations

import sys
import threading
import webbrowser

import customtkinter as ctk

from components.cards import CTkMessagebox
from components.layout import PAGE_PADX, PAGE_TOP_PADY, SECTION_GAP, SUBSECTION_GAP
from constants import APP_VERSION
from updater import (
    GITHUB_RELEASES_URL,
    UpdateError,
    baixar_e_instalar_atualizacao,
    registrar_callback_progresso,
)


class ConfiguracoesView(ctk.CTkFrame):
    """Tela de dados da oficina e estado de atualização."""

    def __init__(self, master, repos, app) -> None:
        super().__init__(master, fg_color="transparent")
        self.repos = repos
        self.app = app

        self._download_em_andamento = False
        self._download_percentual = 0
        self._download_thread: threading.Thread | None = None
        self._update_status_label: ctk.CTkLabel | None = None
        self._update_action_button: ctk.CTkButton | None = None
        self._update_manual_button: ctk.CTkButton | None = None
        self._update_progressbar: ctk.CTkProgressBar | None = None

        ctk.CTkLabel(
            self,
            text="Configurações",
            font=ctk.CTkFont(size=24, weight="bold"),
        ).pack(anchor="w", padx=PAGE_PADX, pady=(PAGE_TOP_PADY, SECTION_GAP))

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
            ctk.CTkLabel(
                form,
                text=label,
                font=ctk.CTkFont(size=13, weight="bold"),
                anchor="w",
            ).pack(fill="x", pady=(10, 2))
            entry = ctk.CTkEntry(form, placeholder_text=label)
            entry.pack(fill="x")
            self._fields[key] = entry

        ctk.CTkButton(
            form,
            text="💾 Salvar Configurações",
            width=200,
            command=self._salvar,
        ).pack(anchor="w", pady=15)

        self._msg = ctk.CTkLabel(form, text="", font=ctk.CTkFont(size=12))
        self._msg.pack(anchor="w")

        ctk.CTkFrame(self, height=1, fg_color="gray40").pack(
            fill="x", padx=PAGE_PADX, pady=SECTION_GAP
        )

        info = ctk.CTkFrame(self, fg_color="transparent")
        info.pack(fill="x", padx=PAGE_PADX)
        ctk.CTkLabel(
            info,
            text="Sobre o Sistema",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(anchor="w")
        ctk.CTkLabel(
            info,
            text=f"Versão: {APP_VERSION}",
            font=ctk.CTkFont(size=13),
        ).pack(anchor="w", pady=5)
        ctk.CTkLabel(
            info,
            text="Python + SQLite + CustomTkinter",
            text_color="gray50",
        ).pack(anchor="w")

        self._update_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._update_frame.pack(fill="x", padx=PAGE_PADX, pady=SECTION_GAP)
        self.render_update_section()

    def refresh(self) -> None:
        """Atualiza os dados da oficina e mantém o estado de atualização em cache."""
        try:
            dados = self.repos.config.get_dados_oficina()
            for key, entry in self._fields.items():
                entry.delete(0, "end")
                valor = dados.get(key.replace("_oficina", ""), "")
                if valor:
                    entry.insert(0, valor)
        except Exception:
            pass

        self.render_update_section()

    def render_update_section(self) -> None:
        """Desenha a seção de atualizações com base no estado cacheado do app."""
        for widget in self._update_frame.winfo_children():
            widget.destroy()

        self._update_status_label = None
        self._update_action_button = None
        self._update_manual_button = None
        self._update_progressbar = None

        container = ctk.CTkFrame(self._update_frame, fg_color="transparent")
        container.pack(fill="x")

        ctk.CTkLabel(
            container,
            text="Atualizações",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(anchor="w")

        estado = getattr(self.app, "update_status", {
            "estado": "verificando",
            "versao_nova": None,
            "url_download": None,
        })

        status = estado["estado"]
        if status == "verificando":
            self._update_status_label = ctk.CTkLabel(
                container,
                text="Verificando atualizações...",
                text_color="gray55",
                font=ctk.CTkFont(size=13),
            )
            self._update_status_label.pack(anchor="w", pady=(SUBSECTION_GAP, 0))
            return

        if status == "atualizado":
            self._update_status_label = ctk.CTkLabel(
                container,
                text=f"✓ Você está na versão mais recente ({APP_VERSION})",
                text_color="#16A34A",
                font=ctk.CTkFont(size=13),
            )
            self._update_status_label.pack(anchor="w", pady=(SUBSECTION_GAP, 0))
            return

        if status == "erro":
            self._update_status_label = ctk.CTkLabel(
                container,
                text="⚠ Não foi possível verificar atualizações",
                text_color="#D97706",
                font=ctk.CTkFont(size=13),
            )
            self._update_status_label.pack(anchor="w", pady=(SUBSECTION_GAP, 0))

            self._update_manual_button = ctk.CTkButton(
                container,
                text="Verificar manualmente",
                fg_color="transparent",
                hover_color="#E5E7EB",
                text_color="#2563EB",
                height=30,
                width=170,
                command=lambda: webbrowser.open(GITHUB_RELEASES_URL),
            )
            self._update_manual_button.pack(anchor="w", pady=(8, 0))
            return

        versao_nova = estado["versao_nova"] or ""
        self._update_status_label = ctk.CTkLabel(
            container,
            text=f"Nova versão disponível: {versao_nova}",
            font=ctk.CTkFont(size=13),
        )
        self._update_status_label.pack(anchor="w", pady=(SUBSECTION_GAP, 0))

        self._update_action_button = ctk.CTkButton(
            container,
            text="⬇ Atualizar agora",
            fg_color="#2563EB",
            hover_color="#1D4ED8",
            width=170,
            command=self._iniciar_atualizacao,
        )
        self._update_action_button.pack(anchor="w", pady=(10, 0))

        if self._download_em_andamento:
            self._update_action_button.configure(state="disabled", text="Baixando...")
            self._update_progressbar = ctk.CTkProgressBar(container, mode="indeterminate")
            self._update_progressbar.pack(fill="x", pady=(8, 0))
            self._update_progressbar.start()

            if self._download_percentual > 0:
                self._atualizar_progresso_download(self._download_percentual)

    def _salvar(self) -> None:
        try:
            for key, entry in self._fields.items():
                self.repos.config.set(key, entry.get().strip())
            self._msg.configure(text="✅ Configurações salvas!", text_color="#34a853")
        except Exception as exc:
            self._msg.configure(text=f"Erro: {exc}", text_color="#ea4335")

    def _iniciar_atualizacao(self) -> None:
        """Dispara o download do instalador sem travar a interface."""
        if self._download_em_andamento:
            return

        estado = getattr(self.app, "update_status", {})
        url_download = estado.get("url_download")
        if not url_download:
            CTkMessagebox(
                self,
                title="Atualização",
                message="Não foi possível localizar a página do release para a atualização.",
                icon="warning",
            )
            return

        self._download_em_andamento = True
        self._download_percentual = 0
        self.render_update_section()

        self._download_thread = threading.Thread(
            target=self._executar_download_atualizacao,
            args=(str(url_download),),
            daemon=True,
        )
        self._download_thread.start()

    def _executar_download_atualizacao(self, url_download: str) -> None:
        """Executa o download e dispara a instalação em background."""
        registrar_callback_progresso(self._agendar_progresso_download)
        try:
            try:
                baixar_e_instalar_atualizacao(url_download)
            except SystemExit:
                self.after(0, lambda: sys.exit(0))
            except UpdateError as exc:
                self.after(0, lambda mensagem=str(exc): self._finalizar_download_erro(mensagem))
            except Exception as exc:
                self.after(0, lambda mensagem=str(exc): self._finalizar_download_erro(mensagem))
        finally:
            registrar_callback_progresso(None)

    def _agendar_progresso_download(self, percentual: int) -> None:
        """Agenda a atualização visual do progresso na thread da UI."""
        try:
            self.after(0, lambda valor=percentual: self._atualizar_progresso_download(valor))
        except Exception:
            pass

    def _atualizar_progresso_download(self, percentual: int) -> None:
        """Atualiza a barra de progresso sem tocar na interface fora da thread principal."""
        self._download_percentual = percentual
        barra = self._update_progressbar
        if barra is None or not barra.winfo_exists():
            return

        try:
            barra.stop()
        except Exception:
            pass

        try:
            barra.configure(mode="determinate")
        except Exception:
            pass

        barra.set(percentual / 100)

    def _finalizar_download_erro(self, mensagem: str) -> None:
        """Restaura a tela de atualização após uma falha amigável."""
        self._download_em_andamento = False
        self._download_percentual = 0
        self.render_update_section()

        CTkMessagebox(
            self,
            title="Erro na atualização",
            message=mensagem,
            icon="cancel",
        )
